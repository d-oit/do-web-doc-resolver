use crate::semantic_cache::SemanticCacheConfig;
use crate::types::Profile;
use serde::Deserialize;
use std::collections::HashMap;
use std::env;
use std::path::Path;
use thiserror::Error;

use defaults::*;
mod defaults;
mod merge;
mod parsing;
use merge::{merge_explicit_bool, merge_map, merge_option, merge_string, merge_value, merge_vec};

pub use defaults::RoutingProfileConfig;
pub use defaults::routing_profile_defaults;

#[derive(Error, Debug)]
pub enum ConfigError {
    #[error("Failed to read config file: {0}")]
    IoError(#[from] std::io::Error),
    #[error("Failed to parse config file: {0}")]
    ParseError(#[from] toml::de::Error),
}

/// Boolean config keys whose TOML presence must be tracked so that
/// `enabled = false` can override a `true` default.
///
/// This is a hand-maintained list, so **adding a default-on boolean config
/// option means adding its dotted path here too.** `test_config_file_can_disable_
/// default_on_features` covers every entry and will not catch a new field that
/// was never registered, so treat a new `enabled` flag as requiring both a
/// registry entry and a test assertion.
const EXPLICIT_BOOL_KEYS: &[&str] = &[
    "semantic_cache.enabled",
    "cache.synthesis.enabled",
    "routing.prewarm.enabled",
    "disable_routing_memory",
];

/// Set of explicitly-present boolean keys, tracked as `a.b.c` dotted paths.
pub type ExplicitBools = std::collections::BTreeSet<String>;

/// Resolve a dotted path (e.g. `routing.prewarm.enabled`) inside a TOML table.
fn lookup_dotted<'a>(table: &'a toml::Table, key: &str) -> Option<&'a toml::Value> {
    let mut segments = key.split('.');
    let first = segments.next()?;
    let mut cursor = table.get(first)?;

    for segment in segments {
        cursor = cursor.as_table()?.get(segment)?;
    }

    Some(cursor)
}

/// Record which of [`EXPLICIT_BOOL_KEYS`] the parsed TOML actually specified.
fn collect_explicit_bools(table: &toml::Table) -> ExplicitBools {
    let mut out = ExplicitBools::new();
    for key in EXPLICIT_BOOL_KEYS {
        if lookup_dotted(table, key).is_some_and(toml::Value::is_bool) {
            out.insert((*key).to_string());
        }
    }
    out
}

