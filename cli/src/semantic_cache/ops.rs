use super::{SemanticCache, StdResult};
use crate::ResolverError;
use crate::config::Config;
use crate::types::ResolvedResult;

#[cfg(feature = "semantic-cache")]
use {
    chaotic_semantic_memory::encoder::TextEncoder,
    chaotic_semantic_memory::prelude::*,
    serde_json::Value,
    std::collections::HashMap,
    std::sync::{Mutex, OnceLock},
};

#[cfg(feature = "semantic-cache")]
static GLOBAL_ENCODER: OnceLock<TextEncoder> = OnceLock::new();

impl SemanticCache {
    /// Internal normalization for cache keys and semantic comparison
    #[allow(dead_code)]
    pub(crate) fn normalize_text(text: &str, filter_stop_words: bool) -> String {
        let mut tokens: Vec<&str> = text
            .split(|c: char| !c.is_alphanumeric())
            .filter(|w| !w.is_empty())
            .collect();

        if crate::resolver::is_url(text) {
            tokens.retain(|w| {
                let low = w.to_lowercase();
                ![
                    "https", "http", "www", "html", "htm", "php", "asp", "aspx", "jsp", "docs",
                    "api", "index",
                ]
                .contains(&low.as_str())
            });
        }

        if filter_stop_words && !crate::resolver::is_url(text) {
            tokens.retain(|w| {
                let low = w.to_lowercase();
                ![
                    "docs",
                    "documentation",
                    "guide",
                    "tutorial",
                    "reference",
                    "ref",
                    "lib",
                    "library",
                    "std",
                    "standard",
                    "for",
                    "of",
                    "the",
                    "a",
                    "an",
                    "and",
                    "programming",
                    "language",
                    "module",
                    "api",
                ]
                .contains(&low.as_str())
            });
        }

        if tokens.is_empty() {
            return text
                .to_lowercase()
                .split_whitespace()
                .collect::<Vec<_>>()
                .join(" ");
        }

        let mut lowered: Vec<String> = tokens.into_iter().map(|s| s.to_lowercase()).collect();
        lowered.sort();
        lowered.join(" ")
    }

    #[cfg(feature = "semantic-cache")]
    pub async fn new(config: &Config) -> StdResult<Option<Self>, ResolverError> {
        if !config.semantic_cache.enabled {
            tracing::debug!("Semantic cache disabled");
            return Ok(None);
        }

        let mut cache_config = config.semantic_cache.clone();

        let mut ttls = std::collections::HashMap::new();
        ttls.insert("firecrawl".into(), config.cache.ttl.firecrawl);
        ttls.insert("exa".into(), config.cache.ttl.exa);
        ttls.insert("exa_mcp".into(), config.cache.ttl.exa);
        ttls.insert("tavily".into(), config.cache.ttl.tavily);
        ttls.insert("serper".into(), config.cache.ttl.serper);
        ttls.insert("jina".into(), config.cache.ttl.jina);
        ttls.insert("mistral".into(), config.cache.ttl.mistral);
        ttls.insert("mistral_browser".into(), config.cache.ttl.mistral);
        ttls.insert("mistral_websearch".into(), config.cache.ttl.mistral);
        ttls.insert("duckduckgo".into(), config.cache.ttl.duckduckgo);
        ttls.insert("llms_txt".into(), config.cache.ttl.llms_txt);
        ttls.insert("synthesis".into(), config.cache.ttl.synthesis);
        ttls.insert("default".into(), config.cache.ttl.default);
        cache_config.ttls = Some(ttls);

        tracing::info!(
            "Initializing semantic cache at '{}' with threshold {}",
            cache_config.path,
            cache_config.threshold
        );

        if let Err(e) = std::fs::create_dir_all(&cache_config.path) {
            tracing::warn!("Failed to create cache directory: {}", e);
            return Ok(None);
        }

        let db_path = std::path::Path::new(&cache_config.path).join("semantic.db");

        let framework = ChaoticSemanticFramework::builder()
            .with_local_db(db_path.to_str().unwrap_or("memory.db"))
            .with_max_concepts(cache_config.max_entries)
            .build()
            .await
            .map_err(|e| ResolverError::Config(e.to_string()))?;

        // Warm up the encoder in a background task to pay the ~1s loading cost upfront
        // This ensures the first semantic hit in a long-running session is fast,
        // and for CLI it makes the 'init' phase include model loading.
        tokio::task::spawn_blocking(|| {
            let _ = GLOBAL_ENCODER.get_or_init(|| {
                tracing::info!("Warming up text encoder in background...");
                TextEncoder::new_code_aware()
            });
        });

        Ok(Some(Self {
            framework,
            config: cache_config,
            embedding_cache: Mutex::new(HashMap::new()),
            hit_count: std::sync::atomic::AtomicUsize::new(0),
            miss_count: std::sync::atomic::AtomicUsize::new(0),
        }))
    }

