---
name: science-approval
description: Generates the official Scientific Approval & Celebration Ceremony artifact featuring empirical validation metrics, silicon milestone verification, interactive 'Celebrate' and 'Approve' controls, and plan-stage Proceed buttons.
---

# Scientific Approval & Celebration Protocol

This skill governs the generation of interactive approval artifacts and celebration ceremonies across H1OS engineering milestones and planning phases.

---

## 1. Lifecycle-Phased Widget Protocol

The interaction follows a strict two-stage lifecycle:

1. **Planning Stage Mandate (Awaiting Plan Approval):**
   - Whenever authoring an architecture plan, refactoring roadmap, or `/plan` response:
     - Save the plan as an artifact with:
       ```json
       {
         "ArtifactMetadata": {
           "RequestFeedback": true,
           "UserFacing": true,
           "Summary": "<Plan Title> - Ready for Review & Proceed"
         }
       }
       ```
     - Mount the native interactive **"Proceed"** button on the artifact.
     - Embed **ONLY** the **Approval Widget (`science_approve_widget.html`)** in the chat response:
       ```html
       <agent-embed src="file:///<artifact_directory>/science_approve_widget.html"></agent-embed>
       ```
     - **NEVER** display the celebration widget during the planning phase.

2. **Execution & Victory Stage Mandate (After Successful Execution):**
   - Only after an approved plan has been completely implemented, compiled, and empirically verified:
     - Embed **ONLY** the **Celebration Widget (`science_celebrate_widget.html`)** in the chat response:
       ```html
       <agent-embed src="file:///<artifact_directory>/science_celebrate_widget.html"></agent-embed>
       ```
     - Triggers celebratory particle physics (confetti/stars), synthesized victory audio fanfare, cheer counter, and live telemetry tickers.
     - **NEVER** display the approval widget after execution has succeeded (the plan is already executed).

---

## 2. Mathematical & Empirical Compliance

Per [`.agents/rules/science.md`](file:///c:/Users/Matt/Documents/GitHub/H1OS/.agents/rules/science.md):
- Every approval ceremony must explicitly cite the physical invariants, register configurations, and empirical measurements verified (e.g. August-Roche-Magnus psychrometrics, eFuse ADC calibration curves, zero-leakage pin pad isolation).
- Never celebrate ungrounded heuristics or unverified builds. All celebratory sessions must be preceded by a clean build (`build_dev` / `build_prod` with 0 errors).
