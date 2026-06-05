#[derive(Debug, Clone)]
pub struct QualityScore {
    pub score: f32,
    pub too_short: bool,
    pub missing_links: bool,
    pub duplicate_heavy: bool,
    pub noisy: bool,
    pub acceptable: bool,
}

use regex::Regex;
use std::collections::HashSet;
use std::sync::OnceLock;

static NOISY_REGEX: OnceLock<Regex> = OnceLock::new();

pub fn score_content(markdown: &str, links: &[String], threshold: f32) -> QualityScore {
    let trimmed = markdown.trim();
    let len = trimmed.len();

    let too_short = len < 500;
    let missing_links = links.is_empty();

    let mut num_lines = 0;
    let mut unique_lines = HashSet::new();
    for line in trimmed.lines() {
        num_lines += 1;
        unique_lines.insert(line.trim());
    }
    let unique_count = unique_lines.len();
    let duplicate_heavy = num_lines > 0 && unique_count < std::cmp::max(5, num_lines / 3);

    let noisy_re = NOISY_REGEX
        .get_or_init(|| Regex::new("(?i)cookie|subscribe|javascript|log in|sign up").unwrap());
    let noisy_count = noisy_re.find_iter(trimmed).count();
    let noisy = noisy_count > 6;

    let has_frontmatter = trimmed.starts_with("---")
        && trimmed.contains("relevance_score:")
        && trimmed.contains("intent_category:")
        && trimmed.contains("token_estimate:")
        && trimmed.contains("last_updated:");
    let has_structural_anchors = trimmed.contains("[ANCHOR: SUMMARY]")
        && trimmed.contains("[ANCHOR: TECHNICAL_DETAILS]")
        && trimmed.contains("[ANCHOR: COMPARISON]")
        && trimmed.contains("[ANCHOR: CITATIONS]");

    let mut score = 1.0_f32;
    if too_short {
        score -= 0.25;
    }
    if missing_links {
        score -= 0.10;
    }
    if duplicate_heavy {
        score -= 0.15;
    }
    if noisy {
        score -= 0.10;
    }

    if has_frontmatter {
        score += 0.05;
    }
    if has_structural_anchors {
        score += 0.05;
    }

    let score = score.clamp(0.0, 1.0);
    let acceptable = score >= threshold && !too_short;

    QualityScore {
        score,
        too_short,
        missing_links,
        duplicate_heavy,
        noisy,
        acceptable,
    }
}