    #[cfg(not(feature = "semantic-cache"))]
    pub async fn new(_config: &Config) -> StdResult<Option<Self>, ResolverError> {
        Ok(None)
    }

    #[cfg(feature = "semantic-cache")]
    pub async fn query(
        &self,
        query: &str,
    ) -> StdResult<Option<Vec<ResolvedResult>>, ResolverError> {
        let normalized = Self::normalize_text(query, false);

        if let Ok(Some(concept)) = self.framework.get_concept(&normalized).await {
            tracing::info!("Semantic cache EXACT HIT for query='{}'", query);
            self.hit_count
                .fetch_add(1, std::sync::atomic::Ordering::Relaxed);

            if let (Some(provider_val), Some(ts_val)) = (
                concept.metadata.get("provider"),
                concept.metadata.get("timestamp"),
            ) {
                if let (Some(provider), Some(ts_str)) = (provider_val.as_str(), ts_val.as_str()) {
                    if let Ok(ts) = chrono::DateTime::parse_from_rfc3339(ts_str) {
                        let ttl_secs = self.config.get_ttl(provider);
                        let age = chrono::Utc::now().signed_duration_since(ts);
                        if age.num_seconds() > ttl_secs as i64 {
                            tracing::info!("Semantic cache entry expired for query='{}'", query);
                            let _ = self.remove(query).await;
                            return Ok(None);
                        }
                    }
                }
            }

            if let Some(results_value) = concept.metadata.get("results") {
                if let Ok(results) =
                    serde_json::from_value::<Vec<ResolvedResult>>(results_value.clone())
                {
                    return Ok(Some(results));
                }
            }
        }

        let query_vector = self.encode_query(query);

        let hits = self
            .framework
            .probe(query_vector, 5)
            .await
            .map_err(|e| ResolverError::Cache(format!("probe failed: {}", e)))?;

        if hits.is_empty() {
            tracing::debug!("Semantic cache miss for query='{}'", query);
            return Ok(None);
        }

        let (best_id, best_score) = &hits[0];

        // Dynamic threshold adjustment: if query is very short, be more strict
        let effective_threshold = if normalized.len() < 10 {
            self.config.threshold.max(0.92)
        } else {
            self.config.threshold
        };

        if *best_score >= effective_threshold {
            tracing::info!(
                "Semantic cache HIT for query='{}' (score: {:.2}, id: {})",
                query,
                best_score,
                best_id
            );
            self.hit_count
                .fetch_add(1, std::sync::atomic::Ordering::Relaxed);

            if let Some(concept) = self
                .framework
                .get_concept(best_id)
                .await
                .map_err(|e| ResolverError::Cache(format!("get_concept failed: {}", e)))?
            {
                if let (Some(provider_val), Some(ts_val)) = (
                    concept.metadata.get("provider"),
                    concept.metadata.get("timestamp"),
                ) {
                    if let (Some(provider), Some(ts_str)) = (provider_val.as_str(), ts_val.as_str())
                    {
                        if let Ok(ts) = chrono::DateTime::parse_from_rfc3339(ts_str) {
                            let ttl_secs = self.config.get_ttl(provider);
                            let age = chrono::Utc::now().signed_duration_since(ts);
                            if age.num_seconds() > ttl_secs as i64 {
                                tracing::info!(
                                    "Semantic cache entry expired (semantic) for id: {}",
                                    best_id
                                );
                                let _ = self.remove(best_id).await;
                                return Ok(None);
                            }
                        }
                    }
                }

                if let Some(results_value) = concept.metadata.get("results") {
                    if let Ok(results) =
                        serde_json::from_value::<Vec<ResolvedResult>>(results_value.clone())
                    {
                        // Optimization: Alias this semantic hit as an exact hit for next time.
                        if *best_score > 0.95 {
                            let _ = self.store_alias(query, &results, query_vector).await;
                        }
                        return Ok(Some(results));
                    }
                }
            }
        }

        tracing::debug!(
            "Semantic cache miss for query='{}' (best score: {:.2} < {})",
            query,
            best_score,
            self.config.threshold
        );
        self.miss_count
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        Ok(None)
    }

