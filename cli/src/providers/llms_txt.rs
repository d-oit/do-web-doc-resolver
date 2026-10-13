//! llms.txt provider.
//!
//! Checks for site-provided structured documentation.

use crate::error::{ResolverError, detect_error_type};
use crate::providers::shared_client::get_client;
use crate::types::ResolvedResult;
use async_trait::async_trait;
use std::result::Result;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use url::Url;

/// llms.txt provider - checks for structured LLM documentation
pub struct LlmsTxtProvider {
    rate_limited: Arc<AtomicBool>,
}

impl LlmsTxtProvider {
    /// Create a new llms.txt provider
    pub fn new() -> Self {
        Self {
            rate_limited: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Check if rate limited
    pub fn is_rate_limited(&self) -> bool {
        self.rate_limited.load(Ordering::SeqCst)
    }

    /// Set rate limit
    pub fn set_rate_limited(&self, limited: bool) {
        self.rate_limited.store(limited, Ordering::SeqCst);
    }
}

impl Default for LlmsTxtProvider {
    fn default() -> Self {
        Self::new()
    }
}

/// Build the `llms.txt` URL for a page, preserving scheme, host and port.
fn build_llms_txt_url(url: &str) -> Result<String, ResolverError> {
    let parsed_url =
        Url::parse(url).map_err(|e| ResolverError::Parse(format!("Invalid URL: {}", e)))?;

    Ok(format!(
        "{}://{}{}/llms.txt",
        parsed_url.scheme(),
        parsed_url.host_str().unwrap_or(""),
        parsed_url
            .port()
            .map(|port| format!(":{}", port))
            .unwrap_or_default()
    ))
}

#[async_trait]
impl crate::providers::UrlProvider for LlmsTxtProvider {
    fn name(&self) -> &str {
        "llms_txt"
    }

    fn is_available(&self) -> bool {
        !self.is_rate_limited()
    }

    async fn extract(&self, url: &str) -> Result<ResolvedResult, ResolverError> {
        if self.is_rate_limited() {
            return Err(ResolverError::RateLimit(
                "llms.txt provider is rate limited".to_string(),
            ));
        }

        // Parse the URL and construct the llms.txt URL. The port must be
        // preserved: `https://example.com:8443/docs` serves llms.txt on
        // :8443, not on the scheme default.
        let llms_txt_url = build_llms_txt_url(url)?;

        let client = get_client();
        let response = client
            .get(&llms_txt_url)
            .send()
            .await
            .map_err(|e| ResolverError::Network(e.to_string()))?;

        if response.status() == 404 {
            return Err(ResolverError::NotFound("llms.txt not found".to_string()));
        }

        if response.status() == 429 {
            self.set_rate_limited(true);
            return Err(ResolverError::RateLimit("Rate limit exceeded".to_string()));
        }

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            return Err(detect_error_type(&error_text));
        }

        let content = response
            .text()
            .await
            .map_err(|e| ResolverError::Parse(e.to_string()))?;

        Ok(ResolvedResult::new(
            llms_txt_url,
            Some(content),
            "llms_txt",
            1.0,
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::providers::UrlProvider;

    #[test]
    fn test_provider_name() {
        let provider = LlmsTxtProvider::new();
        assert_eq!(provider.name(), "llms_txt");
    }

    #[test]
    fn test_build_llms_txt_url_preserves_port() {
        assert_eq!(
            build_llms_txt_url("https://example.com:8443/docs").unwrap(),
            "https://example.com:8443/llms.txt"
        );
    }

    #[test]
    fn test_build_llms_txt_url_without_port() {
        assert_eq!(
            build_llms_txt_url("https://example.com/docs").unwrap(),
            "https://example.com/llms.txt"
        );
    }

    #[test]
    fn test_build_llms_txt_url_rejects_invalid_url() {
        assert!(build_llms_txt_url("not a url").is_err());
    }
}
