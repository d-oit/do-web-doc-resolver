//! Direct HTTP fetch provider.
//!
//! Basic content extraction from HTML.

use crate::error::{ResolverError, detect_error_type};
use crate::providers::shared_client::get_client;
use crate::types::ResolvedResult;
use async_trait::async_trait;
use std::collections::HashSet;
use std::result::Result;
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};

/// Direct HTTP fetch provider
pub struct DirectFetchProvider {
    rate_limited: Arc<AtomicBool>,
}

impl DirectFetchProvider {
    /// Create a new direct fetch provider
    pub fn new() -> Self {
        Self {
            rate_limited: Arc::new(AtomicBool::new(false)),
        }
    }

    /// Check if rate limited
    pub fn is_rate_limited(&self) -> bool {
        self.rate_limited.load(Ordering::SeqCst)
    }

    /// Set rate limit
    pub fn set_rate_limited(&self, limited: bool) {
        self.rate_limited.store(limited, Ordering::SeqCst);
    }
}

impl Default for DirectFetchProvider {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl crate::providers::UrlProvider for DirectFetchProvider {
    fn name(&self) -> &str {
        "direct_fetch"
    }

    fn is_available(&self) -> bool {
        !self.is_rate_limited()
    }

    async fn extract(&self, url: &str) -> Result<ResolvedResult, ResolverError> {
        if self.is_rate_limited() {
            return Err(ResolverError::RateLimit(
                "Direct fetch is rate limited".to_string(),
            ));
        }

        let client = get_client();
        let response = client
            .get(url)
            .header("Accept", "text/html,application/xhtml+xml")
            .send()
            .await
            .map_err(|e| ResolverError::Network(e.to_string()))?;

        if response.status() == 429 {
            self.set_rate_limited(true);
            return Err(ResolverError::RateLimit("Rate limit exceeded".to_string()));
        }

        if response.status() == 404 {
            return Err(ResolverError::NotFound("URL not found".to_string()));
        }

        if !response.status().is_success() {
            let error_text = response.text().await.unwrap_or_default();
            return Err(detect_error_type(&error_text));
        }

        let html = response
            .text()
            .await
            .map_err(|e| ResolverError::Parse(e.to_string()))?;

        // Simple HTML to text conversion
        let content = strip_html(&html);

        Ok(ResolvedResult::new(url, Some(content), "direct_fetch", 0.5))
    }
}

/// Decode basic HTML entities using a single-pass scanner for performance
fn decode_entities(text: &str) -> String {
    if !text.contains('&') && !text.contains('\u{2060}') {
        return text.to_string();
    }

    let mut result = String::with_capacity(text.len());
    let mut chars = text.char_indices().peekable();

    while let Some((_, ch)) = chars.next() {
        if ch == '&' {
            let mut found_semi = false;
            let mut end_idx = 0;
            let temp_chars = chars.clone();

            for (idx, next_ch) in temp_chars.take(10) {
                if next_ch == ';' {
                    found_semi = true;
                    end_idx = idx + 1;
                    break;
                }
            }

            if found_semi {
                let start_idx = if let Some(&(idx, _)) = chars.peek() {
                    idx
                } else {
                    end_idx
                };

                let entity = &text[start_idx..end_idx];
                let decoded = match entity {
                    "lt;" => Some("<"),
                    "gt;" => Some(">"),
                    "quot;" => Some("\""),
                    "#x27;" | "#39;" => Some("'"),
                    "nbsp;" => Some(" "),
                    "copy;" => Some("©"),
                    "reg;" => Some("®"),
                    "trade;" => Some("™"),
                    "ndash;" => Some("–"),
                    "mdash;" => Some("—"),
                    "lsquo;" => Some("‘"),
                    "rsquo;" => Some("’"),
                    "ldquo;" => Some("“"),
                    "rdquo;" => Some("”"),
                    "#91;" => Some("["),
                    "#93;" => Some("]"),
                    "#8288;" => Some(""),
                    "amp;" => Some("&"),
                    _ => None,
                };

                if let Some(d) = decoded {
                    result.push_str(d);
                    // Advance main iterator to after the semicolon
                    while let Some(&(idx, _)) = chars.peek() {
                        if idx < end_idx {
                            chars.next();
                        } else {
                            break;
                        }
                    }
                    continue;
                }
            }
        }

        if ch == '\u{2060}' {
            // Remove word joiner
            continue;
        }

        result.push(ch);
    }

    result
}

/// Get an attribute value from a tag string
fn get_attribute(tag_content: &str, attr_name: &str) -> Option<String> {
    let lower = tag_content.to_lowercase();
    let pattern = format!("{}=", attr_name);
    if let Some(start) = lower.find(&pattern) {
        let value_part = &tag_content[start + pattern.len()..];
        if let Some(stripped) = value_part.strip_prefix('"') {
            if let Some(end) = stripped.find('"') {
                return Some(stripped[..end].to_string());
            }
        } else if let Some(stripped) = value_part.strip_prefix('\'') {
            if let Some(end) = stripped.find('\'') {
                return Some(stripped[..end].to_string());
            }
        } else {
            // Unquoted attribute
            let end = value_part
                .find(|c: char| c.is_whitespace() || c == '/' || c == '>')
                .unwrap_or(value_part.len());
            return Some(value_part[..end].to_string());
        }
    }
    None
}

/// Parse language hint from class attribute
fn parse_language_hint(class_attr: &str) -> Option<String> {
    for part in class_attr.split_whitespace() {
        if let Some(lang) = part.strip_prefix("language-") {
            return Some(lang.to_string());
        }
        if let Some(lang) = part.strip_prefix("lang-") {
            return Some(lang.to_string());
        }
        if part == "rust" {
            return Some("rust".to_string());
        }
    }
    None
}

/// State for HTML stripping
struct StripperState<'a> {
    result: String,
    skip_content_depth: usize,
    in_pre: bool,
    current_pre_lang: String,
    block_tags: HashSet<&'a str>,
    last_formula: String, // Track last extracted formula for deduplication
}

