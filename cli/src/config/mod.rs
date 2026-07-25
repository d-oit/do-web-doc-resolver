use crate::semantic_cache::SemanticCacheConfig;
use crate::types::Profile;
use serde::Deserialize;
use std::collections::HashMap;
use std::env;
use std::path::Path;
use thiserror::Error;

use defaults::*;
mod defaults;
mod parsing;

pub use defaults::RoutingProfileConfig;
pub use defaults::routing_profile_defaults;

#[derive(Error, Debug)]
#[allow(dead_code)]
pub enum ConfigError {
    #[error("Failed to read config file: {0}")]
    IoError(#[from] std::io::Error),
    #[error("Failed to parse config file: {0}")]
    ParseError(#[from] toml::de::Error),
    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),
}

#[derive(Debug, Clone, Deserialize)]
pub struct Config {
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
    #[serde(default = "default_max_links")]
    pub max_links: usize,
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
            max_links: default_max_links(),
            providers: HashMap::new(),
        }
    }
}

impl Config {
    pub fn from_file(path: impl AsRef<Path>) -> Result<Self, ConfigError> {
        let content = std::fs::read_to_string(path.as_ref())?;
        let file_config: Config = toml::from_str(&content)?;
        let mut config = Config::default();
        config.merge(file_config);
        Ok(config)
    }

    pub fn merge(&mut self, other: Config) {
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
        merge_value(&mut self.max_links, other.max_links, default_max_links());
        merge_bool(
            &mut self.semantic_cache.enabled,
            other.semantic_cache.enabled,
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
        merge_bool(
            &mut self.routing.prewarm.enabled,
            other.routing.prewarm.enabled,
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
        merge_bool(
            &mut self.disable_routing_memory,
            other.disable_routing_memory,
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

fn merge_value<T: PartialEq>(target: &mut T, value: T, default: T) {
    if value != default {
        *target = value;
    }
}

fn merge_string(target: &mut String, value: String) {
    merge_value(target, value, "info".to_string());
}

fn merge_bool(target: &mut bool, value: bool) {
    if value {
        *target = value;
    }
}

fn merge_option<T>(target: &mut Option<T>, value: Option<T>) {
    if value.is_some() {
        *target = value;
    }
}

fn merge_vec<T>(target: &mut Vec<T>, value: Vec<T>) {
    if !value.is_empty() {
        *target = value;
    }
}

fn merge_map<K, V>(target: &mut HashMap<K, V>, value: HashMap<K, V>)
where
    K: Eq + std::hash::Hash,
{
    for (name, provider_config) in value {
        target.entry(name).or_insert(provider_config);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = Config::default();
        assert_eq!(config.max_chars, 8000);
        assert_eq!(config.min_chars, 200);
        assert_eq!(config.exa_results, 5);
        assert_eq!(config.tavily_results, 3);
        assert_eq!(config.output_limit, 10);
    }

    #[test]
    fn test_api_key_lookup() {
        let config = Config::default();
        assert!(config.api_key("unknown").is_none());
    }

    #[test]
    fn test_skip_providers() {
        let config = Config {
            skip_providers: vec!["exa".to_string(), "tavily".to_string()],
            ..Default::default()
        };

        assert!(config.is_skipped("exa"));
        assert!(config.is_skipped("tavily"));
        assert!(!config.is_skipped("firecrawl"));
    }

    #[test]
    fn test_get_ttl() {
        let config = Config::default();
        assert_eq!(config.get_ttl("firecrawl"), 21600);
        assert_eq!(config.get_ttl("exa"), 14400);
        assert_eq!(config.get_ttl("exa_mcp"), 14400);
        assert_eq!(config.get_ttl("tavily"), 14400);
        assert_eq!(config.get_ttl("serper"), 7200);
        assert_eq!(config.get_ttl("jina"), 7200);
        assert_eq!(config.get_ttl("mistral"), 28800);
        assert_eq!(config.get_ttl("mistral_browser"), 28800);
        assert_eq!(config.get_ttl("mistral_websearch"), 28800);
        assert_eq!(config.get_ttl("duckduckgo"), 3600);
        assert_eq!(config.get_ttl("llms_txt"), 28800);
        assert_eq!(config.get_ttl("synthesis"), 43200);
        assert_eq!(config.get_ttl("unknown"), 3600);
    }
}
