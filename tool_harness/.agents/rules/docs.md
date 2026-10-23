# Documentation Governance, Historical Memory & OSHW Attribution

This rule governs documentation integrity, living memory tracking, and open-source attribution in **H1OS**.

---

## 1. Documentation is Law

> *"Documentation is memory and history reflective of progress and hard lessons learned. We document the weeds so we can find flowers next time."*

1. **Mandatory & Methodical Updates:**
   - Documentation is not an optional afterthought; it is committed alongside code changes.
   - When APIs, state machines, or pinouts change, the corresponding documentation in `docs/` must be updated in the same patch.
2. **Documenting the Weeds (Failure Analysis):**
   - Record design dead-ends, silicon hardware bugs, and discarded workarounds in `docs/architecture/08_lessons_learned.md` and `ERRATA.md`.
   - Never erase historical technical rationale—distill it into authoritative digests so future maintainers avoid repeating mistakes.

---

## 2. Open Source Hardware (OSHW) & Attribution

1. **Commitment to OSHW & OSS:**
   - Design public operating system APIs to support open-source hardware, hobbyists, and commercial appliance builders alike.
   - Maintain clear board schematics, pinout tables (`docs/pinout.md`), and errata guides (`ERRATA.md`).
2. **Strict Attribution & Licensing:**
   - Always credit original authors, upstream algorithms, font designers, and driver creators.
   - Maintain appropriate SPDX license tags (`SPDX-License-Identifier: MIT` or `CC-BY-4.0`) across all code and documentation files.
