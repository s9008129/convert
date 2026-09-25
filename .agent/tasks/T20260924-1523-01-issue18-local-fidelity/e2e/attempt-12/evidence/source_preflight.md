# C1 Raw-Source Preflight (Redacted)

- Checked: 2026-09-25 (Asia/Taipei); attempt-12 Stage05, R17.
- Scan scope: the previously authorized local cache root only. No other roots were added.
- Designated source/run identity: the expected run-record SHA-256 matched exactly once (`e93c2666d8038894fc691a526ca82ffc6e1c3410f6f6aac322800eef0c6c4414`); the unique designated run identifier linked to the expected raw-input digest (`b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0`). One run-record match and one designated run-ID record were observed.
- Raw-input identity: 13 byte-identical local copies matched the expected SHA-256 `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0`.
- Locator handling: the previously identified locator artifact hash matched once (`9ff1ff5232c8c53b423111ced0fa0d7cc458f8b4facc99c5c4847475692d0f20`). Its relation/metadata were not used as authority. The source-quote hash matched once (`13eb4af25d62db492853c83cc574ce5605c3224be28de083dca725d2a7e9a583`). After NFKC and whitespace normalization, its exact occurrence count was one in each of the 13 byte-identical inputs.
- Raw-derived relation audit: the minimal occurrence context was examined in memory across the identical inputs. A conservative independent cue check found no decisive, unambiguous causal-direction signal; the expected typed direction remains **INCONCLUSIVE**. No locator relation, prior model output, or synthetic output was consulted. No raw source, quotation, private path, or model output was emitted or stored.
- Decision: source/run identity and unique occurrence **PASS**; raw-derived relation **BLOCKED/AUTHORITY**. Because all three prerequisites did not conclusively pass, no source-bearing model call was made.
