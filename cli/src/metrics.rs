//! Telemetry and metrics for resolution tracking.

use crate::types::ProviderType;
use serde::{Deserialize, Serialize};

/// Metrics for a single provider call
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderMetric {
    pub provider: ProviderType,
    pub latency_ms: u64,
    pub success: bool,
    pub paid: bool,
    pub attempt_index: usize,
    pub quality_score: Option<f32>,
    pub accepted: bool,
    pub skip_reason: Option<String>,
    pub stop_reason: Option<String>,
    pub negative_cache_hit: bool,
    pub circuit_open: bool,
}

/// Aggregated metrics for a resolution request
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ResolveMetrics {
    pub total_latency_ms: u64,
    pub provider_metrics: Vec<ProviderMetric>,
    pub cascade_depth: usize,
    pub paid_usage: bool,
    pub cache_hit: bool,
    pub budget_elapsed_ms: u64,
    pub synthesis_cache_hit: bool,
    pub quality_gate_passed: bool,
    pub quality_gate_score: Option<f32>,
}

impl ResolveMetrics {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn record_cache_hit(&mut self, cache_type: &str) {
        if cache_type == "synthesis" {
            self.synthesis_cache_hit = true;
        }
        self.cache_hit = true;
    }

    /// Record a semantic cache hit with its associated metadata
    pub fn record_semantic_cache_hit(&mut self, latency_ms: u64, score: f64) {
        self.cache_hit = true;
        self.total_latency_ms = latency_ms.max(1);
        // Meaningful scores >= 0.5 are reported to passing the quality gate
        if score >= 0.5 {
            self.quality_gate_passed = true;
            self.quality_gate_score = Some(score as f32);
        }
    }

    pub fn record_gate(&mut self, score: f32) {
        self.quality_gate_passed = true;
        self.quality_gate_score = Some(score);
    }

    pub fn record_provider(&mut self, provider: ProviderType, latency_ms: u64, success: bool) {
        self.record_provider_detailed(
            provider, latency_ms, success, 0, None, success, None, None, false, false,
        );
    }

    #[allow(clippy::too_many_arguments)]
    pub fn record_provider_detailed(
        &mut self,
        provider: ProviderType,
        latency_ms: u64,
        success: bool,
        attempt_index: usize,
        quality_score: Option<f32>,
        accepted: bool,
        skip_reason: Option<String>,
        stop_reason: Option<String>,
        negative_cache_hit: bool,
        circuit_open: bool,
    ) {
        let paid = provider.is_paid();
        if paid && success {
            self.paid_usage = true;
        }
        self.provider_metrics.push(ProviderMetric {
            provider,
            latency_ms,
            success,
            paid,
            attempt_index,
            quality_score,
            accepted,
            skip_reason,
            stop_reason,
            negative_cache_hit,
            circuit_open,
        });
        self.total_latency_ms += latency_ms;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_is_empty() {
        let m = ResolveMetrics::new();
        assert_eq!(m.total_latency_ms, 0);
        assert!(m.provider_metrics.is_empty());
        assert!(!m.cache_hit);
        assert!(!m.quality_gate_passed);
        assert!(m.quality_gate_score.is_none());
    }

    #[test]
    fn test_record_cache_hit() {
        let mut m = ResolveMetrics::new();
        m.record_cache_hit("semantic");
        assert!(m.cache_hit);
        assert!(!m.synthesis_cache_hit);

        let mut m2 = ResolveMetrics::new();
        m2.record_cache_hit("synthesis");
        assert!(m2.cache_hit);
        assert!(m2.synthesis_cache_hit);
    }

    #[test]
    fn test_record_gate_sets_score() {
        let mut m = ResolveMetrics::new();
        m.record_gate(0.88);
        assert!(m.quality_gate_passed);
        assert_eq!(m.quality_gate_score, Some(0.88));
    }

    #[test]
    fn test_record_semantic_cache_hit_threshold() {
        // Scores below 0.5 must not report as passing the quality gate.
        let mut low = ResolveMetrics::new();
        low.record_semantic_cache_hit(42, 0.3);
        assert!(low.cache_hit);
        assert_eq!(low.total_latency_ms, 42);
        assert!(!low.quality_gate_passed);
        assert!(low.quality_gate_score.is_none());

        let mut high = ResolveMetrics::new();
        high.record_semantic_cache_hit(7, 0.9);
        assert!(high.quality_gate_passed);
        assert_eq!(high.quality_gate_score, Some(0.9));
    }

    #[test]
    fn test_record_provider_success_marks_paid_usage() {
        let mut m = ResolveMetrics::new();
        m.record_provider(ProviderType::ExaMcp, 10, true);
        assert!(!m.paid_usage);
        assert_eq!(m.total_latency_ms, 10);
        assert_eq!(m.provider_metrics.len(), 1);
        assert_eq!(m.provider_metrics[0].provider, ProviderType::ExaMcp);
        assert!(m.provider_metrics[0].accepted);
        assert!(!m.provider_metrics[0].paid);
        assert_eq!(m.provider_metrics[0].attempt_index, 0);

        let mut m2 = ResolveMetrics::new();
        m2.record_provider(ProviderType::Exa, 25, true);
        assert!(m2.paid_usage);
        assert!(m2.provider_metrics[0].paid);
    }

    #[test]
    fn test_record_provider_detailed_preserves_fields() {
        let mut m = ResolveMetrics::new();
        m.record_provider_detailed(
            ProviderType::Serper,
            99,
            false,
            3,
            Some(0.4),
            false,
            Some("thin_content".to_string()),
            Some("timeout".to_string()),
            true,
            true,
        );
        assert_eq!(m.provider_metrics.len(), 1);
        let pm = &m.provider_metrics[0];
        assert_eq!(pm.latency_ms, 99);
        assert!(!pm.success);
        assert!(pm.paid);
        assert_eq!(pm.attempt_index, 3);
        assert_eq!(pm.quality_score, Some(0.4));
        assert!(!pm.accepted);
        assert_eq!(pm.skip_reason.as_deref(), Some("thin_content"));
        assert_eq!(pm.stop_reason.as_deref(), Some("timeout"));
        assert!(pm.negative_cache_hit);
        assert!(pm.circuit_open);
        assert_eq!(m.total_latency_ms, 99);
    }

    #[test]
    fn test_metrics_round_trip_serialization() {
        let mut m = ResolveMetrics::new();
        m.record_provider(ProviderType::Jina, 5, true);
        m.record_gate(0.9);
        let json = serde_json::to_string(&m).unwrap();
        let back: ResolveMetrics = serde_json::from_str(&json).unwrap();
        assert_eq!(back.provider_metrics.len(), 1);
        assert_eq!(back.provider_metrics[0].provider, ProviderType::Jina);
        assert!(back.quality_gate_passed);
        assert_eq!(back.quality_gate_score, Some(0.9));
    }
}
