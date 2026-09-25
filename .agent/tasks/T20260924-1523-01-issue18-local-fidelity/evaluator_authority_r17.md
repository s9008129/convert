# R17 evaluator authority/applicability audit (redacted)

**Determination: NEEDS_RESCORING.** The P7-C rubric is semantically usable as a scoring instrument for the fresh blind cohort, but the existing three Gemini score medians are not decision-valid denominators without re-adjudication. This is not a finding that P7-C's local candidate scores should be reused; they remain excluded.

## User authority

The authoritative task source is the user attachment (§35, lines 1991–2048): it requires three fresh blind Gemma outputs and three fresh blind Qwen outputs; the four dimensions Completeness, Faithfulness, Traceability, Usability; use of original unrounded Gemini medians; every output/dimension at least 80% of that median; and zero adjudicated major fidelity hard failures. The attachment's §35 does not adopt P7-C's stricter `<10%` gap rule.

## Identified frozen inputs

- Frozen P7-C rubric: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/quality/rubric-v1.md`, final SHA-256 `ecdf138bc3e957d0747ed3e95f87205be384c35959b716d1ea61cc3a419c64eb`.
- Rubric dimensions/formulas are defined at lines 17–45. It uses the same four dimensions and transcript-grounded scoring, but its §Strict parity formula at line 41 imposes `gap < 0.10`; that gate must not be imported.
- The frozen score sheets are identified in the prior execution record at `.agent/tasks/T20260923-2050-01-local-extraction-adherence/execution.md:672`: A `4ea698ce0f6c427c1428319bf4ff9a75f328a9a06205aeced3ba2122b377051d`, B `e3d4ab5ddc44b8266e6c4725aa3493ad2ac4d3f8b9fea0a4cbc87a4ee67f67e0`, C `cfa0d17497dc28cbc7b70940320e7e47bf1f255d35baa22339ff776cf29496d3`.
- Source identity audit `.agent/tasks/T20260923-2050-01-local-extraction-adherence/execution.md:674` records the exact rubric/transcript/checklist hashes matched by the locked sheets. Transcript SHA-256 `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0`; checklist SHA-256 `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`.
- The redacted cloud-median audit `[ignored cloud-median audit artifact]` (SHA-256 `5c6a727ddc8e115d126ac09127a855ea6051d3e198ad1cb07746b65392ed53ec`) identifies the cloud cohort and exact medians: `83.9285714286 / 89.7959183673 / 93.8775510204 / 85`. The three Gemini source-output hashes linked to the blinded score records are `8a23d79913564152f0c0e2aba189ce0d224d48b4c27d9ab3be807ac2f9893c98`, `e1511ebcaaaced670b9ebe6c414d517bd530b637449ca47946de7c4d0262baca`, and `ffa23bbc87f4321cf6d1cd7f618a56ba16f3322de1e4993e71b1ecd3a9964afd`. The exact medians numerically match the user's four displayed values; the unrounded values above are preserved.
- The ignored identity-map artifact `[ignored source identity artifact]` (SHA-256 `152b14acd58268c900a701a00242bcb0d4647eb6c6d7d67a27d7a54852f9c282`) links the cloud aliases to those source-output hashes. **Yes:** those same three hash-identified Gemini outputs can be re-scored alone; no P7-C local-candidate outputs need be opened, selected, or used.

## Applicability defect

The relevant adjudication `[ignored reconciliation artifact]`, SHA-256 `76963e2b7deb3ef4e8345c85d8942aeaa00d7078a2bd0fe56b688304e401593b`, has an `overall` summary saying reliable three-way claim alignment was unavailable for **all nine** aliases. This includes the three cloud/Gemini baseline aliases, not only local candidates. Each of those three baseline aliases has `claim_reconciliation.status: BLOCKED`; each also has unresolved core-fact labels (IDs only; not reproduced here). Prior execution `.agent/tasks/T20260923-2050-01-local-extraction-adherence/execution.md:693` independently records the crosswalk block and unresolved fact ties.

Therefore the crosswalk failure is **not independent** of denominator validity: the Gemini dimension scores themselves came from records whose claim-level adjudication remains unresolved. The transcript/checklist/rubric identity match proves shared inputs, and the source hashes establish which three outputs supplied the median, but neither repairs disputed scoring. The values are reproducible arithmetic over the prior scores, not yet a valid adjudicated baseline.

## Required next step / scope

Before fresh blind 3+3 scoring, re-score **only the same three original Gemini outputs**, identified by the hashes above, under the frozen four-dimension rubric with complete reliable independent claim/fact adjudication and verified source-hash linkage. Do not rescore or use any P7-C local-candidate outputs. If the original Gemini outputs or a valid adjudication cannot be established, mark the affected quality acceptance `BLOCKED/AUTHORITY` with this precise cause. Preserve the user's `>=80%` per-output/per-dimension rule and zero-major-hard-fail requirement; never import P7-C's `<10%` gap gate.

No transcript, output text, prompts, mapping contents, or free-text rationale is included in this note; no raw content was persisted to the task evidence.
