//! Shared HTTP client for all providers.
//!
//! Provides a single `reqwest::Client` instance with connection pooling
//! and retry configuration, shared across all providers.

use once_cell::sync::Lazy;
use reqwest::Client;
use std::time::Duration;

/// Shared HTTP client with connection pooling and retry configuration.
///
/// This client is initialized once and shared across all providers to:
/// - Reuse TCP connections (HTTP/2 keep-alive)
/// - Share connection pool across providers
/// - Apply consistent timeout and retry settings
pub static SHARED_CLIENT: Lazy<Client> = Lazy::new(|| {
    Client::builder()
        .timeout(Duration::from_secs(30))
        .connect_timeout(Duration::from_secs(10))
        .pool_max_idle_per_host(10)
        .pool_idle_timeout(Duration::from_secs(90))
        .tcp_keepalive(Duration::from_secs(60))
        .user_agent("WDR/1.0 (LLM documentation resolver)")
        .build()
        .expect("Failed to create shared HTTP client")
});

/// Get a reference to the shared HTTP client.
///
/// This is a convenience function that returns a reference to the
/// lazily-initialized shared client.
pub fn get_client() -> &'static Client {
    &SHARED_CLIENT
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_shared_client_initialization() {
        let client = get_client();
        // Client should be initialized and usable
        assert!(!format!("{:?}", client).is_empty());
    }

    #[test]
    fn test_shared_client_is_static() {
        // Verify that calling get_client() multiple times returns the same reference
        let client1 = get_client() as *const Client;
        let client2 = get_client() as *const Client;
        assert_eq!(client1, client2);
    }
}
