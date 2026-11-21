//! Pure alternative-source discovery core.
//!
//! Mirrors `scripts/discovery.py`; shared fixtures in
//! `tests/fixtures/discovery_cases.json` define the contract. Live HTTP
//! extraction remains Python-led (see `agents-docs/DISCOVERY.md`).

use chrono::Utc;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::sync::LazyLock;
use url::Url;

use crate::discovery_strategies::{
    official_repository, publisher_metadata, search_provider, versioned_docs,
};

pub const DISCOVERY_SCHEMA_VERSION: u32 = 2;

type StrategyFn = fn(&DiscoveryInput) -> Vec<DiscoveryCandidate>;

pub(crate) static VERSION_RE: LazyLock<Regex> =
    LazyLock::new(|| Regex::new(r"(?i)^(?:v)?\d+(?:\.\d+)+(?:\.\d+)?$").expect("version regex"));

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub url: String,
    #[serde(default)]
    pub title: Option<String>,
    #[serde(default)]
    pub snippet: Option<String>,
    #[serde(default)]
    pub provider: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DiscoveryInput {
    pub primary_url: String,
    #[serde(default)]
    pub final_url: Option<String>,
    #[serde(default)]
    pub html: String,
    #[serde(default)]
    pub llms_txt: Option<String>,
    #[serde(default)]
    pub search_results: Vec<SearchResult>,
    #[serde(default)]
    pub query: Option<String>,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ValidationRecord {
    pub is_valid: bool,
    #[serde(default)]
    pub final_url: Option<String>,
    #[serde(default)]
    pub redirect_chain: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiscoveryCandidate {
    pub url: String,
    pub canonical_url: String,
    pub strategy: String,
    pub family: String,
    pub discovery_provider: String,
    pub original_url: String,
    pub publisher_domain: String,
    pub relationship: String,
    pub reason: String,
    pub timestamp: String,
    pub verification_state: String,
    pub redirect_chain: Vec<String>,
    pub title: Option<String>,
    pub content_hash: Option<String>,
    pub scores: HashMap<String, f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StrategyReport {
    pub name: String,
    pub family: String,
    pub candidate_count: usize,
    pub observable: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiscoveryReport {
    pub schema_version: u32,
    pub primary_url: String,
    pub selected: Option<DiscoveryCandidate>,
    pub candidates: Vec<DiscoveryCandidate>,
    pub rejected: Vec<DiscoveryCandidate>,
    pub strategies: Vec<StrategyReport>,
    pub duplicate_count: usize,
}

fn domain(url: &str) -> String {
    Url::parse(url)
        .ok()
        .and_then(|parsed| parsed.host_str().map(str::to_ascii_lowercase))
        .unwrap_or_default()
}

fn same_publisher(left: &str, right: &str) -> bool {
    let a = domain(left);
    let b = domain(right);
    !a.is_empty()
        && !b.is_empty()
        && (a == b || a.ends_with(&format!(".{b}")) || b.ends_with(&format!(".{a}")))
}

pub(crate) fn canonicalize(url: &str) -> String {
    let Ok(mut parsed) = Url::parse(url) else {
        return url.to_string();
    };
    parsed.set_fragment(None);
    let path = parsed.path().to_string();
    if path != "/" && path.ends_with('/') {
        parsed.set_path(path.trim_end_matches('/'));
    }
    parsed.to_string()
}

fn relationship(url: &str, primary: &str, final_url: Option<&str>) -> String {
    if canonicalize(url) == canonicalize(primary) {
        return "canonical".into();
    }
    if final_url.is_some_and(|value| canonicalize(url) == canonicalize(value)) {
        return "canonical".into();
    }
    if same_publisher(url, primary) || final_url.is_some_and(|value| same_publisher(url, value)) {
        return "same-publisher".into();
    }
    let host = domain(url);
    if host == "github.com"
        || host == "gitlab.com"
        || host == "crates.io"
        || host == "pypi.org"
        || host == "npmjs.com"
    {
        return "official-repository".into();
    }
    "unofficial".into()
}

fn registry_rank(url: &str) -> u8 {
    let host = domain(url);
    if host == "github.com" || host == "gitlab.com" || host.ends_with(".github.com") {
        2
    } else if matches!(host.as_str(), "crates.io" | "pypi.org" | "npmjs.com") {
        1
    } else {
        0
    }
}

fn tier(relationship: &str) -> u8 {
    match relationship {
        "canonical" => 4,
        "same-publisher" => 3,
        "official-repository" => 2,
        _ => 1,
    }
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn make_candidate(
    inp: &DiscoveryInput,
    raw: &str,
    strategy: &str,
    family: &str,
    provider: &str,
    reason: &str,
    title: Option<String>,
    content_hash: Option<String>,
) -> Option<DiscoveryCandidate> {
    let base = Url::parse(&inp.primary_url).ok()?;
    let absolute = base.join(raw).ok()?;
    if !matches!(absolute.scheme(), "http" | "https") {
        return None;
    }
    let url = absolute.to_string();
    let canonical_url = canonicalize(&url);
    Some(DiscoveryCandidate {
        publisher_domain: domain(&url),
        relationship: relationship(&url, &inp.primary_url, inp.final_url.as_deref()),
        original_url: inp.primary_url.clone(),
        strategy: strategy.into(),
        family: family.into(),
        discovery_provider: provider.into(),
        reason: reason.into(),
        timestamp: Utc::now().to_rfc3339(),
        verification_state: "unverified".into(),
        redirect_chain: Vec::new(),
        title,
        content_hash,
        scores: HashMap::new(),
        url,
        canonical_url,
    })
}

fn query_terms(query: Option<&str>) -> HashSet<String> {
    let Some(query) = query else {
        return HashSet::new();
    };
    query
        .to_ascii_lowercase()
        .split(|ch: char| !ch.is_ascii_alphanumeric())
        .filter(|token| token.len() >= 3)
        .filter(|token| {
            !matches!(
                *token,
                "the"
                    | "and"
                    | "for"
                    | "with"
                    | "from"
                    | "docs"
                    | "documentation"
                    | "guide"
                    | "reference"
                    | "api"
            )
        })
        .map(str::to_string)
        .collect()
}

fn score_candidate(candidate: &mut DiscoveryCandidate, terms: &HashSet<String>) {
    let haystack = format!(
        "{} {}",
        candidate.url,
        candidate.title.clone().unwrap_or_default()
    )
    .to_ascii_lowercase();
    let relevance = if terms.is_empty() {
        0.5
    } else {
        terms.iter().filter(|term| haystack.contains(*term)).count() as f64 / terms.len() as f64
    };
    let authority = match candidate.relationship.as_str() {
        "canonical" => 1.0,
        "same-publisher" => 0.85,
        "official-repository" => 0.75,
        _ => 0.25,
    };
    let structural = match candidate.discovery_provider.as_str() {
        "llms.txt" => 1.0,
        "redirect" => 0.9,
        "page-html" => 0.75,
        "url-path" => 0.65,
        "search" => 0.45,
        _ => 0.5,
    };
    let mut freshness = *candidate.scores.get("freshness").unwrap_or(&0.7);
    if !candidate.scores.contains_key("freshness") {
        if let Ok(parsed) = Url::parse(&candidate.url) {
            if parsed
                .path_segments()
                .map(|segments| segments.filter(|part| VERSION_RE.is_match(part)).count() > 0)
                .unwrap_or(false)
            {
                freshness = 0.3;
            }
        }
    }
    let extraction = *candidate.scores.get("extraction_quality").unwrap_or(&0.5);
    let overall = 0.35 * authority
        + 0.25 * relevance
        + 0.15 * freshness
        + 0.15 * structural
        + 0.10 * extraction;
    candidate.scores.insert("relevance".into(), relevance);
    candidate.scores.insert("freshness".into(), freshness);
    candidate
        .scores
        .insert("structural_completeness".into(), structural);
    candidate.scores.insert("authority".into(), authority);
    candidate
        .scores
        .insert("extraction_quality".into(), extraction);
    candidate.scores.insert("overall".into(), overall);
}

fn verify(
    candidate: &mut DiscoveryCandidate,
    validations: Option<&HashMap<String, ValidationRecord>>,
) {
    let Some(validations) = validations else {
        return;
    };
    let Some(result) = validations.get(&candidate.url) else {
        candidate.verification_state = "rejected".into();
        candidate.reason = format!("{}; URL validation failed", candidate.reason);
        return;
    };
    if !result.is_valid {
        candidate.verification_state = "rejected".into();
        candidate.reason = format!("{}; URL validation failed", candidate.reason);
        return;
    }
    candidate.verification_state = "verified".into();
    if let Some(final_url) = &result.final_url {
        candidate.canonical_url = canonicalize(final_url);
        candidate.publisher_domain = domain(final_url);
        let derived = relationship(final_url, &candidate.original_url, None);
        if tier(&derived) > tier(&candidate.relationship) {
            candidate.relationship = derived;
        }
    }
    candidate.redirect_chain = result.redirect_chain.clone();
}

pub fn discover_alternatives(
    inp: &DiscoveryInput,
    validations: Option<&HashMap<String, ValidationRecord>>,
    max_candidates: usize,
) -> DiscoveryReport {
    let strategies: Vec<(&str, StrategyFn)> = vec![
        ("publisher_metadata", publisher_metadata),
        ("official_repository", official_repository),
        ("versioned_docs", versioned_docs),
        ("search_provider", search_provider),
    ];
    let mut generated = Vec::new();
    let mut strategy_reports = Vec::new();
    for (name, strategy) in &strategies {
        let produced = strategy(inp);
        strategy_reports.push(StrategyReport {
            name: (*name).into(),
            family: (*name).into(),
            candidate_count: produced.len(),
            observable: true,
        });
        generated.extend(produced);
    }

    let mut deduplicated: HashMap<String, DiscoveryCandidate> = HashMap::new();
    let mut duplicate_count = 0;
    for candidate in generated {
        if let Some(existing) = deduplicated.get_mut(&candidate.canonical_url) {
            duplicate_count += 1;
            if tier(&candidate.relationship) > tier(&existing.relationship) {
                *existing = candidate;
            }
        } else {
            deduplicated.insert(candidate.canonical_url.clone(), candidate);
        }
    }

    let terms = query_terms(inp.query.as_deref());
    let mut accepted = Vec::new();
    let mut rejected = Vec::new();
    let mut seen_content = HashSet::new();
    for mut candidate in deduplicated.into_values() {
        if let Some(hash) = &candidate.content_hash {
            if !seen_content.insert(hash.clone()) {
                duplicate_count += 1;
                continue;
            }
        }
        verify(&mut candidate, validations);
        score_candidate(&mut candidate, &terms);
        if candidate.verification_state == "rejected" {
            rejected.push(candidate);
        } else {
            accepted.push(candidate);
        }
    }
    accepted.sort_by(|a, b| {
        tier(&b.relationship)
            .cmp(&tier(&a.relationship))
            .then((b.verification_state == "verified").cmp(&(a.verification_state == "verified")))
            .then(
                b.scores
                    .get("overall")
                    .unwrap_or(&0.0)
                    .partial_cmp(a.scores.get("overall").unwrap_or(&0.0))
                    .unwrap_or(std::cmp::Ordering::Equal),
            )
            .then(registry_rank(&b.url).cmp(&registry_rank(&a.url)))
    });
    accepted.truncate(max_candidates);
    let selected = accepted
        .iter()
        .find(|candidate| {
            candidate.verification_state == "verified" && candidate.relationship != "unofficial"
        })
        .cloned();
    DiscoveryReport {
        schema_version: DISCOVERY_SCHEMA_VERSION,
        primary_url: inp.primary_url.clone(),
        selected,
        candidates: accepted,
        rejected,
        strategies: strategy_reports,
        duplicate_count,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const FIXTURE: &str = include_str!("../../tests/fixtures/discovery_cases.json");

    #[test]
    fn shared_fixture_matches_rust_selection() {
        let fixture: Value = serde_json::from_str(FIXTURE).expect("fixture");
        for case in fixture["cases"].as_array().expect("cases") {
            let input = DiscoveryInput {
                primary_url: case["primary_url"].as_str().unwrap().to_string(),
                final_url: case["final_url"].as_str().map(str::to_string),
                html: case["html"].as_str().unwrap().to_string(),
                llms_txt: case["llms_txt"].as_str().map(str::to_string),
                search_results: serde_json::from_value(case["search_results"].clone()).unwrap(),
                query: case["query"].as_str().map(str::to_string),
            };
            let validations: HashMap<String, ValidationRecord> =
                serde_json::from_value(case["validator"].clone()).unwrap();
            let report = discover_alternatives(&input, Some(&validations), 8);
            let selected = report.selected.expect("selected");
            assert_eq!(
                selected.canonical_url,
                case["expected_selected"].as_str().unwrap(),
                "{}",
                case["name"].as_str().unwrap()
            );
            assert_eq!(
                selected.relationship,
                case["expected_relationship"].as_str().unwrap(),
                "{}",
                case["name"].as_str().unwrap()
            );
            assert_eq!(
                report.strategies.len(),
                4,
                "all strategy families are observable"
            );
        }
    }

    #[test]
    fn unofficial_mirror_never_outranks_canonical() {
        let fixture: Value = serde_json::from_str(FIXTURE).expect("fixture");
        let case = fixture["cases"]
            .as_array()
            .unwrap()
            .iter()
            .find(|case| case["name"] == "unofficial-mirror")
            .unwrap();
        let input = DiscoveryInput {
            primary_url: case["primary_url"].as_str().unwrap().to_string(),
            final_url: None,
            html: case["html"].as_str().unwrap().to_string(),
            llms_txt: None,
            search_results: serde_json::from_value(case["search_results"].clone()).unwrap(),
            query: case["query"].as_str().map(str::to_string),
        };
        let validations: HashMap<String, ValidationRecord> =
            serde_json::from_value(case["validator"].clone()).unwrap();
        let report = discover_alternatives(&input, Some(&validations), 8);
        let canonical = report
            .candidates
            .iter()
            .position(|candidate| candidate.relationship == "canonical")
            .unwrap();
        let unofficial = report
            .candidates
            .iter()
            .position(|candidate| candidate.relationship == "unofficial")
            .unwrap();
        assert!(canonical < unofficial);
    }
}
