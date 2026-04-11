//! SSRF protection utilities.

use reqwest::redirect::Policy;
use std::time::Duration;
use url::Url;

/// Check if a URL is safe from SSRF attempts.
pub fn is_safe_url(url_str: &str) -> bool {
    let parsed = match Url::parse(url_str) {
        Ok(u) => u,
        Err(_) => return false,
    };

    let scheme = parsed.scheme().to_lowercase();
    if scheme != "http" && scheme != "https" {
        return false;
    }

    let host = match parsed.host() {
        Some(h) => h,
        None => return false,
    };

    match host {
        url::Host::Domain(domain) => {
            let lowered = domain.to_lowercase();
            if lowered == "localhost"
                || lowered == "localhost.localdomain"
                || lowered.ends_with(".local")
                || lowered.ends_with(".internal")
            {
                return false;
            }
            true
        }
        url::Host::Ipv4(ip) => !is_private_ipv4(ip),
        url::Host::Ipv6(ip) => !is_private_ipv6(ip),
    }
}

fn is_private_ipv4(ip: std::net::Ipv4Addr) -> bool {
    ip.is_loopback()
        || ip.is_private()
        || ip.is_link_local()
        || ip.is_documentation()
        || ip.is_broadcast()
        || ip.is_unspecified()
}

fn is_private_ipv6(ip: std::net::Ipv6Addr) -> bool {
    ip.is_loopback()
        || ip.is_unspecified()
        || (ip.segments()[0] & 0xfe00) == 0xfc00
        || (ip.segments()[0] & 0xffc0) == 0xfe80
}

/// Create a reqwest ClientBuilder with SSRF protection via redirect policy.
pub fn create_safe_client_builder(timeout: Duration) -> reqwest::ClientBuilder {
    reqwest::Client::builder()
        .timeout(timeout)
        .redirect(Policy::custom(|attempt| {
            let url = attempt.url().as_str();
            if is_safe_url(url) {
                attempt.follow()
            } else {
                attempt.stop()
            }
        }))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_safe_url() {
        assert!(is_safe_url("https://example.com"));
        assert!(is_safe_url("http://example.com/path"));
        assert!(!is_safe_url("http://localhost"));
        assert!(!is_safe_url("http://127.0.0.1"));
        assert!(!is_safe_url("http://[::1]"));
        assert!(!is_safe_url("http://192.168.0.1"));
        assert!(!is_safe_url("file:///etc/passwd"));
    }
}
