//! Cross-invocation persistence for routing state (Plan 22 B4).
//!
//! Routing memory, the negative cache and circuit breakers used to be
//! process-local: every CLI invocation started empty, so `prewarm` could
//! never see a tracked domain (it always early-returned), and a provider
//! that failed repeatedly was retried from scratch on the next run. The
//! state is written to `<semantic-cache-dir>/routing_state.json` after each
//! resolve and loaded at startup.

use crate::circuit_breaker::CircuitBreakerRegistry;
use crate::negative_cache::NegativeCache;
use crate::routing_memory::RoutingMemory;
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};

/// File name inside the cache directory configured as `semantic_cache.path`.
pub const STATE_FILE_NAME: &str = "routing_state.json";

/// Serializable snapshot of the three process-local routing components.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct PersistedState {
    #[serde(default)]
    pub routing_memory: RoutingMemory,
    #[serde(default)]
    pub negative_cache: NegativeCache,
    #[serde(default)]
    pub circuit_breakers: CircuitBreakerRegistry,
}

impl PersistedState {
    /// Path of the state file inside `cache_dir`.
    pub fn path_in(cache_dir: &str) -> PathBuf {
        Path::new(cache_dir).join(STATE_FILE_NAME)
    }

    /// Load state from the cache directory, returning empty state on any error.
    pub fn load(cache_dir: &str) -> Self {
        Self::load_from(&Self::path_in(cache_dir))
    }

    /// Load state from an explicit path. A missing or corrupt file is not an
    /// error: routing state is an optimization, never required for correctness.
    pub fn load_from(path: &Path) -> Self {
        let Ok(raw) = std::fs::read_to_string(path) else {
            return Self::default();
        };
        match serde_json::from_str::<Self>(&raw) {
            Ok(mut state) => {
                state.negative_cache.prune_expired();
                state
            }
            Err(err) => {
                tracing::debug!(
                    "Ignoring unreadable routing state at {}: {}",
                    path.display(),
                    err
                );
                Self::default()
            }
        }
    }

    /// Persist state into the cache directory.
    pub fn save(&self, cache_dir: &str) -> std::io::Result<()> {
        self.save_to(&Self::path_in(cache_dir))
    }

    /// Persist state to an explicit path, creating parent directories.
    pub fn save_to(&self, path: &Path) -> std::io::Result<()> {
        // No `if let ... &&` here: let-chains are not stable on the CI
        // toolchain (Rust 1.85).
        if let Some(parent) = path.parent().filter(|p| !p.as_os_str().is_empty()) {
            std::fs::create_dir_all(parent)?;
        }
        let json = serde_json::to_string_pretty(self).map_err(std::io::Error::other)?;
        std::fs::write(path, json)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use std::time::Duration;

    #[test]
    fn test_load_missing_file_returns_defaults() {
        let state = PersistedState::load_from(Path::new("/nonexistent/do-wdr/routing_state.json"));

        assert_eq!(state.routing_memory.provider_count("example.com"), 0);
        assert!(state.negative_cache.is_empty());
    }

    #[test]
    fn test_load_corrupt_file_returns_defaults() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join(STATE_FILE_NAME);
        std::fs::write(&path, "{ not json").unwrap();

        let state = PersistedState::load_from(&path);

        assert!(state.negative_cache.is_empty());
    }

    #[test]
    fn test_round_trip_preserves_all_three_components() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join(STATE_FILE_NAME);

        let mut memory = RoutingMemory::default();
        memory.record("docs.rs", "jina", true, 120, 0.9);

        let mut negative_cache = NegativeCache::default();
        negative_cache.insert(
            "https://blocked.example.com",
            "firecrawl",
            "bot challenge",
            Duration::from_secs(300),
            HashMap::new(),
        );

        let mut breakers = CircuitBreakerRegistry::default();
        breakers.record_failure("serper", 1, Duration::from_secs(300));

        let state = PersistedState {
            routing_memory: memory,
            negative_cache,
            circuit_breakers: breakers,
        };
        state.save_to(&path).unwrap();

        let restored = PersistedState::load_from(&path);

        assert_eq!(restored.routing_memory.provider_count("docs.rs"), 1);
        assert!(
            restored
                .negative_cache
                .should_skip("https://blocked.example.com", "firecrawl")
        );
        assert!(restored.circuit_breakers.is_open("serper"));
    }

    #[test]
    fn test_save_creates_missing_cache_directory() {
        let dir = tempfile::tempdir().unwrap();
        let nested = dir.path().join("does/not/exist");

        PersistedState::default()
            .save_to(&nested.join(STATE_FILE_NAME))
            .unwrap();

        assert!(nested.join(STATE_FILE_NAME).is_file());
    }

    #[test]
    fn test_load_prunes_expired_negative_cache_entries() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join(STATE_FILE_NAME);

        let mut negative_cache = NegativeCache::default();
        negative_cache.insert(
            "stale",
            "jina",
            "old",
            Duration::from_secs(0),
            HashMap::new(),
        );

        PersistedState {
            negative_cache,
            ..Default::default()
        }
        .save_to(&path)
        .unwrap();

        let restored = PersistedState::load_from(&path);
        assert!(restored.negative_cache.is_empty());
    }
}
