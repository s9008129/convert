# Independent Gemini rescore — attempt 03

**Overall status:** `BLOCKED/AUTHORITY`

**Rubric SHA-256:** `ecdf138bc3e957d0747ed3e95f87205be384c35959b716d1ea61cc3a419c64eb`

## Frozen output identities

| Blind alias | Source SHA-256 |
|---|---|
| O1 | `8a23d79913564152f0c0e2aba189ce0d224d48b4c27d9ab3be807ac2f9893c98` |
| O2 | `e1511ebcaaaced670b9ebe6c414d517bd530b637449ca47946de7c4d0262baca` |
| O3 | `ffa23bbc87f4321cf6d1cd7f618a56ba16f3322de1e4993e71b1ecd3a9964afd` |

## Dimension results

| Dimension | O1 | O2 | O3 | Three-output median | Status |
|---|---:|---:|---:|---:|---|
| Completeness | `23.5/28 × 100 = 83.9285714286` | `19.5/28 × 100 = 69.6428571429` | `27/28 × 100 = 96.4285714286` | `83.9285714286` | `SCORED` |
| Faithfulness | — | — | — | — | `BLOCKED/AUTHORITY` |
| Traceability | — | — | — | — | `BLOCKED/AUTHORITY` |
| Usability | `(100+100+75+75+50)/5 = 80` | `(100+100+75+75+75)/5 = 85` | `(100+100+75+75+75)/5 = 85` | `85` | `SCORED` |

Faithfulness and traceability were not scored: a complete, reliable atomic-claim denominator and anchor adjudication was not established for all three outputs. The claim-level audit is also required to determine whether zero major fidelity hard failures holds; that result is `UNDETERMINED`. These dimensions and the hard-fail result remain `BLOCKED/AUTHORITY`; no prior scores were reused. No `<10%` gap rule was applied.
