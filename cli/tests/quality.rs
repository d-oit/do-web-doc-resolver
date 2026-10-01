use do_wdr_lib::quality::score_content;

#[test]
fn test_quality_scoring() {
    let good_content =
        "This is a long enough content that should be considered acceptable and unique.\n"
            .repeat(20);
    let links = vec!["https://example.com".to_string()];

    let score = score_content(&good_content, &links, 0.65);
    assert!(score.acceptable);
    assert!(score.score > 0.7);

    let short_content = "Too short";
    let score = score_content(short_content, &links, 0.65);
    assert!(!score.acceptable);
    assert!(score.too_short);
}

#[test]
fn test_noisy_content() {
    let noisy_content =
        "Accept cookies. Subscribe to our newsletter. JavaScript is required. ".repeat(5);
    let links = vec!["https://example.com".to_string()];

    let score = score_content(&noisy_content, &links, 0.65);
    assert!(score.noisy);
}

/// Body lines that are unique (so they do not trip duplicate detection) and
/// long enough overall to clear the minimum-length threshold.
fn padded_body() -> String {
    (0..20)
        .map(|i| format!("Unique body line {i} used only for length padding.\n"))
        .collect()
}

#[test]
fn test_frontmatter_bonus_requires_fields_inside_the_block() {
    let links = vec!["https://example.com".to_string()];
    let body = padded_body();

    // Genuine frontmatter: all four fields sit inside the opening/closing block.
    let real_frontmatter = format!(
        "---\nrelevance_score: 1.0\nintent_category: docs\n\
         token_estimate: 100\nlast_updated: 2026-10-01\n---\n{body}"
    );

    // The same four fields, but only in the body *after* the closing delimiter.
    let spoofed = format!(
        "---\n{body}---\nrelevance_score: 1.0\nintent_category: docs\n\
         token_estimate: 100\nlast_updated: 2026-10-01\n"
    );

    let real = score_content(&real_frontmatter, &links, 0.65);
    let fake = score_content(&spoofed, &links, 0.65);

    // Both bodies are structurally identical, so the only difference is the
    // frontmatter bonus: the spoofed variant must not earn it.
    assert!(
        (real.score - fake.score - 0.05).abs() < f32::EPSILON,
        "expected frontmatter bonus only for the real block: real={} fake={}",
        real.score,
        fake.score
    );
}

