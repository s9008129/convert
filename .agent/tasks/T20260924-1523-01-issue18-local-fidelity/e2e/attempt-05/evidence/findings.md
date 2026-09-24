# Stage05 attempt 05 independent findings (redacted)

## Freshness

Plan R9, Handoff, and Review 08 identities agree. The immutable Stage04 execution snapshot identity at this acceptance startup was SHA-256 `45d55b0aaf4104a69e4f7d47089876aa54a2f434ca37df52098451cf5266f2ef`.

## Confirmed synthetic contract failures

1. `FactClaim.fingerprint` omits relation `direction`, claim `status`, and `uncertainty`. `consolidate_claims` therefore merged claims that represented opposite directions and different epistemic status. Observed result for three synthetic claims: one retained claim (`subject_to_object`, `asserted`) and zero conflicts. This silently discards approved R2/R4 semantics and is a product defect.
2. `fidelity_firewall` accepts a rendered required causal relation when the expected relation substring and correct metadata are present even if the same rendered section also contains a contradictory predicate variant for the same entities. Observed synthetic result: `accepted=True`, no relation issues, no unsupported additions. The check does not reject this contradictory extra relation, violating the approved R6 distortion/unsupported-addition protection.

These are reproduced directly against repository code with synthetic values only. They do not use user transcript or model output. Both are bounded implementation defects within the approved R9 contract; no plan premise change is asserted.

## Controlled model outcome, as reported by parent

Two fresh Qwen 3.8 27B attempts each reached the extraction boundary but ended with `LocalPipelineV2Error` after schema repair; the second reproduced the same parse-failure class. Because this verifier did not inspect output snapshots/payloads, the exact parse cause remains unknown. The model journey did not produce an accepted meeting record.