    #[cfg(not(feature = "semantic-cache"))]
    #[allow(dead_code)]
    pub async fn query(
        &self,
        _query: &str,
    ) -> StdResult<Option<Vec<ResolvedResult>>, ResolverError> {
        Ok(None)
    }

    #[cfg(feature = "semantic-cache")]
    pub async fn store(
        &self,
        query: &str,
        results: &[ResolvedResult],
        provider: &str,
    ) -> StdResult<(), ResolverError> {
        let normalized = Self::normalize_text(query, false);

        let query_vector = self.encode_query(query);

        // Redundancy pruning: check if a very similar entry already exists
        if let Ok(hits) = self.framework.probe(query_vector, 5).await {
            for (best_id, best_score) in hits {
                // If score is extremely high (>0.995), always skip to avoid database bloat.
                // High similarity often indicates near-duplicate normalization results.
                if best_score > 0.995 {
                    tracing::info!(
                        "Skipping store for query='{}': extremely similar entry already exists (id: {}, score: {:.4})",
                        query,
                        best_id,
                        best_score
                    );
                    return Ok(());
                }

                if best_score > 0.98 {
                    // Check if the actual content is identical to avoid redundant storage
                    if let Ok(Some(existing)) = self.framework.get_concept(&best_id).await {
                        if let (Some(existing_results), Some(new_results)) = (
                            existing.metadata.get("results"),
                            serde_json::to_value(results).ok(),
                        ) {
                            if existing_results == &new_results {
                                tracing::info!(
                                    "Skipping store for query='{}': identical result already exists (id: {}, score: {:.4})",
                                    query,
                                    best_id,
                                    best_score
                                );
                                return Ok(());
                            }
                        }
                    }
                }
            }
        }

        let mut metadata = HashMap::new();
        metadata.insert("query".to_string(), Value::String(query.to_string()));
        metadata.insert(
            "results".to_string(),
            serde_json::to_value(results)
                .map_err(|e| ResolverError::Cache(format!("serialize results: {}", e)))?,
        );
        metadata.insert("provider".to_string(), Value::String(provider.to_string()));
        metadata.insert(
            "timestamp".to_string(),
            Value::String(chrono::Utc::now().to_rfc3339()),
        );

        self.framework
            .inject_concept_with_metadata(normalized.clone(), query_vector, metadata)
            .await
            .map_err(|e| ResolverError::Cache(format!("inject failed: {}", e)))?;

        tracing::info!(
            "Stored result in semantic cache: provider={}, query='{}'",
            provider,
            query
        );
        Ok(())
    }

    #[cfg(not(feature = "semantic-cache"))]
    #[allow(dead_code)]
    pub async fn store(
        &self,
        _query: &str,
        _results: &[ResolvedResult],
        _provider: &str,
    ) -> StdResult<(), ResolverError> {
        Ok(())
    }

    #[cfg(feature = "semantic-cache")]
    pub async fn store_alias(
        &self,
        query: &str,
        results: &[ResolvedResult],
        vector: HVec10240,
    ) -> StdResult<(), ResolverError> {
        let normalized = Self::normalize_text(query, false);

        let mut metadata = std::collections::HashMap::new();
        metadata.insert(
            "query".to_string(),
            serde_json::Value::String(query.to_string()),
        );
        metadata.insert(
            "results".to_string(),
            serde_json::to_value(results)
                .map_err(|e| ResolverError::Cache(format!("serialize results: {}", e)))?,
        );
        metadata.insert(
            "provider".to_string(),
            serde_json::Value::String("cache_alias".to_string()),
        );
        metadata.insert(
            "timestamp".to_string(),
            serde_json::Value::String(chrono::Utc::now().to_rfc3339()),
        );

        self.framework
            .inject_concept_with_metadata(normalized, vector, metadata)
            .await
            .map_err(|e| ResolverError::Cache(format!("inject alias failed: {}", e)))?;

        Ok(())
    }

