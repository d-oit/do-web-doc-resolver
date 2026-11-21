use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

pub const MIN_EVIDENCE: usize = 3;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Outcome {
    Success,
    LowQuality,
    NoResult,
    Blocked,
    RateLimited,
    Timeout,
    AuthError,
    ServerError,
    TransportError,
    Unknown,
}

impl Outcome {
    #[must_use]
    pub fn is_content(self) -> bool {
        matches!(self, Outcome::Success | Outcome::LowQuality)
    }

    #[must_use]
    pub fn is_transport(self) -> bool {
        matches!(
            self,
            Outcome::Blocked
                | Outcome::RateLimited
                | Outcome::Timeout
                | Outcome::AuthError
                | Outcome::ServerError
                | Outcome::TransportError
        )
    }

    #[must_use]
    pub fn from_reason(reason: &str) -> Self {
        match reason {
            "timeout" => Outcome::Timeout,
            "rate_limited" => Outcome::RateLimited,
            "provider_5xx" => Outcome::ServerError,
            "auth_required" => Outcome::AuthError,
            "blocked" | "ssrf_blocked" | "bot_challenge" => Outcome::Blocked,
            "no_result" | "not_found" => Outcome::NoResult,
            "thin_content" | "low_quality" => Outcome::LowQuality,
            "transport_error" | "network_error" => Outcome::TransportError,
            _ => Outcome::Unknown,
        }
    }
}

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct OutcomeCounts {
    #[serde(default)]
    pub success: usize,
    #[serde(default)]
    pub low_quality: usize,
    #[serde(default)]
    pub no_result: usize,
    #[serde(default)]
    pub blocked: usize,
    #[serde(default)]
    pub rate_limited: usize,
    #[serde(default)]
    pub timeout: usize,
    #[serde(default)]
    pub auth_error: usize,
    #[serde(default)]
    pub server_error: usize,
    #[serde(default)]
    pub transport_error: usize,
    #[serde(default)]
    pub unknown: usize,
}

impl OutcomeCounts {
    pub(crate) fn increment(&mut self, outcome: Outcome) {
        let slot = match outcome {
            Outcome::Success => &mut self.success,
            Outcome::LowQuality => &mut self.low_quality,
            Outcome::NoResult => &mut self.no_result,
            Outcome::Blocked => &mut self.blocked,
            Outcome::RateLimited => &mut self.rate_limited,
            Outcome::Timeout => &mut self.timeout,
            Outcome::AuthError => &mut self.auth_error,
            Outcome::ServerError => &mut self.server_error,
            Outcome::TransportError => &mut self.transport_error,
            Outcome::Unknown => &mut self.unknown,
        };
        *slot += 1;
    }

    #[must_use]
    pub fn total(self) -> usize {
        self.success
            + self.low_quality
            + self.no_result
            + self.blocked
            + self.rate_limited
            + self.timeout
            + self.auth_error
            + self.server_error
            + self.transport_error
            + self.unknown
    }

    #[must_use]
    pub fn transport_failures(self) -> usize {
        self.blocked
            + self.rate_limited
            + self.timeout
            + self.auth_error
            + self.server_error
            + self.transport_error
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ProviderStats {
    pub success: usize,
    pub failure: usize,
    #[serde(default)]
    pub outcomes: OutcomeCounts,
    #[serde(default)]
    pub contributed: usize,
    pub avg_latency_ms: f32,
    pub avg_quality: f32,
    pub last_attempted: Option<DateTime<Utc>>,
}

impl ProviderStats {
    #[must_use]
    pub fn content_attempts(&self) -> usize {
        self.success + self.failure
    }

    #[must_use]
    pub fn confidence(&self) -> f64 {
        (self.content_attempts() as f64 / MIN_EVIDENCE as f64).min(1.0)
    }
}

pub(crate) fn merge_stats(target: &mut ProviderStats, source: &ProviderStats) {
    let target_total = target.outcomes.total();
    let source_total = source.outcomes.total();
    target.success += source.success;
    target.failure += source.failure;
    target.contributed += source.contributed;
    target.outcomes.success += source.outcomes.success;
    target.outcomes.low_quality += source.outcomes.low_quality;
    target.outcomes.no_result += source.outcomes.no_result;
    target.outcomes.blocked += source.outcomes.blocked;
    target.outcomes.rate_limited += source.outcomes.rate_limited;
    target.outcomes.timeout += source.outcomes.timeout;
    target.outcomes.auth_error += source.outcomes.auth_error;
    target.outcomes.server_error += source.outcomes.server_error;
    target.outcomes.transport_error += source.outcomes.transport_error;
    target.outcomes.unknown += source.outcomes.unknown;
    let total = target_total + source_total;
    if total > 0 {
        let total_f = total as f32;
        target.avg_latency_ms = (target.avg_latency_ms * target_total as f32
            + source.avg_latency_ms * source_total as f32)
            / total_f;
        target.avg_quality = (target.avg_quality * target_total as f32
            + source.avg_quality * source_total as f32)
            / total_f;
    }
    target.last_attempted = match (target.last_attempted, source.last_attempted) {
        (Some(left), Some(right)) => Some(left.max(right)),
        (left, right) => left.or(right),
    };
}
