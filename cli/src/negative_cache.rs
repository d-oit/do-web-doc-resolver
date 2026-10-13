use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::Duration;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NegativeCacheEntry {
    pub provider: String,
    pub reason: String,
    pub expires_at: DateTime<Utc>,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct NegativeCache {
    entries: HashMap<String, NegativeCacheEntry>,
}

impl NegativeCache {
    pub fn make_key(target: &str, provider: &str) -> String {
        format!("{provider}::{target}")
    }

    pub fn should_skip(&self, target: &str, provider: &str) -> bool {
        let key = Self::make_key(target, provider);
        self.entries
            .get(&key)
            .map(|entry| entry.expires_at > Utc::now())
            .unwrap_or(false)
    }

    pub fn insert(
        &mut self,
        target: &str,
        provider: &str,
        reason: impl Into<String>,
        ttl: Duration,
        metadata: HashMap<String, String>,
    ) {
        let key = Self::make_key(target, provider);
        self.entries.insert(
            key,
            NegativeCacheEntry {
                provider: provider.to_string(),
                reason: reason.into(),
                // Wall-clock time, not `Instant`: the cache is persisted across
                // invocations and `Instant` has no serializable representation.
                expires_at: Utc::now() + chrono::Duration::from_std(ttl).unwrap_or_default(),
                metadata,
            },
        );
    }

    /// Drop entries whose TTL has passed. Called on load and before persisting
    /// so a long-lived state file cannot grow without bound.
    pub fn prune_expired(&mut self) {
        let now = Utc::now();
        self.entries.retain(|_, entry| entry.expires_at > now);
    }

    /// Number of live (non-expired) entries.
    pub fn len(&self) -> usize {
        let now = Utc::now();
        self.entries
            .values()
            .filter(|entry| entry.expires_at > now)
            .count()
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_inserted_entry_is_skipped_until_ttl_expires() {
        let mut cache = NegativeCache::default();
        cache.insert(
            "https://example.com",
            "jina",
            "bot challenge",
            Duration::from_secs(300),
            HashMap::new(),
        );

        assert!(cache.should_skip("https://example.com", "jina"));
        assert!(!cache.should_skip("https://example.com", "firecrawl"));
    }

    #[test]
    fn test_expired_entry_is_not_skipped_and_is_pruned() {
        let mut cache = NegativeCache::default();
        cache.entries.insert(
            NegativeCache::make_key("target", "jina"),
            NegativeCacheEntry {
                provider: "jina".to_string(),
                reason: "transient".to_string(),
                expires_at: Utc::now() - chrono::Duration::seconds(1),
                metadata: HashMap::new(),
            },
        );

        assert!(!cache.should_skip("target", "jina"));
        assert_eq!(cache.len(), 0);

        cache.prune_expired();
        assert!(cache.entries.is_empty());
    }

    #[test]
    fn test_round_trips_through_json() {
        let mut cache = NegativeCache::default();
        cache.insert(
            "https://example.com",
            "serper",
            "quota",
            Duration::from_secs(60),
            HashMap::from([("status".to_string(), "429".to_string())]),
        );

        let json = serde_json::to_string(&cache).unwrap();
        let restored: NegativeCache = serde_json::from_str(&json).unwrap();

        assert!(restored.should_skip("https://example.com", "serper"));
    }
}