    #[cfg(feature = "semantic-cache")]
    pub async fn remove(&self, query: &str) -> StdResult<(), ResolverError> {
        let normalized = Self::normalize_text(query, false);

        self.framework
            .delete_concept(&normalized)
            .await
            .map_err(|e| ResolverError::Cache(format!("delete failed: {}", e)))?;

        tracing::info!("Removed from semantic cache: query='{}'", query);
        Ok(())
    }

    #[cfg(not(feature = "semantic-cache"))]
    #[allow(dead_code)]
    pub async fn store_alias(
        &self,
        _query: &str,
        _results: &[ResolvedResult],
        _vector: (),
    ) -> StdResult<(), ResolverError> {
        Ok(())
    }

    #[cfg(not(feature = "semantic-cache"))]
    #[allow(dead_code)]
    pub async fn remove(&self, _query: &str) -> StdResult<(), ResolverError> {
        Ok(())
    }

    #[cfg(feature = "semantic-cache")]
    pub async fn query_url(&self, url: &str) -> StdResult<Option<ResolvedResult>, ResolverError> {
        self.query(url)
            .await
            .map(|opt| opt.and_then(|vec| vec.into_iter().next()))
    }

    #[cfg(not(feature = "semantic-cache"))]
    pub async fn query_url(&self, _url: &str) -> StdResult<Option<ResolvedResult>, ResolverError> {
        Ok(None)
    }

    #[cfg(feature = "semantic-cache")]
    pub async fn query_provider(
        &self,
        query: &str,
        provider: &str,
    ) -> StdResult<Option<Vec<ResolvedResult>>, ResolverError> {
        let key = format!("{}:{}", provider, query);
        self.query(&key).await
    }

    #[cfg(not(feature = "semantic-cache"))]
    pub async fn query_provider(
        &self,
        _query: &str,
        _provider: &str,
    ) -> StdResult<Option<Vec<ResolvedResult>>, ResolverError> {
        Ok(None)
    }

    #[cfg(feature = "semantic-cache")]
    pub async fn has_valid_entry(&self, query: &str) -> bool {
        let normalized = Self::normalize_text(query, false);

        if let Ok(Some(_)) = self.framework.get_concept(&normalized).await {
            return true;
        }

        let query_vector = self.encode_query(query);

        if let Ok(hits) = self.framework.probe(query_vector, 1).await {
            if let Some((_, score)) = hits.first() {
                return *score >= self.config.threshold;
            }
        }

        false
    }

    #[cfg(not(feature = "semantic-cache"))]
    pub async fn has_valid_entry(&self, _query: &str) -> bool {
        false
    }

    #[cfg(feature = "semantic-cache")]
    pub(crate) fn encode_query(&self, query: &str) -> HVec10240 {
        let start = std::time::Instant::now();
        let normalized = Self::normalize_text(query, true);

        if let Ok(cache) = self.embedding_cache.lock() {
            if let Some(vec) = cache.get(&normalized) {
                tracing::debug!("Embedding cache hit in {}ms", start.elapsed().as_millis());
                return *vec;
            }
        }

        tracing::debug!("Encoding query: '{}'", normalized);
        let encoder_start = std::time::Instant::now();
        let encoder = GLOBAL_ENCODER.get_or_init(|| {
            tracing::info!("Loading text encoder (first use)... ");
            TextEncoder::new_code_aware()
        });
        tracing::debug!("Encoder ready in {}ms", encoder_start.elapsed().as_millis());

        let encode_start = std::time::Instant::now();
        let vec = encoder.encode(&normalized);
        tracing::debug!("Text encoded in {}ms", encode_start.elapsed().as_millis());

        if let Ok(mut cache) = self.embedding_cache.lock() {
            if cache.len() < 1000 {
                cache.insert(normalized, vec);
            }
        }

        vec
    }

    #[cfg(not(feature = "semantic-cache"))]
    #[allow(dead_code, clippy::unused_unit)]
    pub(crate) fn encode_query(&self, _query: &str) -> () {}
}
