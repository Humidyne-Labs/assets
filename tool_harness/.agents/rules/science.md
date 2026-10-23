# Mathematical & Empirical Grounding Policy

This rule governs the physical, thermodynamic, and mathematical models implemented in **H1OS**.

---

## 1. Math Precedes Code

> *"Code solves a problem that math already did."*

1. **No Ad-Hoc Heuristics:** Never implement heuristic curve-fitting, synthetic sensor scaling, or arbitrary correction dividers when underlying physics formulations exist.
2. **Thermodynamic Invariants:**
   - Ground environmental algorithms in thermodynamic conservation laws.
   - For psychrometrics: actual water vapor pressure ($e$) and Dew Point ($T_{\text{dew}}$) are invariants unaffected by local PCB self-heating. Calculate true metrics using August-Roche-Magnus formulations.
   - For power: calculate State of Charge (SoC) using empirical 13-point LiPo Open-Circuit Voltage (OCV) lookups rather than arbitrary linear approximations.

---

## 2. Reproducibility & Mathematical Verification

1. **Citation of Governing Equations:** Every non-trivial calculation in code or documentation must cite its physical formula, IEEE standard, or component datasheet equation.
2. **Deterministic & Unit-Testable:**
   - Keep mathematical algorithms in pure, stateless functions (`orch_math.c`).
   - Pure math routines must be testable on host compilation test fixtures without hardware dependencies.
3. **Integer Fixed-Point in Coprocessor Domains:**
   - Because the ULP-RISC-V coprocessor lacks hardware floating-point units (FPU), express temperatures in centi-degrees ($1^\circ\text{C} = 100$) and relative humidity in centi-percent to preserve mathematical precision without software emulation penalties.
