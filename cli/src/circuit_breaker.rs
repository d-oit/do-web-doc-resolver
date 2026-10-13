use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CircuitBreakerState {
    pub failures: usize,
    pub open_until: Option<DateTime<Utc>>,
}

impl CircuitBreakerState {
    pub fn is_open(&self) -> bool {
        self.open_until.map(|t| t > Utc::now()).unwrap_or(false)
    }

    pub fn record_failure(&mut self, threshold: usize, cooldown: Duration) {
        self.failures += 1;
        if self.failures >= threshold {
            // Wall-clock time so the open state survives across invocations
            // through the persisted routing state (Plan 22 B4).
            self.open_until =
                Some(Utc::now() + chrono::Duration::from_std(cooldown).unwrap_or_default());
        }
    }

    pub fn record_success(&mut self) {
        self.failures = 0;
        self.open_until = None;
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CircuitBreakerRegistry {
    providers: HashMap<String, CircuitBreakerState>,
}

impl CircuitBreakerRegistry {
    pub fn is_open(&self, provider: &str) -> bool {
        self.providers
            .get(provider)
            .map(|s| s.is_open())
            .unwrap_or(false)
    }

    pub fn record_failure(&mut self, provider: &str, threshold: usize, cooldown: Duration) {
        self.providers
            .entry(provider.to_string())
            .or_default()
            .record_failure(threshold, cooldown);
    }

    pub fn record_success(&mut self, provider: &str) {
        self.providers
            .entry(provider.to_string())
            .or_default()
            .record_success();
    }

    /// Number of providers whose breaker is currently open.
    pub fn open_count(&self) -> usize {
        self.providers.values().filter(|s| s.is_open()).count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_breaker_opens_at_threshold() {
        let mut registry = CircuitBreakerRegistry::default();
        assert!(!registry.is_open("jina"));

        registry.record_failure("jina", 3, Duration::from_secs(60));
        registry.record_failure("jina", 3, Duration::from_secs(60));
        assert!(!registry.is_open("jina"));

        registry.record_failure("jina", 3, Duration::from_secs(60));
        assert!(registry.is_open("jina"));
        assert_eq!(registry.open_count(), 1);

        registry.record_success("jina");
        assert!(!registry.is_open("jina"));
        assert_eq!(registry.open_count(), 0);
    }

    #[test]
    fn test_expired_open_state_closes() {
        let mut registry = CircuitBreakerRegistry::default();
        registry.providers.insert(
            "jina".to_string(),
            CircuitBreakerState {
                failures: 5,
                open_until: Some(Utc::now() - chrono::Duration::seconds(1)),
            },
        );

        assert!(!registry.is_open("jina"));
    }

    #[test]
    fn test_round_trips_through_json() {
        let mut registry = CircuitBreakerRegistry::default();
        registry.record_failure("serper", 1, Duration::from_secs(120));

        let json = serde_json::to_string(&registry).unwrap();
        let restored: CircuitBreakerRegistry = serde_json::from_str(&json).unwrap();

        assert!(restored.is_open("serper"));
    }
}
