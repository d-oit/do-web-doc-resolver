use criterion::{Criterion, criterion_group, criterion_main};
use std::hint::black_box;

// Current implementation
fn decode_entities_old(text: &str) -> String {
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
        .replace("&#91;", "[")
        .replace("&#93;", "]")
        .replace("&#8288;", "") // word joiner
        .replace("&amp;", "&") // Ampersand last to avoid double-unescaping
        .replace("\u{2060}", "") // Remove word joiner
}

// Proposed optimized implementation
fn decode_entities_optimized(text: &str) -> String {
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
            continue;
        }

        result.push(ch);
    }

    result
}

fn bench_decode_entities(c: &mut Criterion) {
    let text_with_entities = "This &lt;is&gt; a &quot;test&quot; with many &amp; various entities like &copy;, &reg;, &trade;, &ndash;, &mdash;, &lsquo;, &rsquo;, &ldquo;, &rdquo;, &#91;, &#93;, &#8288;, \u{2060}, &#x27;, &#39;, &nbsp;.";
    let text_no_entities = "This is a test with no entities at all. Just some plain text to see the overhead of the replacement mechanism when nothing matches.";
    let long_text = text_with_entities.repeat(10);

    let mut group = c.benchmark_group("decode_entities");

    group.bench_function("old_with_entities", |b| {
        b.iter(|| decode_entities_old(black_box(text_with_entities)))
    });

    group.bench_function("optimized_with_entities", |b| {
        b.iter(|| decode_entities_optimized(black_box(text_with_entities)))
    });

    group.bench_function("old_no_entities", |b| {
        b.iter(|| decode_entities_old(black_box(text_no_entities)))
    });

    group.bench_function("optimized_no_entities", |b| {
        b.iter(|| decode_entities_optimized(black_box(text_no_entities)))
    });

    group.bench_function("old_long", |b| {
        b.iter(|| decode_entities_old(black_box(&long_text)))
    });

    group.bench_function("optimized_long", |b| {
        b.iter(|| decode_entities_optimized(black_box(&long_text)))
    });

    group.finish();
}

criterion_group!(benches, bench_decode_entities);
criterion_main!(benches);
