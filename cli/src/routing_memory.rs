use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

use crate::routing_context::is_query_context_key;
use crate::routing_outcomes::merge_stats;
pub use crate::routing_outcomes::{MIN_EVIDENCE, Outcome, OutcomeCounts, ProviderStats};

pub const MEMORY_SCHEMA_VERSION: u32 = 2;
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum RoutingMode {
    Off,
    #[default]
    Shadow,
    Active,
}

impl RoutingMode {
    #[must_use]
    pub fn from_env() -> Self {
        match std::env::var("DO_WDR_ROUTING_MODE")
            .unwrap_or_else(|_| "shadow".to_string())
            .to_lowercase()
            .as_str()
        {
            "off" => RoutingMode::Off,
            "active" => RoutingMode::Active,
            _ => RoutingMode::Shadow,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RouteExplanation {
    pub provider: String,
    pub static_rank: usize,
    pub learned_rank: usize,
    pub sample_count: usize,
    pub total_attempts: usize,
    pub confidence: f64,
    pub evidence_gate: f64,
    pub prior: f64,
    pub learned_component: f64,
    pub availability: f64,
    pub blended: f64,
    pub score: f64,
    pub success_rate: Option<f64>,
    pub avg_quality: Option<f32>,
    pub avg_latency_ms: Option<f32>,
    pub outcomes: OutcomeCounts,
    pub transport_failures: usize,
    pub contributed: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingMemory {
    #[serde(default)]
    pub version: u32,
    #[serde(rename = "stats", alias = "domain_stats", default)]
    domain_stats: HashMap<String, HashMap<String, ProviderStats>>,
    #[serde(skip)]
    unsupported_version: bool,
}

impl Default for RoutingMemory {
    fn default() -> Self {
        Self {
            version: MEMORY_SCHEMA_VERSION,
            domain_stats: HashMap::new(),
            unsupported_version: false,
        }
    }
}

impl RoutingMemory {
    /// Migrate a legacy (unversioned) snapshot in place.
    pub fn migrate(&mut self) {
        if self.version > MEMORY_SCHEMA_VERSION {
            tracing::warn!(
                "Routing memory schema {} is newer than supported {}; persistence disabled",
                self.version,
                MEMORY_SCHEMA_VERSION
            );
            self.unsupported_version = true;
            self.domain_stats.clear();
            return;
        }
        if self.version == 0 {
            // Legacy snapshots had no version and no outcome counts. Their
            // success/failure counters remain valid content evidence.
            self.version = MEMORY_SCHEMA_VERSION;
        }
        if let Some(legacy) = self.domain_stats.remove("query") {
            let general = self
                .domain_stats
                .entry("q:v2:general:general:na:none".to_string())
                .or_default();
            for (provider, stats) in legacy {
                general
                    .entry(provider)
                    .and_modify(|current| merge_stats(current, &stats))
                    .or_insert(stats);
            }
        }
    }

    #[must_use]
    pub fn can_persist(&self) -> bool {
        !self.unsupported_version
    }

    #[must_use]
    pub fn schema_version(&self) -> u32 {
        if self.version == 0 { 1 } else { self.version }
    }

    pub fn record(
        &mut self,
        domain: &str,
        provider: &str,
        success: bool,
        latency_ms: u64,
        quality_score: f32,
    ) {
        self.record_outcome(
            domain,
            provider,
            if success {
                Outcome::Success
            } else {
                Outcome::LowQuality
            },
            latency_ms,
            quality_score,
            false,
        );
    }

    #[allow(clippy::too_many_arguments)]
    pub fn record_outcome(
        &mut self,
        domain: &str,
        provider: &str,
        outcome: Outcome,
        latency_ms: u64,
        quality_score: f32,
        contributed: bool,
    ) {
        let providers = self.domain_stats.entry(domain.to_string()).or_default();
        let stats = providers.entry(provider.to_string()).or_default();

        let previous_total = stats.outcomes.total();
        stats.outcomes.increment(outcome);
        let total = stats.outcomes.total();
        let total_f = total as f32;
        stats.avg_latency_ms =
            ((stats.avg_latency_ms * previous_total as f32) + latency_ms as f32) / total_f.max(1.0);
        stats.last_attempted = Some(Utc::now());

        match outcome {
            Outcome::Success => stats.success += 1,
            Outcome::LowQuality => stats.failure += 1,
            _ => {}
        }

        if outcome.is_content() {
            let content_total = stats.success + stats.failure;
            let previous_content = content_total.saturating_sub(1) as f32;
            stats.avg_quality = ((stats.avg_quality * previous_content) + quality_score)
                / (content_total as f32).max(1.0);
        }
        if contributed {
            stats.contributed += 1;
        }
    }

    #[must_use]
    pub fn compute_score(&self, provider: &str, domain: &str) -> f64 {
        let Some(domain_map) = self.domain_stats.get(domain) else {
            return 0.5;
        };
        let Some(stats) = domain_map.get(provider) else {
            return 0.5;
        };
        let attempts = stats.content_attempts();
        if attempts == 0 {
            return 0.5;
        }
        let success_rate = stats.success as f64 / attempts as f64;
        let days_since_last = stats.last_attempted.map_or(0.0, |last| {
            Utc::now().signed_duration_since(last).num_seconds() as f64 / 86400.0
        });
        let quality_factor = 0.5 + 0.5 * stats.avg_quality as f64;
        let recency_weight = (-days_since_last / 7.0).exp();
        (success_rate * quality_factor * recency_weight) * 1000.0
            / (stats.avg_latency_ms as f64).max(1.0)
    }

    fn query_score(&self, key: &str, provider: &str) -> f64 {
        let score = self.compute_score(provider, key);
        let Some(stats) = self.domain_stats.get(key).and_then(|map| map.get(provider)) else {
            return score;
        };
        let total = stats.outcomes.total();
        let availability = if total == 0 {
            1.0
        } else {
            (1.0 - stats.outcomes.transport_failures() as f64 / total as f64).max(0.5)
        };
        score * availability
    }

    fn rank_query(&self, key: &str, providers: &[String]) -> Vec<String> {
        let n = providers.len();
        let mut gated = vec![false; n];
        let mut raw = vec![0.0_f64; n];
        for (index, provider) in providers.iter().enumerate() {
            if let Some(stats) = self.domain_stats.get(key).and_then(|map| map.get(provider)) {
                if stats.content_attempts() >= MIN_EVIDENCE {
                    gated[index] = true;
                    raw[index] = self.query_score(key, provider);
                }
            }
        }
        let max_raw = raw.iter().copied().fold(0.0_f64, f64::max);
        let mut scored: Vec<(usize, f64)> = providers
            .iter()
            .enumerate()
            .map(|(index, provider)| {
                let stats = self.domain_stats.get(key).and_then(|map| map.get(provider));
                let total = stats.map_or(0, |s| s.outcomes.total());
                let availability = if total == 0 {
                    1.0
                } else {
                    stats.map_or(1.0, |s| {
                        (1.0 - s.outcomes.transport_failures() as f64 / total as f64).max(0.0)
                    })
                };
                let weight = if gated[index] { 1.0 } else { 0.0 };
                let prior = if n == 0 {
                    0.3
                } else {
                    0.3 * (1.0 - index as f64 / n as f64)
                };
                let learned = if max_raw > 0.0 && weight > 0.0 {
                    raw[index] / max_raw
                } else {
                    0.0
                };
                let blended =
                    weight * learned + (1.0 - weight) * prior - (1.0 - availability) * 0.5;
                (index, blended)
            })
            .collect();
        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scored
            .into_iter()
            .map(|(index, _)| providers[index].clone())
            .collect()
    }

    pub fn rank_providers(&self, domain: &str, providers: &[String]) -> Vec<String> {
        self.rank_providers_mode(domain, providers, RoutingMode::Active)
    }

    pub fn rank_providers_mode(
        &self,
        domain: &str,
        providers: &[String],
        mode: RoutingMode,
    ) -> Vec<String> {
        match mode {
            RoutingMode::Off => providers.to_vec(),
            RoutingMode::Shadow if is_query_context_key(domain) => providers.to_vec(),
            _ if is_query_context_key(domain) => self.rank_query(domain, providers),
            _ if mode == RoutingMode::Shadow => providers.to_vec(),
            _ => {
                let mut scores: Vec<(&String, f64)> = providers
                    .iter()
                    .map(|p| (p, self.compute_score(p, domain)))
                    .collect();
                scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
                scores.into_iter().map(|(p, _)| p.clone()).collect()
            }
        }
    }

    pub fn explain(&self, key: &str, providers: &[String]) -> Vec<RouteExplanation> {
        let active = self.rank_providers_mode(key, providers, RoutingMode::Active);
        let learned_rank: HashMap<&String, usize> = active
            .iter()
            .enumerate()
            .map(|(index, provider)| (provider, index + 1))
            .collect();
        let n = providers.len();
        let mut gated = vec![false; n];
        let mut raw = vec![0.0_f64; n];
        for (index, provider) in providers.iter().enumerate() {
            if let Some(stats) = self.domain_stats.get(key).and_then(|map| map.get(provider)) {
                if stats.content_attempts() >= MIN_EVIDENCE {
                    gated[index] = true;
                    raw[index] = self.query_score(key, provider);
                }
            }
        }
        let max_raw = raw.iter().copied().fold(0.0_f64, f64::max);
        providers
            .iter()
            .enumerate()
            .map(|(index, provider)| {
                let stats = self.domain_stats.get(key).and_then(|map| map.get(provider));
                let total = stats.map_or(0, |s| s.outcomes.total());
                let availability = if total == 0 {
                    1.0
                } else {
                    stats.map_or(1.0, |s| {
                        (1.0 - s.outcomes.transport_failures() as f64 / total as f64).max(0.0)
                    })
                };
                let weight = if gated[index] { 1.0 } else { 0.0 };
                let prior = if n == 0 {
                    0.3
                } else {
                    0.3 * (1.0 - index as f64 / n as f64)
                };
                let learned = if max_raw > 0.0 && weight > 0.0 {
                    raw[index] / max_raw
                } else {
                    0.0
                };
                let blended =
                    weight * learned + (1.0 - weight) * prior - (1.0 - availability) * 0.5;
                RouteExplanation {
                    provider: provider.clone(),
                    static_rank: index + 1,
                    learned_rank: *learned_rank.get(provider).unwrap_or(&(index + 1)),
                    sample_count: stats.map_or(0, ProviderStats::content_attempts),
                    total_attempts: total,
                    confidence: stats.map_or(0.0, ProviderStats::confidence),
                    evidence_gate: weight,
                    prior,
                    learned_component: learned,
                    availability,
                    blended,
                    score: stats.map_or(0.5, |_| self.query_score(key, provider)),
                    success_rate: stats.and_then(|s| {
                        (s.content_attempts() > 0)
                            .then(|| s.success as f64 / s.content_attempts() as f64)
                    }),
                    avg_quality: stats.map(|s| s.avg_quality),
                    avg_latency_ms: stats.map(|s| s.avg_latency_ms),
                    outcomes: stats.map_or_else(OutcomeCounts::default, |s| s.outcomes),
                    transport_failures: stats.map_or(0, |s| s.outcomes.transport_failures()),
                    contributed: stats.map_or(0, |s| s.contributed),
                }
            })
            .collect()
    }

    #[must_use]
    pub fn provider_count(&self, domain: &str) -> usize {
        self.domain_stats.get(domain).map_or(0, HashMap::len)
    }

    #[must_use]
    pub fn top_domains(&self, n: usize) -> Vec<String> {
        let mut domains: Vec<(String, usize)> = self
            .domain_stats
            .iter()
            .map(|(domain, providers)| {
                let total: usize = providers
                    .values()
                    .map(|s| s.outcomes.total().max(s.content_attempts()))
                    .sum();
                (domain.clone(), total)
            })
            .collect();
        domains.sort_unstable_by_key(|b| std::cmp::Reverse(b.1));
        domains.into_iter().take(n).map(|(d, _)| d).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn legacy_snapshot_migrates() {
        let json = r#"{"domain_stats":{"docs.rs":{"jina":{"success":3,"failure":1,"avg_latency_ms":120.0,"avg_quality":0.8,"last_attempted":null}}}}"#;
        let mut memory: RoutingMemory = serde_json::from_str(json).unwrap();
        memory.migrate();
        assert_eq!(memory.schema_version(), MEMORY_SCHEMA_VERSION);
        let stats = memory.domain_stats["docs.rs"]["jina"].clone();
        assert_eq!(stats.content_attempts(), 4);
        assert_eq!(stats.outcomes.success, 0, "legacy counts stay legacy-valid");
    }

    #[test]
    fn blocked_does_not_increment_content_failure() {
        let mut memory = RoutingMemory::default();
        for _ in 0..3 {
            memory.record_outcome(
                "q:v2:general:rust:rust:none",
                "exa",
                Outcome::Blocked,
                100,
                0.0,
                false,
            );
        }
        let stats = &memory.domain_stats["q:v2:general:rust:rust:none"]["exa"];
        assert_eq!(stats.failure, 0);
        assert_eq!(stats.outcomes.blocked, 3);
        assert_eq!(stats.outcomes.transport_failures(), 3);
    }

    #[test]
    fn evidence_gate_preserves_order_below_threshold() {
        let mut memory = RoutingMemory::default();
        memory.record_outcome(
            "q:v2:general:rust:rust:none",
            "last",
            Outcome::Success,
            10,
            0.99,
            false,
        );
        let providers = vec!["first".to_string(), "last".to_string()];
        assert_eq!(
            memory.rank_providers_mode(
                "q:v2:general:rust:rust:none",
                &providers,
                RoutingMode::Active
            ),
            providers
        );
    }

    #[test]
    fn shadow_keeps_query_order_but_explain_shows_learning() {
        let key = "q:v2:documentation:python:python:none";
        let mut memory = RoutingMemory::default();
        for _ in 0..3 {
            memory.record_outcome(key, "exa_mcp", Outcome::Blocked, 50, 0.0, false);
            memory.record_outcome(key, "tavily", Outcome::Success, 100, 0.9, true);
        }
        let providers = vec!["exa_mcp".to_string(), "tavily".to_string()];
        assert_eq!(
            memory.rank_providers_mode(key, &providers, RoutingMode::Shadow),
            providers
        );
        let explained = memory.explain(key, &providers);
        let tavily = explained
            .iter()
            .find(|row| row.provider == "tavily")
            .unwrap();
        assert_eq!(tavily.learned_rank, 1);
        assert_eq!(tavily.sample_count, 3);
        assert!((tavily.confidence - 1.0).abs() < 1e-9);
    }
}
