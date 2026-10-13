//! Async link validation for research results.

use crate::resolver::is_url;
use futures::future::join_all;
use reqwest::Client;
use reqwest::header::RANGE;
use std::sync::OnceLock;
use std::time::Duration;

static SHARED_CLIENT: OnceLock<Client> = OnceLock::new();

/// Get or initialize the shared HTTP client
fn get_client() -> &'static Client {
    SHARED_CLIENT.get_or_init(|| {
        Client::builder()
            .timeout(Duration::from_secs(5))
            .build()
            .unwrap_or_default()
    })
}

/// Probe one link, returning it when it resolves.
///
/// HEAD is tried first because it transfers no body, but servers that reject
/// HEAD with 405/501 (a valid HTTP response, not a broken link) are retried
/// with a one-byte ranged GET so the link is not dropped from the result.
async fn probe_link(client: &Client, link: &str) -> Option<String> {
    match client.head(link).send().await {
        Ok(resp) if resp.status().is_success() => Some(link.to_string()),
        Ok(resp) if matches!(resp.status().as_u16(), 405 | 501) => {
            match client.get(link).header(RANGE, "bytes=0-0").send().await {
                Ok(get_resp)
                    if get_resp.status().is_success() || get_resp.status().as_u16() == 206 =>
                {
                    Some(link.to_string())
                }
                _ => None,
            }
        }
        _ => None,
    }
}

/// Validate a list of links using HTTP HEAD requests (GET fallback for
/// servers that reject HEAD).
pub async fn validate_links(links: &[String]) -> Vec<String> {
    if links.is_empty() {
        return Vec::new();
    }

    let client = get_client();
    let mut futures = Vec::new();

    for link in links {
        if !is_url(link) {
            continue;
        }

        let client = client.clone();
        let link = link.clone();
        futures.push(tokio::spawn(
            async move { probe_link(&client, &link).await },
        ));
    }

    let results = join_all(futures).await;
    results
        .into_iter()
        .filter_map(|r| r.ok().flatten())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::io::{AsyncReadExt, AsyncWriteExt};
    use tokio::net::TcpListener;

    /// Serve `responses` in order; each request is answered then the
    /// connection is closed (reqwest opens a new one for the next request).
    async fn serve(responses: Vec<&'static str>) -> (String, tokio::task::JoinHandle<()>) {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        let handle = tokio::spawn(async move {
            for body in responses {
                let Ok((mut socket, _)) = listener.accept().await else {
                    return;
                };
                let mut buf = [0u8; 2048];
                let _ = socket.read(&mut buf).await;
                let _ = socket.write_all(body.as_bytes()).await;
                let _ = socket.shutdown().await;
            }
        });
        (format!("http://{}/page", addr), handle)
    }

    #[tokio::test]
    async fn test_successful_head_keeps_link() {
        let (link, server) = serve(vec![
            "HTTP/1.1 200 OK\r\ncontent-length: 0\r\nconnection: close\r\n\r\n",
        ])
        .await;

        let validated = validate_links(std::slice::from_ref(&link)).await;
        server.await.unwrap();

        assert_eq!(validated, vec![link]);
    }

    #[tokio::test]
    async fn test_head_405_falls_back_to_ranged_get() {
        let (link, server) = serve(vec![
            "HTTP/1.1 405 Method Not Allowed\r\ncontent-length: 0\r\nconnection: close\r\n\r\n",
            "HTTP/1.1 206 Partial Content\r\ncontent-length: 1\r\nconnection: close\r\n\r\nx",
        ])
        .await;

        let validated = validate_links(std::slice::from_ref(&link)).await;
        server.await.unwrap();

        assert_eq!(validated, vec![link]);
    }

    #[tokio::test]
    async fn test_head_501_falls_back_to_ranged_get() {
        let (link, server) = serve(vec![
            "HTTP/1.1 501 Not Implemented\r\ncontent-length: 0\r\nconnection: close\r\n\r\n",
            "HTTP/1.1 200 OK\r\ncontent-length: 1\r\nconnection: close\r\n\r\nx",
        ])
        .await;

        let validated = validate_links(std::slice::from_ref(&link)).await;
        server.await.unwrap();

        assert_eq!(validated, vec![link]);
    }

    #[tokio::test]
    async fn test_not_found_link_is_dropped() {
        let (link, server) = serve(vec![
            "HTTP/1.1 404 Not Found\r\ncontent-length: 0\r\nconnection: close\r\n\r\n",
        ])
        .await;

        let validated = validate_links(std::slice::from_ref(&link)).await;
        server.await.unwrap();

        assert!(validated.is_empty());
    }

    #[tokio::test]
    async fn test_head_405_and_get_error_is_dropped() {
        let (link, server) = serve(vec![
            "HTTP/1.1 405 Method Not Allowed\r\ncontent-length: 0\r\nconnection: close\r\n\r\n",
            "HTTP/1.1 500 Internal Server Error\r\ncontent-length: 0\r\nconnection: close\r\n\r\n",
        ])
        .await;

        let validated = validate_links(std::slice::from_ref(&link)).await;
        server.await.unwrap();

        assert!(validated.is_empty());
    }

    #[tokio::test]
    async fn test_empty_input_returns_empty() {
        assert!(validate_links(&[]).await.is_empty());
    }
}
