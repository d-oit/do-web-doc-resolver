//! Candidate-generation strategies for discovery.

use regex::Regex;
use std::sync::LazyLock;
use url::Url;

use crate::discovery::{
    DiscoveryCandidate, DiscoveryInput, VERSION_RE, canonicalize, make_candidate,
};

static CANONICAL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r#"(?i)<link[^>]+rel\s*=\s*["'][^"']*canonical[^"']*["'][^>]+href\s*=\s*["']([^"']+)["']"#,
    )
    .expect("canonical regex")
});
static ALTERNATE_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(
        r#"(?i)<link[^>]+rel\s*=\s*["'][^"']*alternate[^"']*["'][^>]+href\s*=\s*["']([^"']+)["']"#,
    )
    .expect("alternate regex")
});
static OG_URL_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?i)<meta[^>]+property\s*=\s*["']og:url["'][^>]+content\s*=\s*["']([^"']+)["']"#)
        .expect("og url regex")
});
static LINK_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r#"(?i)href\s*=\s*["']([^"']+)["']"#).expect("link regex"));
static MARKDOWN_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"\[[^\]]*\]\((https?://[^)\s]+)").expect("markdown link regex"));
static REGISTRY_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r#"(?i)https?://(?:www\.)?(?:github\.com|gitlab\.com|crates\.io|pypi\.org|npmjs\.com)/[^\s"'<>]+"#)
        .expect("registry regex")
});
pub(crate) fn publisher_metadata(inp: &DiscoveryInput) -> Vec<DiscoveryCandidate> {
    let mut candidates = Vec::new();
    for (regex, reason) in [
        (&*CANONICAL_RE, "canonical link"),
        (&*ALTERNATE_RE, "alternate link"),
        (&*OG_URL_RE, "og:url"),
    ] {
        for capture in regex.captures_iter(&inp.html) {
            if let Some(candidate) = make_candidate(
                inp,
                &capture[1],
                "publisher_metadata",
                "publisher_metadata",
                "page-html",
                reason,
                None,
                None,
            ) {
                candidates.push(candidate);
            }
        }
    }
    for capture in LINK_RE.captures_iter(&inp.html) {
        let link = capture[1].to_ascii_lowercase();
        if ["llms.txt", "sitemap.xml", "feed.xml", "atom.xml", "rss.xml"]
            .iter()
            .any(|suffix| link.ends_with(suffix))
        {
            if let Some(candidate) = make_candidate(
                inp,
                &capture[1],
                "publisher_metadata",
                "publisher_metadata",
                "page-html",
                "publisher metadata link",
                None,
                None,
            ) {
                candidates.push(candidate);
            }
        }
    }
    if let Some(llms) = &inp.llms_txt {
        for capture in MARKDOWN_RE.captures_iter(llms) {
            if let Some(candidate) = make_candidate(
                inp,
                &capture[1],
                "publisher_metadata",
                "publisher_metadata",
                "llms.txt",
                "llms.txt link",
                None,
                None,
            ) {
                candidates.push(candidate);
            }
        }
    }
    candidates
}

pub(crate) fn official_repository(inp: &DiscoveryInput) -> Vec<DiscoveryCandidate> {
    let text = format!("{}\n{}", inp.html, inp.llms_txt.clone().unwrap_or_default());
    REGISTRY_RE
        .find_iter(&text)
        .filter_map(|matched| {
            let url = matched.as_str().trim_end_matches(['.', ',', ')', ';']);
            make_candidate(
                inp,
                url,
                "official_repository",
                "official_repository",
                "page-html",
                "official repository or registry link",
                None,
                None,
            )
        })
        .map(|mut candidate| {
            candidate.relationship = "official-repository".into();
            candidate
        })
        .collect()
}

pub(crate) fn versioned_docs(inp: &DiscoveryInput) -> Vec<DiscoveryCandidate> {
    let source = inp.final_url.as_deref().unwrap_or(&inp.primary_url);
    let Ok(parsed) = Url::parse(source) else {
        return Vec::new();
    };
    let segments: Vec<&str> = parsed
        .path_segments()
        .map(|parts| parts.filter(|part| !part.is_empty()).collect())
        .unwrap_or_default();
    let mut candidates = Vec::new();
    for (index, segment) in segments.iter().enumerate() {
        let lowered = segment.to_ascii_lowercase();
        let is_version = VERSION_RE.is_match(segment)
            || matches!(lowered.as_str(), "latest" | "stable" | "current" | "next");
        if !is_version {
            continue;
        }
        for (replacement, freshness) in [("stable", 1.0), ("latest", 0.98), ("", 0.6)] {
            let mut replaced = segments.clone();
            if replacement.is_empty() {
                replaced.remove(index);
            } else {
                replaced[index] = replacement;
            }
            let path = format!("/{}", replaced.join("/"));
            let mut target = parsed.clone();
            target.set_path(&path);
            if let Some(mut candidate) = make_candidate(
                inp,
                target.as_str(),
                "versioned_docs",
                "versioned_docs",
                "url-path",
                &format!(
                    "versioned documentation variant ({})",
                    if replacement.is_empty() {
                        "unversioned"
                    } else {
                        replacement
                    }
                ),
                None,
                None,
            ) {
                candidate.scores.insert("freshness".into(), freshness);
                if matches!(replacement, "stable" | "latest") {
                    candidate.relationship = "canonical".into();
                }
                candidates.push(candidate);
            }
        }
    }
    if let Some(final_url) = &inp.final_url {
        if canonicalize(final_url) != canonicalize(&inp.primary_url) {
            if let Some(mut candidate) = make_candidate(
                inp,
                final_url,
                "versioned_docs",
                "versioned_docs",
                "redirect",
                "redirect final URL",
                None,
                None,
            ) {
                candidate.relationship = "canonical".into();
                candidate.scores.insert("freshness".into(), 0.9);
                candidates.push(candidate);
            }
        }
    }
    candidates
}

pub(crate) fn search_provider(inp: &DiscoveryInput) -> Vec<DiscoveryCandidate> {
    inp.search_results
        .iter()
        .filter_map(|result| {
            make_candidate(
                inp,
                &result.url,
                "search_provider",
                "search_provider",
                result.provider.as_deref().unwrap_or("search"),
                "normalized product/version/error query",
                result.title.clone(),
                None,
            )
        })
        .collect()
}
