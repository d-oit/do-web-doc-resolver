//! Async link validation for research results.

use crate::ssrf::{create_safe_client_builder, is_safe_url};
use futures::future::join_all;
use std::time::Duration;

/// Validate a list of links using HTTP HEAD requests
pub async fn validate_links(links: &[String]) -> Vec<String> {
    let client = create_safe_client_builder(Duration::from_secs(5))
        .build()
        .unwrap_or_default();

    let mut futures = Vec::new();
    for link in links {
        if !is_safe_url(link) {
            continue;
        }
        let client = client.clone();
        let link = link.clone();
        futures.push(tokio::spawn(async move {
            match client.head(&link).send().await {
                Ok(resp) if resp.status().is_success() => Some(link),
                _ => None,
            }
        }));
    }

    let results = join_all(futures).await;
    results
        .into_iter()
        .filter_map(|r| r.ok().flatten())
        .collect()
}
