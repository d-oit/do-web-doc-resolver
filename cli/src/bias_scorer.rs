//! Source bias and quality scoring.

use url::Url;

/// Check if a string contains another string case-insensitively (ASCII-only)
fn contains_ignore_ascii_case(haystack: &str, needle: &str) -> bool {
    if needle.is_empty() {
        return true;
    }
    let haystack_bytes = haystack.as_bytes();
    let needle_bytes = needle.as_bytes();
    if haystack_bytes.len() < needle_bytes.len() {
        return false;
    }
    haystack_bytes
        .windows(needle_bytes.len())
        .any(|window| window.eq_ignore_ascii_case(needle_bytes))
}

/// Check whether `host` is `site` itself or a subdomain of it.
///
/// Substring matching would award trust to hosts like `github.com.evil.example`,
/// so the boundary has to land on a dot.
fn is_domain_or_subdomain(host: &str, site: &str) -> bool {
    let host = host.to_ascii_lowercase();
    let site = site.to_ascii_lowercase();

    host == site || host.ends_with(&format!(".{site}"))
}

/// Score a result based on domain trust and content quality
pub fn score_result(url: &str, content: &str) -> f64 {
    let mut score: f64 = 0.5;

    // Domain trust heuristics
    if let Ok(parsed_url) = Url::parse(url) {
        let domain = parsed_url.host_str().unwrap_or("");

        let trusted_tlds = [".edu", ".gov", ".org", ".rs", ".io"];
        if trusted_tlds.iter().any(|tld| domain.ends_with(tld)) {
            score += 0.2;
        }

        let news_sites = ["nytimes.com", "bbc.co.uk", "reuters.com", "theguardian.com"];
        if news_sites
            .iter()
            .any(|&site| is_domain_or_subdomain(domain, site))
        {
            score += 0.1;
        }

        let dev_sites = [
            "github.com",
            "stackoverflow.com",
            "docs.rs",
            "mozilla.org",
            "rust-lang.org",
            "tokio.rs",
        ];
        if dev_sites
            .iter()
            .any(|&site| is_domain_or_subdomain(domain, site))
        {
            score += 0.2;
        }
    }

    // Content quality heuristics - graduated scoring
    let word_count = content.split_whitespace().take(501).count();
    if word_count > 500 {
        score += 0.2;
    } else if word_count > 300 {
        score += 0.15;
    } else if word_count > 150 {
        score += 0.1;
    } else if word_count < 50 {
        score -= 0.15;
    }

    // Content length bonus (characters)
    let char_count = content.len();
    if char_count > 2000 {
        score += 0.1;
    } else if char_count > 1000 {
        score += 0.05;
    }

    // SEO spam detection using zero-allocation case-insensitive ASCII substring search
    let spam_terms = ["buy now", "cheap", "discount", "free trial", "best price"];
    for term in spam_terms {
        if contains_ignore_ascii_case(content, term) {
            score -= 0.1;
        }
    }

    score.clamp(0.0, 1.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_subdomain_match() {
        assert!(is_domain_or_subdomain("github.com", "github.com"));
        assert!(is_domain_or_subdomain("gist.github.com", "github.com"));
        assert!(is_domain_or_subdomain("GITHUB.COM", "github.com"));
    }

    #[test]
    fn test_suffix_lookalike_rejected() {
        // A host that merely contains a trusted domain must not earn trust.
        assert!(!is_domain_or_subdomain(
            "github.com.evil.example",
            "github.com"
        ));
        assert!(!is_domain_or_subdomain(
            "notstackoverflow.com",
            "stackoverflow.com"
        ));
    }

    #[test]
    fn test_lookalike_host_scores_lower_than_real() {
        // 600 words of filler satisfies the word-count bonus for both hosts, so
        // any difference comes purely from the domain trust heuristic.
        let content = "word ".repeat(600);
        let real = score_result("https://github.com/foo/bar", &content);
        let spoofed = score_result("https://github.com.evil.example/foo", &content);

        assert!(
            real > spoofed,
            "real host ({real}) should outscore lookalike ({spoofed})"
        );
    }
}
