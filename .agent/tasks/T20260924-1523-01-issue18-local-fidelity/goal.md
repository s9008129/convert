# Goal — Issue #18 Local Fidelity

The owner wants GPT-6 to finish Issue #18 end-to-end on the local repo, not merely propose a prompt tweak.

Primary outcome:
- identify the first source-fidelity divergence in the local Gemma/Qwen summarization pipeline;
- repair the evidenced mechanism with the smallest safe change;
- prove it with fail-first tests;
- rerun local E2E;
- produce a fresh blind 3+3 cohort;
- meet the frozen per-output/per-dimension Gemini-median × 0.80 gate with no major fidelity hard fail.

The most important first-principles insight is that the current local path cuts off the transcript after extraction: final generation, refinement, and the general local validator operate on derived notes. That makes extraction errors irreversible and notes-vs-summary agreement insufficient to prove truth. However, the historical first divergence is still UNKNOWN because stage outputs were not retained.

Therefore execution order is mandatory:
observability → controlled first-divergence evidence → fail-first mechanism test → minimal repair → regression → E2E → fresh blind cohort.

Read plan.md and handoff.md before editing.