impl StripperState<'_> {
    fn new() -> Self {
        let block_tags = [
            "p",
            "div",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "tr",
            "pre",
            "br",
            "article",
            "section",
            "header",
            "footer",
            "nav",
            "aside",
            "main",
            "figure",
            "figcaption",
        ]
        .iter()
        .cloned()
        .collect();

        Self {
            result: String::new(),
            skip_content_depth: 0,
            in_pre: false,
            current_pre_lang: String::new(),
            block_tags,
            last_formula: String::new(),
        }
    }

    fn handle_tag(&mut self, tag_content: &str) {
        let tag_lower = tag_content.to_lowercase();
        let is_closing = tag_lower.starts_with('/');
        let tag_name = tag_lower
            .trim_start_matches('/')
            .split_whitespace()
            .next()
            .unwrap_or("");

        if matches!(tag_name, "script" | "style" | "svg" | "noscript") {
            if is_closing {
                self.skip_content_depth = self.skip_content_depth.saturating_sub(1);
            } else if !tag_lower.trim().ends_with('/') {
                self.skip_content_depth += 1;
            }
            return;
        }

        if tag_name == "math" {
            if is_closing {
                self.skip_content_depth = self.skip_content_depth.saturating_sub(1);
            } else if !tag_lower.trim().ends_with('/') {
                self.skip_content_depth += 1;
                if let Some(alt) = get_attribute(tag_content, "alttext") {
                    let formula = alt.trim().to_string();
                    let normalized = normalize_formula(&formula);
                    if !formula.is_empty() && normalized != self.last_formula {
                        self.result.push_str(" $");
                        self.result.push_str(&formula);
                        self.result.push_str("$ ");
                        self.last_formula = normalized;
                    }
                }
            }
            return;
        }

        if self.skip_content_depth > 0 {
            return;
        }

        if is_closing {
            self.handle_closing_tag(tag_name);
        } else {
            self.handle_opening_tag(tag_name, tag_content);
        }
    }

    fn handle_opening_tag(&mut self, tag_name: &str, tag_content: &str) {
        if self.block_tags.contains(tag_name)
            && !self.result.is_empty()
            && !self.result.ends_with('\n')
        {
            self.result.push('\n');
        }

        match tag_name {
            "code" => {
                if !self.in_pre {
                    self.result.push('`');
                } else if self.current_pre_lang.is_empty() {
                    if let Some(lang) =
                        get_attribute(tag_content, "class").and_then(|c| parse_language_hint(&c))
                    {
                        if self.result.ends_with("\n```\n") {
                            self.result.truncate(self.result.len() - 1);
                            self.result.push_str(&lang);
                            self.result.push('\n');
                            self.current_pre_lang = lang;
                        }
                    }
                }
            }
            "pre" => {
                self.in_pre = true;
                self.current_pre_lang = get_attribute(tag_content, "class")
                    .and_then(|c| parse_language_hint(&c))
                    .unwrap_or_default();
                self.result.push_str("\n```");
                self.result.push_str(&self.current_pre_lang);
                self.result.push('\n');
            }
            "img" => {
                if let Some(alt) = get_attribute(tag_content, "alt") {
                    if !alt.is_empty() {
                        let trimmed_alt = alt.trim();
                        if trimmed_alt.contains('\\')
                            || trimmed_alt.contains('^')
                            || trimmed_alt.contains('_')
                        {
                            let normalized = normalize_formula(trimmed_alt);
                            if normalized != self.last_formula {
                                self.result.push(' ');
                                let has_delimiters = trimmed_alt.starts_with('$')
                                    || trimmed_alt.starts_with("\\(")
                                    || trimmed_alt.starts_with("\\[");

                                if !has_delimiters {
                                    self.result.push('$');
                                }
                                self.result.push_str(trimmed_alt);
                                if !has_delimiters {
                                    self.result.push('$');
                                }
                                self.result.push(' ');
                                self.last_formula = normalized;
                            }
                        } else {
                            self.result.push(' ');
                            self.result.push_str(&alt);
                            self.result.push(' ');
                        }
                    }
                }
            }
            _ => {}
        }
    }

    fn handle_closing_tag(&mut self, tag_name: &str) {
        match tag_name {
            "code" => {
                if !self.in_pre {
                    self.result.push('`');
                }
            }
            "pre" => {
                self.in_pre = false;
                if !self.result.ends_with('\n') {
                    self.result.push('\n');
                }
                self.result.push_str("```\n");
            }
            _ => {
                if self.block_tags.contains(tag_name)
                    && !self.result.is_empty()
                    && !self.result.ends_with('\n')
                {
                    self.result.push('\n');
                }
            }
        }
    }
}

