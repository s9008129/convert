# Evaluator rescore R17 — output identity correction

**Recorded:** 2026-09-25 10:57 CST (+0800)
**Purpose:** Append-only correction to the O1–O3 identity table in `evaluator_rescore_r17.md`. The prior report remains unchanged and must not be used as output-identity evidence.

## Correct source-output identities

The same three original Gemini output SHA-256 values are independently recorded in `evaluator_rescore_attempt-02.md`, `evaluator_rescore_attempt-03.md`, and `evaluator_authority_r17.md`:

| Blind alias | Original Gemini source-output SHA-256 |
|---|---|
| O1 | `8a23d79913564152f0c0e2aba189ce0d224d48b4c27d9ab3be807ac2f9893c98` |
| O2 | `e1511ebcaaaced670b9ebe6c414d517bd530b637449ca47946de7c4d0262baca` |
| O3 | `ffa23bbc87f4321cf6d1cd7f618a56ba16f3322de1e4993e71b1ecd3a9964afd` |

`evaluator_authority_r17.md` links these three output hashes to the cloud aliases and identifies them as the original Gemini outputs. Its other three hashes—`5c6a727ddc8e115d126ac09127a855ea6051d3e198ad1cb07746b65392ed53ec`, `76963e2b7deb3ef4e8345c85d8942aeaa00d7078a2bd0fe56b688304e401593b`, and `152b14acd58268c900a701a00242bcb0d4647eb6c6d7d67a27d7a54852f9c282`—identify respectively the cloud-median audit, reconciliation, and source identity-map artifacts. They are not Gemini output hashes.

## Scope and remaining status

This correction supersedes only the incorrect O1–O3 hash table in `evaluator_rescore_r17.md`; it does not create new output-byte verification, semantic claim/fact adjudication, scores, valid medians, or a quality-threshold result. The R17 rescore remains `BLOCKED/AUTHORITY`: the original Gemini outputs still require complete, source-grounded semantic adjudication under an authorized privacy-preserving method before they can serve as denominators. No source/output payload was read or copied while preparing this correction.