#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    /// Not user-facing: records which boolean keys the source config set
    /// explicitly, so `enabled = false` can override a `true` default.
    #[serde(skip)]
    pub explicit_bools: ExplicitBools,
    #[serde(default = "default_max_chars")]
    pub max_chars: usize,
    #[serde(default = "default_min_chars")]
    pub min_chars: usize,
    #[serde(default = "default_exa_results")]
    pub exa_results: usize,
    #[serde(default = "default_tavily_results")]
    pub tavily_results: usize,
    #[serde(default = "default_output_limit")]
    pub output_limit: usize,
    #[serde(default)]
    pub log_level: String,
    #[serde(default)]
    pub skip_providers: Vec<String>,
    #[serde(default)]
    pub providers_order: Vec<String>,
    #[serde(default)]
    pub semantic_cache: SemanticCacheConfig,
    #[serde(default)]
    pub cache: CacheConfig,
    #[serde(default)]
    pub routing: RoutingConfig,
    #[serde(default)]
    pub profile: Profile,
    pub quality_threshold: Option<f32>,
    pub max_provider_attempts: Option<usize>,
    pub max_paid_attempts: Option<usize>,
    pub max_total_latency_ms: Option<u64>,
    #[serde(default)]
    pub disable_routing_memory: bool,
    #[serde(default = "default_negative_cache_ttl")]
    pub negative_cache_ttl_secs: u64,
    #[serde(default = "default_error_cache_ttl")]
    pub error_cache_ttl_secs: u64,
    #[serde(default = "default_circuit_breaker_threshold")]
    pub circuit_breaker_threshold: u32,
    #[serde(default = "default_circuit_breaker_cooldown")]
    pub circuit_breaker_cooldown_secs: u64,
    #[serde(default)]
    pub providers: HashMap<String, ProviderConfig>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct ProviderConfig {
    pub rate_limit: Option<RateLimitConfig>,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct RateLimitConfig {
    pub requests_per_second: f64,
    #[serde(default = "default_burst")]
    pub burst: f64,
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct RoutingConfig {
    pub min_free_quality_to_skip_paid: Option<f32>,
    #[serde(default)]
    pub prewarm: PrewarmConfig,
}

#[derive(Debug, Clone, Deserialize)]
pub struct PrewarmConfig {
    #[serde(default = "default_prewarm_enabled")]
    pub enabled: bool,
    #[serde(default = "default_prewarm_top_n_domains")]
    pub top_n_domains: usize,
    #[serde(default = "default_prewarm_max_concurrency")]
    pub max_concurrency: usize,
}

impl Default for PrewarmConfig {
    fn default() -> Self {
        Self {
            enabled: default_prewarm_enabled(),
            top_n_domains: default_prewarm_top_n_domains(),
            max_concurrency: default_prewarm_max_concurrency(),
        }
    }
}

#[derive(Debug, Clone, Deserialize, Default)]
pub struct CacheConfig {
    #[serde(default)]
    pub synthesis: SynthesisCacheConfig,
    #[serde(default)]
    pub ttl: CacheTtlConfig,
}

#[derive(Debug, Clone, Deserialize)]
pub struct SynthesisCacheConfig {
    #[serde(default = "default_synthesis_cache_enabled")]
    pub enabled: bool,
    #[serde(default = "default_synthesis_cache_ttl")]
    pub ttl: u64,
}

impl Default for SynthesisCacheConfig {
    fn default() -> Self {
        Self {
            enabled: default_synthesis_cache_enabled(),
            ttl: default_synthesis_cache_ttl(),
        }
    }
}

#[derive(Debug, Clone, Deserialize)]
pub struct CacheTtlConfig {
    #[serde(default = "default_ttl_firecrawl")]
    pub firecrawl: u64,
    #[serde(default = "default_ttl_exa")]
    pub exa: u64,
    #[serde(default = "default_ttl_tavily")]
    pub tavily: u64,
    #[serde(default = "default_ttl_serper")]
    pub serper: u64,
    #[serde(default = "default_ttl_jina")]
    pub jina: u64,
    #[serde(default = "default_ttl_mistral")]
    pub mistral: u64,
    #[serde(default = "default_ttl_duckduckgo")]
    pub duckduckgo: u64,
    #[serde(default = "default_ttl_llms_txt")]
    pub llms_txt: u64,
    #[serde(default = "default_ttl_synthesis")]
    pub synthesis: u64,
    #[serde(default = "default_ttl_default")]
    pub default: u64,
}

impl Default for CacheTtlConfig {
    fn default() -> Self {
        Self {
            firecrawl: default_ttl_firecrawl(),
            exa: default_ttl_exa(),
            tavily: default_ttl_tavily(),
            serper: default_ttl_serper(),
            jina: default_ttl_jina(),
            mistral: default_ttl_mistral(),
            duckduckgo: default_ttl_duckduckgo(),
            llms_txt: default_ttl_llms_txt(),
            synthesis: default_ttl_synthesis(),
            default: default_ttl_default(),
        }
    }
}

impl Default for Config {
    fn default() -> Self {
        Self {
            max_chars: default_max_chars(),
            min_chars: default_min_chars(),
            exa_results: default_exa_results(),
            tavily_results: default_tavily_results(),
            explicit_bools: ExplicitBools::new(),
            output_limit: default_output_limit(),
            log_level: "info".to_string(),
            skip_providers: Vec::new(),
            providers_order: Vec::new(),
            semantic_cache: SemanticCacheConfig::default(),
            cache: CacheConfig::default(),
            routing: RoutingConfig::default(),
            profile: Profile::Balanced,
            quality_threshold: None,
            max_provider_attempts: None,
            max_paid_attempts: None,
            max_total_latency_ms: None,
            disable_routing_memory: false,
            negative_cache_ttl_secs: default_negative_cache_ttl(),
            error_cache_ttl_secs: default_error_cache_ttl(),
            circuit_breaker_threshold: default_circuit_breaker_threshold(),
            circuit_breaker_cooldown_secs: default_circuit_breaker_cooldown(),
            providers: HashMap::new(),
        }
    }
}

impl Config {
    pub fn from_file(path: impl AsRef<Path>) -> Result<Self, ConfigError> {
        let content = std::fs::read_to_string(path.as_ref())?;

        // Parse twice: once to learn which boolean keys the file actually set,
        // and once to build the typed config.
        let value: toml::Value = toml::from_str(&content)?;
        let explicit_bools = value
            .as_table()
            .map(collect_explicit_bools)
            .unwrap_or_default();

        let mut file_config: Config = toml::from_str(&content)?;
        file_config.explicit_bools = explicit_bools;

        let mut config = Config::default();
        config.merge(file_config);
        Ok(config)
    }

    pub fn merge(&mut self, other: Config) {
        // Carry forward which boolean keys were explicit, so a merged-in file
        // keeps its ability to turn a `true` default off through later merges.
        self.explicit_bools
            .extend(other.explicit_bools.iter().cloned());

        merge_value(&mut self.max_chars, other.max_chars, default_max_chars());
        merge_value(&mut self.min_chars, other.min_chars, default_min_chars());
        merge_value(
            &mut self.exa_results,
            other.exa_results,
            default_exa_results(),
        );
        merge_value(
            &mut self.tavily_results,
            other.tavily_results,
            default_tavily_results(),
        );
        merge_value(
            &mut self.output_limit,
            other.output_limit,
            default_output_limit(),
        );
        merge_string(&mut self.log_level, other.log_level);
        merge_vec(&mut self.skip_providers, other.skip_providers);
        merge_vec(&mut self.providers_order, other.providers_order);
        merge_value(
            &mut self.negative_cache_ttl_secs,
            other.negative_cache_ttl_secs,
            default_negative_cache_ttl(),
        );
        merge_value(
            &mut self.error_cache_ttl_secs,
            other.error_cache_ttl_secs,
            default_error_cache_ttl(),
        );
        merge_value(
            &mut self.circuit_breaker_threshold,
            other.circuit_breaker_threshold,
            default_circuit_breaker_threshold(),
        );
        merge_value(
            &mut self.circuit_breaker_cooldown_secs,
            other.circuit_breaker_cooldown_secs,
            default_circuit_breaker_cooldown(),
        );
        merge_explicit_bool(
            &mut self.semantic_cache.enabled,
            other.semantic_cache.enabled,
            "semantic_cache.enabled",
            &other.explicit_bools,
        );
        merge_value(
            &mut self.semantic_cache.path,
            other.semantic_cache.path,
            ".do-wdr_cache".to_string(),
        );
        merge_value(
            &mut self.semantic_cache.threshold,
            other.semantic_cache.threshold,
            0.85,
        );
        merge_value(
            &mut self.semantic_cache.max_entries,
            other.semantic_cache.max_entries,
            10000,
        );
        merge_value(
            &mut self.cache.ttl.firecrawl,
            other.cache.ttl.firecrawl,
            default_ttl_firecrawl(),
        );
        merge_value(
            &mut self.cache.ttl.exa,
            other.cache.ttl.exa,
            default_ttl_exa(),
        );
        merge_value(
            &mut self.cache.ttl.tavily,
            other.cache.ttl.tavily,
            default_ttl_tavily(),
        );
        merge_value(
            &mut self.cache.ttl.serper,
            other.cache.ttl.serper,
            default_ttl_serper(),
        );
        merge_value(
            &mut self.cache.ttl.jina,
            other.cache.ttl.jina,
            default_ttl_jina(),
        );
        merge_value(
            &mut self.cache.ttl.mistral,
            other.cache.ttl.mistral,
            default_ttl_mistral(),
        );
        merge_value(
            &mut self.cache.ttl.duckduckgo,
            other.cache.ttl.duckduckgo,
            default_ttl_duckduckgo(),
        );
        merge_value(
            &mut self.cache.ttl.llms_txt,
            other.cache.ttl.llms_txt,
            default_ttl_llms_txt(),
        );
        merge_value(
            &mut self.cache.ttl.synthesis,
            other.cache.ttl.synthesis,
            default_ttl_synthesis(),
        );
        merge_value(
            &mut self.cache.ttl.default,
            other.cache.ttl.default,
            default_ttl_default(),
        );
        merge_value(&mut self.profile, other.profile, Profile::Balanced);
        merge_option(&mut self.quality_threshold, other.quality_threshold);
        merge_option(
            &mut self.routing.min_free_quality_to_skip_paid,
            other.routing.min_free_quality_to_skip_paid,
        );
        merge_explicit_bool(
            &mut self.routing.prewarm.enabled,
            other.routing.prewarm.enabled,
            "routing.prewarm.enabled",
            &other.explicit_bools,
        );
        merge_explicit_bool(
            &mut self.cache.synthesis.enabled,
            other.cache.synthesis.enabled,
            "cache.synthesis.enabled",
            &other.explicit_bools,
        );
        merge_value(
            &mut self.cache.synthesis.ttl,
            other.cache.synthesis.ttl,
            default_synthesis_cache_ttl(),
        );
        merge_value(
            &mut self.routing.prewarm.top_n_domains,
            other.routing.prewarm.top_n_domains,
            default_prewarm_top_n_domains(),
        );
        merge_value(
            &mut self.routing.prewarm.max_concurrency,
            other.routing.prewarm.max_concurrency,
            default_prewarm_max_concurrency(),
        );
        merge_option(&mut self.max_provider_attempts, other.max_provider_attempts);
        merge_option(&mut self.max_paid_attempts, other.max_paid_attempts);
        merge_option(&mut self.max_total_latency_ms, other.max_total_latency_ms);
        merge_explicit_bool(
            &mut self.disable_routing_memory,
            other.disable_routing_memory,
            "disable_routing_memory",
            &other.explicit_bools,
        );
        merge_map(&mut self.providers, other.providers);
    }

    pub fn load() -> Self {
        let mut config = Config::default();
        parsing::apply_env_overrides(&mut config);
        config
    }

    pub fn api_key(&self, provider: &str) -> Option<String> {
        let key_name = match provider {
            "exa" | "exa_mcp" => "EXA_API_KEY",
            "tavily" => "TAVILY_API_KEY",
            "serper" => "SERPER_API_KEY",
            "firecrawl" => "FIRECRAWL_API_KEY",
            "mistral" | "mistral_browser" | "mistral_websearch" => "MISTRAL_API_KEY",
            _ => return None,
        };
        env::var(key_name).ok()
    }

    pub fn is_skipped(&self, provider: &str) -> bool {
        self.skip_providers.iter().any(|p| p == provider)
    }

    pub fn get_ttl(&self, provider: &str) -> u64 {
        match provider {
            "firecrawl" => self.cache.ttl.firecrawl,
            "exa" | "exa_mcp" => self.cache.ttl.exa,
            "tavily" => self.cache.ttl.tavily,
            "serper" => self.cache.ttl.serper,
            "jina" => self.cache.ttl.jina,
            "mistral" | "mistral_browser" | "mistral_websearch" => self.cache.ttl.mistral,
            "duckduckgo" => self.cache.ttl.duckduckgo,
            "llms_txt" => self.cache.ttl.llms_txt,
            "synthesis" => self.cache.ttl.synthesis,
            _ => self.cache.ttl.default,
        }
    }
}

// Unit tests live in their own module file so this one stays under the
// 500-line source limit documented in AGENTS.md.
#[cfg(test)]
#[path = "tests.rs"]
mod tests;
