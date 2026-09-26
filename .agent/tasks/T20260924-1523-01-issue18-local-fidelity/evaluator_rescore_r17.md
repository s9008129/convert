# Independent rescore R17

**Status:** `BLOCKED/AUTHORITY`

## Scope and frozen inputs

This rescore was limited to the three original Gemini outputs, identified only by blind alias and SHA-256:

| Blind alias | Original content SHA-256 |
|---|---|
| O1 | `5c6a727ddc8e115d126ac09127a855ea6051d3e198ad1cb07746b65392ed53ec` |
| O2 | `76963e2b7deb3ef4e8345c85d8942aeaa00d7078a2bd0fe56b688304e401593b` |
| O3 | `152b14acd58268c900a701a00242bcb0d4647eb6c6d7d67a27d7a54852f9c282` |

Frozen materials recorded in the approved plan:

- P7-C rubric SHA-256: `ecdf138bc3e957d0747ed3e95f87205be384c35959b716d1ea61cc3a419c64eb`
- Checklist SHA-256: `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`
- Transcript SHA-256: `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0`

## Adjudication result

No output was scored. The P7-C reconciliation finding invalidates the old medians, so none were reused. A fresh score under the four user-authorized dimensions and rubric formula requires semantic comparison of private output wording against the source/checklist. The privacy boundary prohibits placing that wording in tool output or this artifact. The available local scripting interface can verify opaque bytes and hashes but cannot make the required independent semantic judgments without exposing the text; model/API calls are expressly disallowed.

Accordingly, exact unrounded new medians are **not available**, and the 80% threshold / zero-major-hard-fail outcome is **undetermined**. The P7-C `<10%` gap gate was explicitly excluded and was not applied. No local candidate was inspected or scored. No raw content, claims, quotations, names, or private paths are included here.

## Safe disposition

`BLOCKED/AUTHORITY` is limited to this independent rescore. Resume only through an evaluation method that enables source-grounded semantic review while keeping all private text out of tool outputs, messages, and artifacts; otherwise these outputs remain unscored.
