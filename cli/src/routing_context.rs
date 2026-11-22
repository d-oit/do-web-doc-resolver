//! Context-aware routing keys for search queries.
//!
//! Mirrors `scripts/routing_context.py`; shared fixtures in
//! `tests/fixtures/routing_context_cases.json` keep the runtimes aligned.

use serde::{Deserialize, Serialize};
use url::Url;

pub const CONTEXT_SCHEMA_VERSION: u32 = 2;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct QueryContext {
    pub intent: String,
    pub topic: String,
    pub language: String,
    pub platform: String,
}

impl QueryContext {
    #[must_use]
    pub fn routing_key(&self) -> String {
        format!(
            "q:v{}:{}:{}:{}:{}",
            CONTEXT_SCHEMA_VERSION, self.intent, self.topic, self.language, self.platform
        )
    }
}

const INTENTS: &[(&str, &[&str])] = &[
    (
        "troubleshooting",
        &[
            "error",
            "exception",
            "traceback",
            "crash",
            "broken",
            "debug",
            "troubleshoot",
            "not working",
            "does not work",
            "fix",
            "issue",
        ],
    ),
    (
        "release",
        &[
            "release",
            "changelog",
            "change log",
            "version",
            "upgrade",
            "migration",
            "deprecated",
            "breaking",
            "whats new",
            "what's new",
        ],
    ),
    (
        "package",
        &[
            "install",
            "installation",
            "package",
            "crate",
            "dependency",
            "sdk",
            "download",
            "cargo add",
            "pip install",
            "npm install",
            "gem",
        ],
    ),
    (
        "api_reference",
        &[
            "api",
            "reference",
            "signature",
            "method",
            "function",
            "class",
            "endpoint",
            "struct",
            "trait",
            "parameter",
            "argument",
        ],
    ),
    (
        "comparison",
        &[
            "vs",
            "versus",
            "compare",
            "comparison",
            "difference",
            "alternative",
            "alternatives",
        ],
    ),
    (
        "documentation",
        &[
            "docs",
            "documentation",
            "guide",
            "tutorial",
            "how to",
            "example",
            "usage",
            "learn",
            "quickstart",
            "manual",
        ],
    ),
];

const PLATFORM_HINTS: &[(&str, &str)] = &[
    ("stack overflow", "stackoverflow"),
    ("stackoverflow", "stackoverflow"),
    ("github", "github"),
    ("gitlab", "gitlab"),
    ("docs.rs", "docsrs"),
    ("docsrs", "docsrs"),
    ("read the docs", "readthedocs"),
    ("readthedocs", "readthedocs"),
    ("pypi", "pypi"),
    ("pip ", "pypi"),
    ("crates.io", "cratesio"),
    ("cratesio", "cratesio"),
    ("npmjs", "npm"),
    ("npm ", "npm"),
];

fn topic_for_token(token: &str) -> Option<&'static str> {
    Some(match token {
        "rust" | "cargo" | "crates" | "crates.io" | "docs.rs" | "tokio" | "serde" | "axum" => {
            "rust"
        }
        "python" | "pip" | "pypi" => "python",
        "django" => "django",
        "flask" => "flask",
        "fastapi" => "fastapi",
        "pandas" => "pandas",
        "numpy" => "numpy",
        "node" | "nodejs" | "npm" | "express" => "nodejs",
        "typescript" => "typescript",
        "javascript" | "js" => "javascript",
        "deno" => "deno",
        "bun" => "bun",
        "react" | "reactjs" => "react",
        "next.js" | "nextjs" => "nextjs",
        "vue" => "vue",
        "angular" => "angular",
        "svelte" => "svelte",
        "go" | "golang" => "go",
        "java" => "java",
        "spring" => "spring",
        "kotlin" => "kotlin",
        "dotnet" | "csharp" | "c#" => "dotnet",
        "php" => "php",
        "ruby" => "ruby",
        "rails" => "rails",
        "swift" => "swift",
        "android" => "android",
        "ios" => "ios",
        "kubernetes" | "k8s" => "kubernetes",
        "docker" => "docker",
        "terraform" => "terraform",
        "postgres" | "postgresql" => "postgresql",
        "mysql" => "mysql",
        "sqlite" => "sqlite",
        "redis" => "redis",
        "mongodb" => "mongodb",
        "aws" | "amazon" => "aws",
        "azure" => "azure",
        "gcp" => "gcp",
        "linux" => "linux",
        "git" => "git",
        "github" => "github",
        "graphql" => "graphql",
        "grpc" => "grpc",
        "openai" | "anthropic" | "langchain" | "llm" => "llm",
        _ => return None,
    })
}

