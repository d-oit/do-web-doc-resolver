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

/// Request kind for typed cache scoping
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum RequestKind {
    Url,
    Query,
    ProviderQuery,
    Aggregated,
    Synthesis,
}

impl RequestKind {
    pub fn as_str(&self) -> &'static str {
        match self {
            RequestKind::Url => "url",
            RequestKind::Query => "query",
            RequestKind::ProviderQuery => "pquery",
            RequestKind::Aggregated => "aggregated",
            RequestKind::Synthesis => "synthesis",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "url" => Some(RequestKind::Url),
            "query" => Some(RequestKind::Query),
            "pquery" => Some(RequestKind::ProviderQuery),
            "aggregated" => Some(RequestKind::Aggregated),
            "synthesis" => Some(RequestKind::Synthesis),
            _ => None,
        }
    }
}

/// Typed cache key ensuring identity isolation and provider/kind scoping
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CacheKey {
    pub kind: RequestKind,
    pub provider: String,
    pub canonical: String,
}

impl CacheKey {
    pub fn to_concept_id(&self) -> String {
        format!("v2:{}:{}:{}", self.kind.as_str(), self.provider, self.canonical)
    }

    pub fn parse_concept_id(id: &str) -> Option<Self> {
        let mut parts = id.splitn(4, ':');
        let version = parts.next()?;
        if version != "v2" {
            return None;
        }
        let kind = RequestKind::parse(parts.next()?)?;
        let provider = parts.next()?.to_string();
        let canonical = parts.next()?.to_string();
        Some(Self {
            kind,
            provider,
            canonical,
        })
    }

    pub fn from_query(query: &str, provider: Option<&str>) -> Self {
        if let Some(rest) = query.strip_prefix("aggregated:") {
            CacheKey {
                kind: RequestKind::Aggregated,
                provider: "none".to_string(),
                canonical: canonicalize_query(rest),
            }
        } else if crate::resolver::is_url(query) {
            CacheKey {
                kind: RequestKind::Url,
                provider: "none".to_string(),
                canonical: canonicalize_url(query),
            }
        } else if let Some(p) = provider {
            let prefix = format!("{}:", p);
            if let Some(rest) = query.strip_prefix(&prefix) {
                CacheKey {
                    kind: RequestKind::ProviderQuery,
                    provider: p.to_lowercase(),
                    canonical: canonicalize_query(rest),
                }
            } else {
                CacheKey {
                    kind: RequestKind::Query,
                    provider: "none".to_string(),
                    canonical: canonicalize_query(query),
                }
            }
        } else {
            CacheKey {
                kind: RequestKind::Query,
                provider: "none".to_string(),
                canonical: canonicalize_query(query),
            }
        }
    }
}

/// Canonicalize a URL for exact identity matching
pub fn canonicalize_url(raw_url: &str) -> String {
    let trimmed = raw_url.trim();
    let Ok(mut parsed) = url::Url::parse(trimmed) else {
        return trimmed.to_string();
    };

    // Strip client-side UI fragment anchors per fragment policy
    parsed.set_fragment(None);

    // Sort query parameters deterministically by key, then value
    if parsed.query().is_some() {
        let mut pairs: Vec<(String, String)> = parsed
            .query_pairs()
            .map(|(k, v)| (k.into_owned(), v.into_owned()))
            .collect();
        pairs.sort_by(|a, b| a.0.cmp(&b.0).then_with(|| a.1.cmp(&b.1)));

        parsed.query_pairs_mut().clear();
        for (k, v) in pairs {
            parsed.query_pairs_mut().append_pair(&k, &v);
        }
    }

    parsed.to_string()
}

/// Canonicalize a natural language query preserving word order
pub fn canonicalize_query(raw_query: &str) -> String {
    raw_query
        .split_whitespace()
        .collect::<Vec<_>>()
        .join(" ")
        .to_lowercase()
}

