use regex::Regex;
use std::sync::OnceLock;

static NOISY_PATTERNS: OnceLock<Regex> = OnceLock::new();
static JARGON_PATTERNS: OnceLock<Regex> = OnceLock::new();

// Quality scoring thresholds
const THRESHOLD_NOISE: usize = 6;
const THRESHOLD_JARGON: usize = 3;
const THRESHOLD_MIN_CHARS: usize = 500;

// Quality scoring penalties
const PENALTY_TOO_SHORT: f32 = 0.25;
const PENALTY_MISSING_LINKS: f32 = 0.10;
const PENALTY_DUPLICATE_HEAVY: f32 = 0.15;
const PENALTY_NOISY: f32 = 0.10;
const PENALTY_JARGON: f32 = 0.10;

// Quality scoring bonuses
const BONUS_HAS_FRONTMATTER: f32 = 0.05;
const BONUS_HAS_STRUCTURAL_ANCHORS: f32 = 0.05;

#[derive(Debug, Clone)]
pub struct QualityScore {
    pub score: f32,
    pub too_short: bool,
    pub missing_links: bool,
    pub duplicate_heavy: bool,
    pub noisy: bool,
    pub acceptable: bool,
}

pub fn score_content(markdown: &str, links: &[String], threshold: f32) -> QualityScore {
    let trimmed = markdown.trim();
    let len = trimmed.len();

    let too_short = len < THRESHOLD_MIN_CHARS;
    let missing_links = links.is_empty();

    // Optimize duplicate detection: pre-calculate total lines via byte scan and early exit
    let duplicate_heavy = if trimmed.is_empty() {
        false
    } else {
        let total_lines = trimmed.bytes().filter(|&b| b == b'\n').count() + 1;
        let threshold_unique = std::cmp::max(5, total_lines / 3);
        let mut unique_set = std::collections::HashSet::with_capacity(std::cmp::min(
            total_lines,
            threshold_unique + 1,
        ));
        let mut is_dup = true;
        for line in trimmed.lines() {
            unique_set.insert(line);
            if unique_set.len() >= threshold_unique {
                is_dup = false;
                break;
            }
        }
        is_dup
    };

    // Optimize noise detection: use case-insensitive regex to avoid to_lowercase() allocation
    let noisy_re = NOISY_PATTERNS.get_or_init(|| {
        Regex::new("(?i)cookie|subscribe|javascript|log in|sign up")
            .expect("Invalid quality noise regex patterns")
    });
    // Early exit if noise threshold is exceeded
    let noisy_count = noisy_re
        .find_iter(trimmed)
        .take(THRESHOLD_NOISE + 1)
        .count();
    let noisy = noisy_count > THRESHOLD_NOISE;

    let jargon_re = JARGON_PATTERNS.get_or_init(|| {
        Regex::new("(?i)seamlessly|robust|powerful|comprehensive|streamlined|leverage|revolutionize|game-changing|intuitive|next-generation|cutting-edge|state-of-the-art|best-in-class|unlock|transform|supercharge")
            .expect("Invalid quality jargon regex patterns")
    });
    // Early exit if jargon threshold is exceeded
    let jargon_count = jargon_re
        .find_iter(trimmed)
        .take(THRESHOLD_JARGON + 1)
        .count();
    let jargon_heavy = jargon_count > THRESHOLD_JARGON;

    let has_frontmatter = if let Some(rest) = trimmed.strip_prefix("---") {
        let header_end = rest
            .find("\n---")
            .map(|i| i + 7)
            .unwrap_or(trimmed.len());
        let header_slice = &trimmed[..header_end];
        header_slice.contains("relevance_score:")
            && header_slice.contains("intent_category:")
            && header_slice.contains("token_estimate:")
            && header_slice.contains("last_updated:")
    } else {
        false
    };

    let has_structural_anchors = trimmed.contains("[ANCHOR:")
        && trimmed.contains("[ANCHOR: SUMMARY]")
        && trimmed.contains("[ANCHOR: TECHNICAL_DETAILS]")
        && trimmed.contains("[ANCHOR: COMPARISON]")
        && trimmed.contains("[ANCHOR: CITATIONS]");

    let mut score = 1.0_f32;
    if too_short {
        score -= PENALTY_TOO_SHORT;
    }
    if missing_links {
        score -= PENALTY_MISSING_LINKS;
    }
    if duplicate_heavy {
        score -= PENALTY_DUPLICATE_HEAVY;
    }
    if noisy {
        score -= PENALTY_NOISY;
    }
    if jargon_heavy {
        score -= PENALTY_JARGON;
    }

    if has_frontmatter {
        score += BONUS_HAS_FRONTMATTER;
    }
    if has_structural_anchors {
        score += BONUS_HAS_STRUCTURAL_ANCHORS;
    }

    let score = score.clamp(0.0, 1.0);
    let acceptable = score >= threshold && !too_short;

    QualityScore {
        score,
        too_short,
        missing_links,
        duplicate_heavy,
        noisy: noisy || jargon_heavy,
        acceptable,
    }
}
