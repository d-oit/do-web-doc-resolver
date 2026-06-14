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

/// Decode basic HTML entities
fn decode_entities(text: &str) -> String {
    text.replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", "\"")
        .replace("&#x27;", "'")
        .replace("&#39;", "'")
        .replace("&nbsp;", " ")
        .replace("&copy;", "©")
        .replace("&reg;", "®")
        .replace("&trade;", "™")
        .replace("&ndash;", "–")
        .replace("&mdash;", "—")
        .replace("&lsquo;", "‘")
        .replace("&rsquo;", "’")
        .replace("&ldquo;", "“")
        .replace("&rdquo;", "”")
        .replace("&#8288;", "") // word joiner
        .replace("&amp;", "&") // Ampersand last to avoid double-unescaping
        .replace("\u{2060}", "") // Remove word joiner
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

        if matches!(tag_name, "script" | "style" | "math" | "svg" | "noscript") {
            if is_closing {
                self.skip_content_depth = self.skip_content_depth.saturating_sub(1);
            } else if !tag_lower.trim().ends_with('/') {
                self.skip_content_depth += 1;
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
                        self.result.push(' ');
                        let trimmed_alt = alt.trim();
                        if trimmed_alt.starts_with("{\\displaystyle") {
                            self.result.push('$');
                            self.result.push_str(trimmed_alt);
                            self.result.push('$');
                        } else {
                            self.result.push_str(&alt);
                        }
                        self.result.push(' ');
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

/// Strip HTML tags and convert to plain text with basic formatting
fn strip_html(html: &str) -> String {
    let mut state = StripperState::new();
    let mut in_tag = false;
    let mut current_tag = String::new();

    for ch in html.chars() {
        if ch == '<' {
            in_tag = true;
            current_tag.clear();
        } else if ch == '>' {
            in_tag = false;
            state.handle_tag(&current_tag);
        } else if in_tag {
            current_tag.push(ch);
        } else if state.skip_content_depth == 0 {
            state.result.push(ch);
        }
    }

    let decoded = decode_entities(&state.result);

    // Clean up whitespace
    let mut final_result = String::new();
    let mut last_was_empty = false;

    for line in decoded.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() {
            if !last_was_empty && !final_result.is_empty() {
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
}
