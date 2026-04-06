## 2025-05-15 - [SSRF Protection Gap in llms.txt Fetching]
**Vulnerability:** The `fetch_llms_txt` function in the Python core and the entire Rust CLI's URL resolution cascade were missing SSRF protections, allowing outbound requests to localhost and private network ranges.
**Learning:** Security controls like SSRF protection must be applied consistently across all entry points that perform outbound HTTP requests, including secondary paths like probing for `llms.txt`.
**Prevention:** Centralize URL validation in a shared utility and enforce its use in all network-bound providers. For multi-language repositories, ensure parity in security controls between the core implementation (Python) and auxiliary tools (Rust CLI).
