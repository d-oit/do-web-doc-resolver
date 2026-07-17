//! Content compaction and token optimization.

use std::collections::HashSet;
use std::sync::OnceLock;

use regex::RegexSet;

static BOILERPLATE_SET: OnceLock<RegexSet> = OnceLock::new();
static PROTECTED_SET: OnceLock<RegexSet> = OnceLock::new();

const INITIAL_LINE_CAPACITY: usize = 128;

/// Compact content by removing boilerplate and redundant information
pub fn compact_content(content: &str, max_chars: usize) -> String {
    let lines = content.lines();
    let mut unique_lines = HashSet::with_capacity(INITIAL_LINE_CAPACITY);
    let mut compacted = Vec::with_capacity(INITIAL_LINE_CAPACITY);

    for line in lines {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            compacted.push("");
            continue;
        }

        // Basic boilerplate detection (simple heuristics)
        if is_boilerplate(trimmed) {
            continue;
        }

        // Deduplication
        if unique_lines.insert(trimmed) {
            compacted.push(trimmed);
        }
    }

    let joined = compacted.join("\n");

    // Truncate to max_chars safely (avoiding UTF-8 slicing panics)
    if joined.len() <= max_chars {
        joined
    } else if let Some((idx, _)) = joined.char_indices().nth(max_chars) {
        let mut result = joined;
        result.truncate(idx);
        result
    } else {
        joined
    }
}

fn is_boilerplate(line: &str) -> bool {
    // If the line is short, it cannot match any of the boilerplate patterns (all >= 10 chars).
    if line.len() < 10 {
        if !line.is_empty() && line.chars().all(|c| !c.is_alphanumeric()) {
            let protected_set = PROTECTED_SET.get_or_init(|| {
                RegexSet::new([
                    r"```",
                    r"\$\$",
                    r"---",
                    r"###",
                    r"\|",
                    r">",
                    r"\{\\displaystyle",
                    r"\\textstyle",
                    r"\\begin\{aligned\}",
                    r"\\end\{aligned\}",
                    r"<pre",
                    r"<code",
                ])
                .expect("Invalid protected marker regex patterns")
            });
            // Only perform regex matching if a protected formatting character is present
            let has_protected_char = line.contains(['`', '$', '-', '#', '|', '>', '\\', '{', '<']);
            if has_protected_char && protected_set.is_match(line) {
                return false;
            }
            return true;
        }
        return false;
    }

    let boilerplate_set = BOILERPLATE_SET.get_or_init(|| {
        RegexSet::new([
            "(?i)cookie policy",
            "(?i)all rights reserved",
            "(?i)terms of service",
            "(?i)privacy policy",
            "(?i)subscribe to our newsletter",
            "(?i)follow us on",
            "(?i)click here",
        ])
        .expect("Invalid boilerplate regex patterns")
    });

    if boilerplate_set.is_match(line) {
        return true;
    }

    // Protect Markdown structural elements and LaTeX markers from being treated as boilerplate
    let protected_set = PROTECTED_SET.get_or_init(|| {
        RegexSet::new([
            r"```",
            r"\$\$",
            r"---",
            r"###",
            r"\|",
            r">",
            r"\{\\displaystyle",
            r"\\textstyle",
            r"\\begin\{aligned\}",
            r"\\end\{aligned\}",
            r"<pre",
            r"<code",
        ])
        .expect("Invalid protected marker regex patterns")
    });

    // Only perform regex matching if a protected formatting character is present
    let has_protected_char = line.contains(['`', '$', '-', '#', '|', '>', '\\', '{', '<']);
    if has_protected_char && protected_set.is_match(line) {
        return false;
    }

    // Since line.len() >= 10, it cannot be < 10
    false
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_boilerplate() {
        assert!(is_boilerplate("Cookie Policy"));
        assert!(is_boilerplate("all rights reserved"));
        assert!(is_boilerplate("!!!"));
        assert!(!is_boilerplate("This is normal content"));
        assert!(!is_boilerplate("```rust"));
        assert!(!is_boilerplate("$$ E=mc^2 $$"));
        assert!(!is_boilerplate("### Heading"));
    }

    #[test]
    fn test_compact_content() {
        let input = "Line 1\n\nLine 1\nCookie Policy\nLine 2";
        let compacted = compact_content(input, 100);
        assert_eq!(compacted, "Line 1\n\nLine 2");
    }
}
