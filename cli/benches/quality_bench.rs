use criterion::{Criterion, criterion_group, criterion_main};
use do_wdr_lib::bias_scorer::score_result;
use do_wdr_lib::quality::score_content;
use std::hint::black_box;

fn bench_quality_scoring(c: &mut Criterion) {
    let markdown = r#"
---
relevance_score: 0.95
intent_category: documentation
token_estimate: 1500
last_updated: 2026-05-20
---

# Technical Documentation

[ANCHOR: SUMMARY]
This is a summary of the technical documentation.

[ANCHOR: TECHNICAL_DETAILS]
Here are some technical details about the system.
It includes many lines of text to simulate a real-world document.
Repeat this line to test deduplication.
Repeat this line to test deduplication.
Repeat this line to test deduplication.

[ANCHOR: COMPARISON]
Comparison with other systems.

[ANCHOR: CITATIONS]
1. Source A
2. Source B

Cookie policy: we use cookies.
Subscribe to our newsletter.
JavaScript is required for this page.
Log in to see more.
Sign up for an account.
Another cookie mentioned here.
One more subscribe button.

"#
    .repeat(10);

    let links = vec![
        "https://example.com/1".to_string(),
        "https://example.com/2".to_string(),
    ];

    c.bench_function("score_content", |b| {
        b.iter(|| {
            score_content(black_box(&markdown), black_box(&links), black_box(0.8));
        });
    });
}

fn bench_bias_scoring(c: &mut Criterion) {
    let content = r#"
# Sample Page

This is a sample page with some content.
It has multiple lines.

Cookie Policy: We use cookies.
All rights reserved (c) 2026.
Privacy Policy is available here.

```rust
fn main() {
    println!("Hello, world!");
}
```

Subscribe to our newsletter for more updates.
Follow us on Twitter.
Click here to learn more.
buy now cheap discount free trial best price
"#
    .repeat(10);

    c.bench_function("score_result", |b| {
        b.iter(|| {
            score_result(
                black_box("https://github.com/rust-lang/rust"),
                black_box(&content),
            );
        });
    });
}

criterion_group!(benches, bench_quality_scoring, bench_bias_scoring);
criterion_main!(benches);