/// Normalize a LaTeX formula for deduplication
fn normalize_formula(formula: &str) -> String {
    formula
        .replace("{\\displaystyle", "")
        .replace(['}', '\\', ' '], "")
        .trim()
        .to_lowercase()
}

/// Strip HTML tags and convert to plain text with basic formatting
fn strip_html(html: &str) -> String {
    let mut state = StripperState::new();
    let mut in_tag = false;
    let mut current_tag = String::new();
    let mut quote_char: Option<char> = None;

    let mut chars = html.chars().peekable();
    while let Some(ch) = chars.next() {
        if in_tag {
            if let Some(q) = quote_char {
                if ch == q {
                    quote_char = None;
                }
                current_tag.push(ch);
            } else if ch == '"' || ch == '\'' {
                quote_char = Some(ch);
                current_tag.push(ch);
            } else if ch == '>' {
                in_tag = false;
                state.handle_tag(&current_tag);

                // If we just entered a script or style tag, look for the closing tag
                // to avoid getting tripped up by '<' or '>' inside the content
                let tag_lower = current_tag.to_lowercase();
                let tag_name = tag_lower.split_whitespace().next().unwrap_or("");
                if matches!(tag_name, "script" | "style") && !tag_lower.starts_with('/') {
                    // Optimized skip: look for </script or </style efficiently
                    let close_tag_start = format!("</{}", tag_name);
                    let mut buffer = String::with_capacity(tag_name.len() + 2);
                    for c in chars.by_ref() {
                        if c == '<' {
                            buffer.clear();
                            buffer.push('<');
                        } else if !buffer.is_empty() {
                            buffer.push(c);
                            if buffer.to_lowercase() == close_tag_start {
                                // Found it, now eat until >
                                for next_c in chars.by_ref() {
                                    if next_c == '>' {
                                        break;
                                    }
                                }
                                break;
                            }
                            if buffer.len() > close_tag_start.len() {
                                buffer.clear();
                            }
                        }
                    }
                    // We've skipped the content and the closing tag
                    state.skip_content_depth = state.skip_content_depth.saturating_sub(1);
                }
            } else {
                current_tag.push(ch);
            }
        } else if ch == '<' {
            // Special handling for comments
            let next_3: String = chars.clone().take(3).collect();
            if next_3 == "!--" {
                current_tag.clear();
                // Skip comment
                for c in chars.by_ref() {
                    if c == '>' && current_tag.ends_with("--") {
                        break;
                    }
                    current_tag.push(c);
                }
                continue;
            }
            in_tag = true;
            current_tag.clear();
            quote_char = None;
        } else if state.skip_content_depth == 0 {
            state.result.push(ch);
        }
    }

    let decoded = decode_entities(&state.result);

    // Clean up whitespace
    let mut final_result = String::new();
    let mut last_was_empty = false;
    let mut in_code_block = false;

    for line in decoded.lines() {
        let is_code_fence = line.trim_start().starts_with("```");
        let trimmed = if is_code_fence {
            in_code_block = !in_code_block;
            line.trim()
        } else if in_code_block {
            line.trim_end()
        } else {
            line.trim()
        };

        if trimmed.is_empty() {
            if in_code_block {
                final_result.push('\n');
                last_was_empty = false;
            } else if !last_was_empty && !final_result.is_empty() {
                final_result.push_str("\n\n");
                last_was_empty = true;
            }
        } else {
            final_result.push_str(trimmed);
            final_result.push('\n');
            last_was_empty = false;
        }
    }

    final_result.trim().to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::providers::UrlProvider;

    #[test]
    fn test_provider_name() {
        let provider = DirectFetchProvider::new();
        assert_eq!(provider.name(), "direct_fetch");
    }

    #[test]
    fn test_strip_html() {
        let html = "<html><body><h1>Title</h1><p>Hello <b>world</b> &amp; others</p><script>alert(1)</script></body></html>";
        let result = strip_html(html);
        assert!(result.contains("Title"));
        assert!(result.contains("Hello world & others"));
        assert!(!result.contains("alert(1)"));
    }

    #[test]
    fn test_code_blocks() {
        let html = "<p>Use <code>fn main()</code></p><pre>println!(\"Hi\");</pre>";
        let result = strip_html(html);
        assert!(result.contains("`fn main()`"));
        assert!(result.contains("```"));
        assert!(result.contains("println!(\"Hi\");"));
    }

    #[test]
    fn test_code_blocks_with_lang() {
        let html = "<pre class=\"language-rust\"><code>fn main() {}</code></pre>";
        let result = strip_html(html);
        assert!(result.contains("```rust"));
        assert!(!result.contains("`` ` ``")); // Ensure no double backticks
    }

    #[test]
    fn test_code_blocks_nested_lang() {
        let html = "<pre><code class=\"language-python\">print(1)</code></pre>";
        let result = strip_html(html);
        assert!(result.contains("```python"));
    }

    #[test]
    fn test_img_alt() {
        let html = "<img src=\"math.svg\" alt=\"x^2 + y^2 = z^2\">";
        let result = strip_html(html);
        assert!(result.contains("x^2 + y^2 = z^2"));
    }

    #[test]
    fn test_img_alt_latex() {
        let html = "<img src=\"math.svg\" alt=\"{\\displaystyle x^2 + y^2 = z^2}\">";
        let result = strip_html(html);
        assert!(result.contains("${\\displaystyle x^2 + y^2 = z^2}$"));
    }

    #[test]
    fn test_skip_math_svg() {
        let html = "<div>Keep this <math><mi>x</mi></math><svg><rect/></svg></div>";
        let result = strip_html(html);
        assert!(result.contains("Keep this"));
        assert!(!result.contains("<mi>"));
        assert!(!result.contains("x"));
        assert!(!result.contains("<rect"));
    }

    #[test]
    fn test_extended_entities() {
        let html = "<p>Copyright &copy; 2026 &mdash; All rights &reg; reserved &trade;.</p>";
        let result = strip_html(html);
        assert!(result.contains("Copyright © 2026 — All rights ® reserved ™."));
    }

    #[test]
    fn test_strip_html_quotes_in_tags() {
        let html = r#"<div data-json='{"foo": ">"}'>leaked content</div>"#;
        let result = strip_html(html);
        assert_eq!(result, "leaked content");
    }

    #[test]
    fn test_strip_html_script_with_gt() {
        let html = r#"<script>if (1 > 0) console.log("greater");</script>Keep this"#;
        let result = strip_html(html);
        assert_eq!(result, "Keep this");
    }
}
