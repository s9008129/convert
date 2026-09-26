# C1 private source preflight (redacted)

- Checked at: 2026-09-24 20:55 UTC.
- The user-designated source identity is hash-linked to the historical run record: the run manifest's `run_id` is `170d08f286b145f59798da29c7ded61b`; it is the only local JSON run record carrying that ID.
- The manifest's `claim_id` is `C-R03-F056-CAUSAL-DIRECTION`. Its `transcript_sha256` and the run's source input SHA-256 both equal `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0`.
- Both matching local transcript files have that SHA-256. The selected-target source quote's SHA-256 is `13eb4af25d62db492853c83cc574ce5605c3224be28de083dca725d2a7e9a583`; after NFKC plus whitespace normalization it has exactly one occurrence in each transcript.
- The ignored locator/claim artifact has SHA-256 `9ff1ff5232c8c53b423111ced0fa0d7cc458f8b4facc99c5c4847475692d0f20`. It is treated only as an untrusted locator; its author and embedded relation are not trusted.
- **Relation authority: inconclusive.** The unique source occurrence does not, by itself, explicitly establish the locator's subject–predicate–object direction. Contextual causal cues are insufficient to prove that typed relation. The attachment designates the source/claim but does not make an ambiguous linguistic derivation conclusive.
- Therefore C1 is `BLOCKED/AUTHORITY`; no Qwen model call was made or counted as C1 acceptance. The selected quote and all raw text remain unprinted and untracked. The source, transcript, and locator paths are covered by the existing `data/cache/*` ignore rule.