fn language_for_topic(topic: &str) -> &'static str {
    match topic {
        "rust" => "rust",
        "python" | "django" | "flask" | "fastapi" | "pandas" | "numpy" => "python",
        "nodejs" | "javascript" | "deno" | "bun" => "javascript",
        "typescript" | "react" | "nextjs" | "vue" | "angular" | "svelte" => "typescript",
        "go" => "go",
        "java" | "spring" => "java",
        "kotlin" | "android" => "kotlin",
        "dotnet" => "csharp",
        "php" => "php",
        "ruby" | "rails" => "ruby",
        "swift" | "ios" => "swift",
        _ => "na",
    }
}

#[must_use]
pub fn normalize_query_text(query: &str) -> String {
    let mut out = String::with_capacity(query.len());
    let mut last_space = true;
    for ch in query.to_lowercase().chars() {
        if ch.is_ascii_alphanumeric() || matches!(ch, '+' | '#' | '.') {
            out.push(ch);
            last_space = false;
        } else if !last_space {
            out.push(' ');
            last_space = true;
        }
    }
    out.trim().to_string()
}

#[must_use]
pub fn classify_intent(query: &str) -> String {
    let normalized = normalize_query_text(query);
    let padded = format!(" {normalized} ");
    for (intent, signals) in INTENTS {
        if signals
            .iter()
            .any(|signal| padded.contains(&format!(" {signal} ")))
        {
            return (*intent).to_string();
        }
    }
    "general".to_string()
}

#[must_use]
pub fn detect_topic(normalized: &str) -> String {
    normalized
        .split_whitespace()
        .find_map(topic_for_token)
        .unwrap_or("general")
        .to_string()
}

#[must_use]
pub fn detect_platform(normalized: &str) -> String {
    let padded = format!(" {normalized} ");
    for (hint, platform) in PLATFORM_HINTS {
        if padded.contains(hint) {
            return (*platform).to_string();
        }
    }
    "none".to_string()
}

#[must_use]
pub fn derive_context(query: &str) -> QueryContext {
    let normalized = normalize_query_text(query);
    let intent = classify_intent(&normalized);
    let topic = detect_topic(&normalized);
    QueryContext {
        language: language_for_topic(&topic).to_string(),
        platform: detect_platform(&normalized),
        intent,
        topic,
    }
}

#[must_use]
pub fn query_routing_key(query: &str) -> String {
    derive_context(query).routing_key()
}

#[must_use]
pub fn is_query_context_key(key: &str) -> bool {
    key.starts_with("q:v")
}

#[must_use]
pub fn routing_key_for(target: &str, is_url: bool) -> String {
    if !is_url {
        return query_routing_key(target);
    }
    Url::parse(target)
        .ok()
        .and_then(|parsed| parsed.host_str().map(str::to_ascii_lowercase))
        .unwrap_or_else(|| "any".to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::Value;

    const FIXTURE: &str = include_str!("../../tests/fixtures/routing_context_cases.json");

    #[test]
    fn shared_fixture_matches_rust() {
        let fixture: Value = serde_json::from_str(FIXTURE).expect("fixture json");
        assert_eq!(fixture["schema_version"], CONTEXT_SCHEMA_VERSION);
        for case in fixture["cases"].as_array().expect("cases") {
            let query = case["query"].as_str().expect("query");
            let context = derive_context(query);
            assert_eq!(context.intent, case["intent"].as_str().unwrap(), "{query}");
            assert_eq!(context.topic, case["topic"].as_str().unwrap(), "{query}");
            assert_eq!(
                context.language,
                case["language"].as_str().unwrap(),
                "{query}"
            );
            assert_eq!(
                context.platform,
                case["platform"].as_str().unwrap(),
                "{query}"
            );
            assert_eq!(
                context.routing_key(),
                case["routing_key"].as_str().unwrap(),
                "{query}"
            );
        }
    }

    #[test]
    fn query_key_is_bounded_and_versioned() {
        let key = query_routing_key("Python asyncio tutorial");
        assert!(key.starts_with("q:v2:"));
        assert_eq!(key, query_routing_key("python asyncio guide"));
        assert!(is_query_context_key(&key));
    }

    #[test]
    fn url_key_stays_a_domain() {
        assert_eq!(
            routing_key_for("https://docs.rs/tokio/latest/tokio/", true),
            "docs.rs"
        );
    }
}