impl SemanticCache {
    /// Internal normalization for legacy callers / encoding
    #[allow(dead_code)]
    pub(crate) fn normalize_text(text: &str, filter_stop_words: bool) -> String {
        if crate::resolver::is_url(text) {
            return canonicalize_url(text);
        }

        let mut tokens: Vec<&str> = text
            .split(|c: char| !c.is_alphanumeric())
            .filter(|w| !w.is_empty())
            .collect();

        if filter_stop_words {
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
            return canonicalize_query(text);
        }

        tokens.into_iter().map(|s| s.to_lowercase()).collect::<Vec<_>>().join(" ")
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
        let key = CacheKey::from_query(query, None);
        self.query_key(&key).await
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
    pub async fn query_url(&self, url: &str) -> StdResult<Option<ResolvedResult>, ResolverError> {
        let key = CacheKey {
            kind: RequestKind::Url,
            provider: "none".to_string(),
            canonical: canonicalize_url(url),
        };
        self.query_key(&key)
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
        let key = CacheKey {
            kind: RequestKind::ProviderQuery,
            provider: provider.to_lowercase(),
            canonical: canonicalize_query(query),
        };
        self.query_key(&key).await
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
    pub async fn query_key(
        &self,
        target_key: &CacheKey,
    ) -> StdResult<Option<Vec<ResolvedResult>>, ResolverError> {
        let concept_id = target_key.to_concept_id();

        // 1. Exact lookup using versioned concept ID
        if let Ok(Some(concept)) = self.framework.get_concept(&concept_id).await {
            tracing::info!("Semantic cache EXACT HIT for key='{}'", concept_id);
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
                            tracing::info!("Semantic cache entry expired for key='{}'", concept_id);
                            let _ = self.framework.delete_concept(&concept_id).await;
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

        // 2. For URLs, approximate hits across different URLs are disabled
        if target_key.kind == RequestKind::Url {
            tracing::debug!("Semantic cache miss for URL key='{}'", concept_id);
            self.miss_count
                .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            return Ok(None);
        }

        // 3. Approximate probe for natural language search queries
        let query_vector = self.encode_query(&target_key.canonical);

        let hits = self
            .framework
            .probe(query_vector, 5)
            .await
            .map_err(|e| ResolverError::Cache(format!("probe failed: {}", e)))?;

        if hits.is_empty() {
            tracing::debug!("Semantic cache miss for key='{}'", concept_id);
            self.miss_count
                .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
            return Ok(None);
        }

        let effective_threshold = if target_key.canonical.len() < 10 {
            self.config.threshold.max(0.92)
        } else {
            self.config.threshold
        };

        for (best_id, best_score) in hits {
            if best_score < effective_threshold {
                break;
            }

            // Parse candidate ID and enforce version and predicate isolation
            let Some(candidate_key) = CacheKey::parse_concept_id(&best_id) else {
                continue;
            };

            if candidate_key.kind != target_key.kind {
                continue;
            }

            if target_key.provider != "none" && candidate_key.provider != target_key.provider {
                continue;
            }

            if let Some(concept) = self
                .framework
                .get_concept(&best_id)
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
                                let _ = self.framework.delete_concept(&best_id).await;
                                continue;
                            }
                        }
                    }
                }

                if let Some(results_value) = concept.metadata.get("results") {
                    if let Ok(results) =
                        serde_json::from_value::<Vec<ResolvedResult>>(results_value.clone())
                    {
                        tracing::info!(
                            "Semantic cache HIT for key='{}' (score: {:.2}, candidate: {})",
                            concept_id,
                            best_score,
                            best_id
                        );
                        self.hit_count
                            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);

                        if best_score > 0.95 {
                            let _ = self.store_alias_key(target_key, &results, query_vector).await;
                        }
                        return Ok(Some(results));
                    }
                }
            }
        }

        tracing::debug!("Semantic cache miss for key='{}'", concept_id);
        self.miss_count
            .fetch_add(1, std::sync::atomic::Ordering::Relaxed);
        Ok(None)
    }

    #[cfg(feature = "semantic-cache")]
    pub async fn store(
        &self,
        query: &str,
        results: &[ResolvedResult],
        provider: &str,
    ) -> StdResult<(), ResolverError> {
        let key = CacheKey::from_query(query, Some(provider));
        self.store_key(&key, results, provider).await
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
    pub async fn store_key(
        &self,
        key: &CacheKey,
        results: &[ResolvedResult],
        provider: &str,
    ) -> StdResult<(), ResolverError> {
        let concept_id = key.to_concept_id();
        let query_vector = self.encode_query(&key.canonical);

        // Redundancy pruning: check if a very similar entry exists IN THE SAME SCOPE
        if let Ok(hits) = self.framework.probe(query_vector, 5).await {
            for (best_id, best_score) in hits {
                if best_id == concept_id {
                    continue; // Replacing exact concept ID
                }

                let Some(candidate_key) = CacheKey::parse_concept_id(&best_id) else {
                    continue;
                };

                if candidate_key.kind != key.kind || candidate_key.provider != key.provider {
                    continue;
                }

                if key.kind == RequestKind::Url && candidate_key.canonical != key.canonical {
                    continue;
                }

                if best_score > 0.995 {
                    tracing::info!(
                        "Skipping store for key='{}': extremely similar entry in same scope exists (id: {}, score: {:.4})",
                        concept_id,
                        best_id,
                        best_score
                    );
                    return Ok(());
                }

                if best_score > 0.98 {
                    if let Ok(Some(existing)) = self.framework.get_concept(&best_id).await {
                        if let (Some(existing_results), Some(new_results)) = (
                            existing.metadata.get("results"),
                            serde_json::to_value(results).ok(),
                        ) {
                            if existing_results == &new_results {
                                tracing::info!(
                                    "Skipping store for key='{}': identical result in same scope exists (id: {}, score: {:.4})",
                                    concept_id,
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
        metadata.insert("version".to_string(), Value::String("2".to_string()));
        metadata.insert("kind".to_string(), Value::String(key.kind.as_str().to_string()));
        metadata.insert("canonical".to_string(), Value::String(key.canonical.clone()));
        metadata.insert("query".to_string(), Value::String(key.canonical.clone()));
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
            .inject_concept_with_metadata(concept_id.clone(), query_vector, metadata)
            .await
            .map_err(|e| ResolverError::Cache(format!("inject failed: {}", e)))?;

        tracing::info!(
            "Stored result in semantic cache: provider={}, key='{}'",
            provider,
            concept_id
        );
        Ok(())
    }

    #[cfg(feature = "semantic-cache")]
    pub async fn store_alias_key(
        &self,
        key: &CacheKey,
        results: &[ResolvedResult],
        vector: HVec10240,
    ) -> StdResult<(), ResolverError> {
        let concept_id = key.to_concept_id();
        let mut metadata = HashMap::new();
        metadata.insert("version".to_string(), Value::String("2".to_string()));
        metadata.insert("kind".to_string(), Value::String(key.kind.as_str().to_string()));
        metadata.insert("canonical".to_string(), Value::String(key.canonical.clone()));
        metadata.insert("query".to_string(), Value::String(key.canonical.clone()));
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
            .inject_concept_with_metadata(concept_id, vector, metadata)
            .await
            .map_err(|e| ResolverError::Cache(format!("inject alias failed: {}", e)))?;

        Ok(())
    }

    #[cfg(not(feature = "semantic-cache"))]
    #[allow(dead_code)]
    pub async fn store_alias_key(
        &self,
        _key: &CacheKey,
        _results: &[ResolvedResult],
        _vector: (),
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
        let key = if crate::resolver::is_url(query) {
            CacheKey {
                kind: RequestKind::Url,
                provider: "none".to_string(),
                canonical: canonicalize_url(query),
            }
        } else {
            CacheKey {
                kind: RequestKind::Query,
                provider: "none".to_string(),
                canonical: canonicalize_query(query),
            }
        };

        self.store_alias_key(&key, results, vector).await
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

    #[cfg(feature = "semantic-cache")]
    pub async fn remove(&self, query: &str) -> StdResult<(), ResolverError> {
        let key = CacheKey::from_query(query, None);
        let concept_id = key.to_concept_id();

        self.framework
            .delete_concept(&concept_id)
            .await
            .map_err(|e| ResolverError::Cache(format!("delete failed: {}", e)))?;

        tracing::info!("Removed from semantic cache: key='{}'", concept_id);
        Ok(())
    }

    #[cfg(not(feature = "semantic-cache"))]
    #[allow(dead_code)]
    pub async fn remove(&self, _query: &str) -> StdResult<(), ResolverError> {
        Ok(())
    }

    #[cfg(feature = "semantic-cache")]
    pub async fn has_valid_entry(&self, query: &str) -> bool {
        self.query(query).await.ok().flatten().is_some()
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
