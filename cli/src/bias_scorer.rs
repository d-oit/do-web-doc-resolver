//! Source bias and quality scoring.

use regex::Regex;
use std::sync::OnceLock;
use url::Url;

static SPAM_PATTERNS: OnceLock<[Regex; 5]> = OnceLock::new();

fn get_spam_patterns() -> &'static [Regex; 5] {
    SPAM_PATTERNS.get_or_init(|| {
        [
            Regex::new("(?i)buy now").expect("Invalid regex for buy now"),
            Regex::new("(?i)cheap").expect("Invalid regex for cheap"),
            Regex::new("(?i)discount").expect("Invalid regex for discount"),
            Regex::new("(?i)free trial").expect("Invalid regex for free trial"),
            Regex::new("(?i)best price").expect("Invalid regex for best price"),
        ]
    })
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
        if news_sites.iter().any(|&site| domain.contains(site)) {
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
        if dev_sites.iter().any(|&site| domain.contains(site)) {
            score += 0.2;
        }
    }

    // Content quality heuristics - graduated scoring
    let word_count = content.split_whitespace().count();
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

    // SEO spam detection
    let spam_patterns = get_spam_patterns();
    for re in spam_patterns {
        if re.is_match(content) {
            score -= 0.1;
        }
    }

    score.clamp(0.0, 1.0)
}
