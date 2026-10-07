# Google Jules: CLI & Autonomous Agent Cheat Sheet

## 1. Core Architecture & Operating Model

### Cloud-Hosted vs. Local Unpushed Code

* **Strictly Cloud-Hosted:** Jules **cannot** inspect or modify your uncommitted, unpushed local working tree.
* **Execution Flow:** Jules provisions an ephemeral cloud virtual machine in Google Cloud, clones the target branch directly from your linked GitHub repository, executes bash commands/tests in that sandbox, and submits its solution as a **GitHub Pull Request**.
* **Requirement:** Any code or architectural change you want Jules to analyze must be pushed to a branch on GitHub first.

### Jules vs. Google Antigravity: Can You Use Them Together?

| Dimension | Google Labs Jules | Google Antigravity (`agy` / IDE) |
| :--- | :--- | :--- |
| **Location** | Cloud-based ephemeral VM | Runs locally on your machine / IDE |
| **State Target** | Remote GitHub branch | Unpushed, dirty local working tree |
| **Interaction** | **Asynchronous / Fire-and-forget** (opens a PR) | **Synchronous / Interactive** (in-editor diffs, MCP tools) |
| **Human Role** | PR Reviewer | Real-time collaborator / supervisor |

**Is using Jules inside Antigravity a good idea?**
No, it is an architectural mismatch:
* Antigravity is built around a local agent engine that directly reads your open files, editor context, and local terminal.
* Jules is built to remove work from your local machine entirely so you can shut your laptop.
* **The Recommended Division of Labor:**
  * Use **Antigravity** for interactive development, debugging local uncommitted spikes, and rapid inner-loop coding.
  * Use **Jules** for delegating tasks asynchronously (e.g., test expansion, documentation sweeps, dependency upgrades) via GitHub PRs while you focus on other work.

---

## 2. Jules Tools CLI: Setup & Installation

Jules provides a CLI utility via npm (`@google/jules`) that lets you dispatch sessions and check task status directly from your shell without opening the web UI.

### Installation

```bash
# Option A: Global installation
npm install -g @google/jules

# Option B: Run on-demand with npx (no install required)
npx @google/jules
```

### Initial Authentication & Verification

```bash
# 1. Authenticate (triggers browser OAuth with your Google/GitHub account)
jules login

# 2. Verify connected repositories
jules remote list --repo

# 3. Launch the interactive Terminal User Interface (TUI)
jules
```

---

## 3. CLI Command Reference

### Interactive Mode (TUI)

Running `jules` without arguments opens the full-screen terminal dashboard:
* Navigate active tasks with arrow keys.
* Inspect multi-step plans and shell logs.
* Approve plans or reject branches directly from the terminal.

### Headless & Scriptable Commands

```bash
# List all active or recent sessions
jules session list

# View details and status of a specific session
jules session get <session-id>

# Dispatch a new task to a specific repo and branch
jules remote new \
  --repo "owner/repo-name" \
  --branch "main" \
  --session "Your prompt goes here"

# Cancel a running background session
jules session cancel <session-id>
```

### Piping Unix Tools and GitHub CLI (`gh`) into Jules

```bash
# Create a Jules task directly from an existing GitHub issue
gh issue view 104 --json title,body --jq '"Fix issue: " + .title + "\n\n" + .body' \
  | jules remote new --repo "owner/repo-name"

# Dispatch bulk documentation tasks across multiple repositories
for repo in repo-a repo-b repo-c; do
  jules remote new --repo "my-org/$repo" --session "Add markdown API docs for src/index.ts"
done
```

---

## 4. Prompting Best Practices for Autonomous Agents

Because Jules operates asynchronously in an isolated sandbox, prompt design differs from conversational chat:

1. **Provide Clear Verification Commands:** Always specify the exact bash test or linter command (e.g., `npm run lint`, `pytest tests/`, `doxygen Doxyfile`). Jules will run these in its VM to check its own work.
2. **Define Boundaries & Non-Goals:** Explicitly state what **not** to touch (e.g., *"Do not modify the database migration files"*, *"Do not change public method signatures"*).
3. **Keep Tasks Atomic:** Jules works best on single-concern pull requests (e.g., "Add docs to Module X" or "Fix bug in calculation Y") rather than open-ended requests like "Refactor the entire backend."

---

## 5. Recipe Catalog: 25 Production Prompts for Jules

Each recipe below follows an autonomous-ready template: **Target**, **Objective**, **Specific Rules**, **Constraints**, and **Verification**. Copy and paste them into `jules remote new --session "..."` or run them in `jules.google.com`.

### Category A: Testing & Quality Assurance

#### Recipe 1: Increasing Unit Test Branch Coverage (TypeScript/Jest/Vitest)
```text
Target: src/services/auth.service.ts
Test File: tests/services/auth.service.test.ts

Objective:
Increase unit test branch coverage for auth.service.ts to at least 90%.

Instructions:
1. Analyze auth.service.ts for all branch conditionals (if/else, switch, ternary, try/catch).
2. Inspect existing test cases to see what is missing.
3. Add new unit test suites covering edge cases: expired tokens, malformed JWT headers, missing database records, and network timeouts.
4. Mock all external database and network calls using standard project mocking conventions.

Constraints:
- DO NOT modify src/services/auth.service.ts. Only touch the test file.
- Do not introduce external npm dependencies.

Verification:
Run `npm test -- tests/services/auth.service.test.ts --coverage` and verify coverage meets or exceeds 90% branches and all tests pass.
```

#### Recipe 2: Python Edge-Case & Error-Handling Tests (pytest)
```text
Target: app/services/billing.py
Test File: tests/test_billing.py

Objective:
Add exhaustive failure mode and edge-case unit tests for billing calculations.

Instructions:
1. Identify all calculation logic, discount tiers, and currency conversion routines.
2. Add pytest parameterized tests for: zero amounts, negative inputs, fractional cents rounding, unsupported ISO currency codes, and unexpected None values.
3. Test custom exception raising (e.g., InsufficientFundsError, InvalidCurrencyError).

Constraints:
- Do not alter business logic in app/services/billing.py.
- Use pytest.raises to assert custom exceptions.

Verification:
Run `pytest tests/test_billing.py -v` and ensure 100% test pass rate with zero warnings.
```

#### Recipe 3: HTTP API Contract / Snapshot Tests (Supertest / Fastify)
```text
Target: src/routes/v1/users.ts
Test File: tests/routes/users.contract.test.ts

Objective:
Implement end-to-end route contract validation tests for all `/api/v1/users` endpoints.

Instructions:
1. Review all GET, POST, PUT, DELETE route definitions in src/routes/v1/users.ts.
2. Write integration tests using supertest that assert:
   - Correct HTTP response status codes (200, 201, 400, 401, 404, 422).
   - Response headers include `Content-Type: application/json` and security headers.
   - Response JSON schema conforms strictly to the expected type definitions in src/types/user.ts.

Constraints:
- Use in-memory SQLite / mock DB fixtures; do not require a live external database.
- Do not alter the route logic.

Verification:
Run `npm run test:integration` and confirm all suites pass.
```

#### Recipe 4: Network & Third-Party Service Mocking (MSW / Nock)
```text
Target: tests/integrations/stripe_webhook.test.ts

Objective:
Eliminate flakiness by replacing unmocked external Stripe API calls with MSW (Mock Service Worker) handlers.

Instructions:
1. Inspect the test suite for direct network calls or brittle manual mocks.
2. Set up clean MSW request handlers intercepting `https://api.stripe.com/v1/*`.
3. Provide realistic mock JSON responses for customer creation, invoice payment success, and charge failure.
4. Ensure MSW resets handlers after each test (`server.resetHandlers()`).

Constraints:
- Do not change test assertions; only replace the transport-level network mocks.

Verification:
Run `npm test -- stripe_webhook.test.ts` with network access disabled (or verify no external network calls occur).
```

---

### Category B: Documentation & Schemas

#### Recipe 5: Doxygen C/C++ Header Docstrings
```text
Target: include/core/engine.h and include/core/memory.h

Objective:
Add standardized, complete Doxygen docblocks to all exposed structs, enums, unions, and function signatures.

Instructions:
1. Use standard Javadoc/Doxygen block formatting (`/** ... */`).
2. For every function, document:
   - `@brief`: Single concise sentence.
   - `@details`: Memory ownership rules, blocking vs non-blocking behavior, thread-safety guarantees.
   - `@param[in]`, `@param[out]`, `@param[in,out]`: Detailed descriptions for each parameter.
   - `@return`: Expected return value and specific error return codes.
3. For every struct and enum field, supply an inline docstring (`///<`).

Constraints:
- DO NOT alter variable names, types, or function prototypes.
- Retain exact existing indentation and line formatting.

Verification:
Run `doxygen Doxyfile` and confirm zero parser warnings or undocumented parameter diagnostics.
```

#### Recipe 6: OpenAPI / Swagger Spec Generation from Route Handlers
```text
Target: docs/openapi.yaml
Source Routes: src/controllers/*.ts

Objective:
Synchronize `docs/openapi.yaml` with the current Express/Fastify route controllers.

Instructions:
1. Audit all controller files in `src/controllers/`.
2. Update `docs/openapi.yaml` with missing paths, query parameters, request bodies, and responses.
3. Ensure every endpoint specifies 200/201 responses, 400 validation error responses, and 401/403 authorization error structures.
4. Define reusable schemas under `components/schemas` rather than inlining repeated object shapes.

Constraints:
- Do not modify TypeScript controller files.

Verification:
Run `npx @stoplight/spectral-cli lint docs/openapi.yaml` and verify zero schema errors.
```

#### Recipe 7: TSDoc / JSDoc Generation for TypeScript Utilities
```text
Target: src/utils/string.ts and src/utils/math.ts

Objective:
Add comprehensive TSDoc comments across all exported functions, types, and interfaces.

Instructions:
1. Add `@remarks` providing code examples using `@example` blocks for non-trivial utilities.
2. Annotate generic type parameters with `@typeParam`.
3. Document parameters with `@param` and return values with `@returns`.
4. Mark deprecated utility functions with `@deprecated` including replacement guidance.

Constraints:
- Do not alter function implementation code.

Verification:
Run `npx eslint --rule 'tsdoc/syntax: error' src/utils/` to ensure TSDoc compliance.
```

#### Recipe 8: Architecture Decision Record (ADR) Creation
```text
Target: docs/adr/

Objective:
Generate an Architecture Decision Record (ADR) documenting the migration from REST to gRPC for inter-service communication.

Instructions:
1. Check existing ADR numbers in `docs/adr/` and assign the next sequential number (e.g., `0008-migrate-internal-services-to-grpc.md`).
2. Follow the standard Michael Nygard format: Title, Status (Accepted), Context, Decision, Consequences (Positive, Negative, Neutral).
3. Reference real internal repository packages (e.g., `services/gateway`, `services/user`).
4. Update `docs/adr/README.md` index table with the new record.

Constraints:
- Only create/edit files under `docs/adr/`.

Verification:
Run `npx markdownlint docs/adr/*.md` to ensure markdown syntax adheres to repo rules.
```

#### Recipe 9: Automated Changelog Generation from Conventional Commits
```text
Target: CHANGELOG.md

Objective:
Update CHANGELOG.md with all commit history since the last git tag following the Keep a Changelog standard.

Instructions:
1. Inspect `git log` since the latest release tag.
2. Group commits by Conventional Commit types: Added (`feat:`), Fixed (`fix:`), Changed (`refactor:`, `perf:`), and Security.
3. Exclude internal chore/build/ci commits unless they introduce breaking changes.
4. Highlight any BREAKING CHANGE with clear migration notes.

Constraints:
- Preserve all existing changelog history below the new release section.

Verification:
Run `git diff CHANGELOG.md` and check that the Markdown structure parses correctly.
```

---

### Category C: Refactoring & Modernization

#### Recipe 10: Deprecated HTTP Client Migration (Axios to native `fetch`)
```text
Target: src/clients/api-client.ts

Objective:
Migrate from `axios` to Node.js native `fetch` (or browser native `fetch`) to eliminate an external runtime dependency.

Instructions:
1. Replace Axios request configuration objects with native RequestInit objects.
2. Replace Axios interceptors with a lightweight wrapper function that handles header injection and standard error unwrapping.
3. Transform `response.data` patterns to `await response.json()`.
4. Ensure HTTP error statuses (4xx, 5xx) throw custom APIError classes with status codes and parsed JSON bodies.
5. Remove `axios` from `package.json` if it is no longer used elsewhere.

Constraints:
- Keep the public signature and return types of `ApiClient` identical so callers do not break.

Verification:
Run `npm run build && npm test` to ensure zero compilation or runtime regression errors.
```

#### Recipe 11: Pruning Dead Code and Unused Exports
```text
Target: Entire repository (`src/`)

Objective:
Identify and remove dead code, unreferenced helper functions, and unused exports.

Instructions:
1. Run `npx knip` or `npx ts-prune` to locate unreferenced source files and unused exports.
2. Verify that flagged exports are not consumed dynamically or across package boundaries.
3. Remove unused internal functions and clean up obsolete import statements.

Constraints:
- DO NOT touch files in `src/public-api/` or entries defined in `package.json` "exports".
- Do not delete methods that satisfy exported interfaces or abstract base classes.

Verification:
Run `npm run build && npm test` and re-run `npx knip` to confirm unused count decreases with zero build failures.
```

#### Recipe 12: Promise Chaining to `async`/`await` Modernization
```text
Target: src/legacy/data-loader.js

Objective:
Modernize legacy `.then().catch().finally()` Promise chains into clean `async`/`await` syntax.

Instructions:
1. Refactor sequential Promise chains to use linear `await` assignments.
2. Wrap operations in standard `try / catch / finally` blocks with equivalent error handling semantics.
3. Replace `Promise.all([ ... ])` callbacks with destructuring assignments: `const [a, b] = await Promise.all([ ... ])`.

Constraints:
- Preserve exact error re-throwing and rejection behavior.
- Do not change exported function signatures or return types.

Verification:
Run `npm test -- tests/legacy/data-loader.test.js` to ensure behavioral parity.
```

#### Recipe 13: Standardizing Application Error Hierarchy
```text
Target: src/errors/ and src/middleware/error-handler.ts

Objective:
Replace ad-hoc string/object errors with an explicit, extensible `AppError` class hierarchy.

Instructions:
1. Create a base `AppError extends Error` class with `statusCode`, `errorCode`, `isOperational`, and `details` payload.
2. Implement standard subclasses: `NotFoundError` (404), `UnauthorizedError` (401), `ForbiddenError` (403), `ValidationError` (422), `ConflictError` (409).
3. Update `src/middleware/error-handler.ts` to inspect instances of `AppError`, log operational metadata, and return clean JSON responses.

Constraints:
- Ensure `Error.captureStackTrace` is called properly in base class constructors.
- Maintain backward compatibility for any existing error codes used by API consumers.

Verification:
Run `npm test -- tests/middleware/error-handler.test.ts` and ensure all error status mappings pass.
```

---

### Category D: Type Safety & Schema Integrity

#### Recipe 14: TypeScript `any` Elimination & Strict Mode Pass
```text
Target: src/models/ and src/transforms/

Objective:
Eliminate all explicit and implicit `any` types in favor of strict, well-defined TypeScript types.

Instructions:
1. Replace `any` with precise interfaces, union types, or `unknown` with runtime type narrowing.
2. Add type guards (`isRecord`, `isString`, etc.) where parsing unvalidated external input.
3. Replace index signatures (`[key: string]: any`) with `Record<string, unknown>`.

Constraints:
- Do not use `@ts-ignore` or `@ts-expect-error` to suppress diagnostics.
- Do not change runtime output logic.

Verification:
Run `npx tsc --noEmit --strict` and verify zero compiler errors.
```

#### Recipe 15: Python Type Annotations & `mypy` Verification
```text
Target: backend/app/crud/

Objective:
Add full type hints to all CRUD repository functions and achieve strict `mypy` compliance.

Instructions:
1. Add explicit argument and return type hints to all functions in `backend/app/crud/`.
2. Use standard `typing` types (e.g., `Optional`, `Sequence`, `Mapping`, `Union`) or Python 3.10+ union syntax (`|`).
3. Correctly type SQLAlchemy session parameters and generic model return types.

Constraints:
- Do not alter the SQL queries or business logic.
- Avoid using `type: ignore` comments unless working around third-party library stub bugs (document reason if used).

Verification:
Run `mypy backend/app/crud/ --strict` and ensure clean passage with zero errors.
```

#### Recipe 16: Zod Schema Generation from Interfaces
```text
Target: src/schemas/user.schema.ts
Source Types: src/types/user.ts

Objective:
Create runtime Zod validation schemas matching the TypeScript interfaces in `src/types/user.ts`.

Instructions:
1. Inspect user interfaces (`CreateUserInput`, `UpdateUserInput`, `UserResponse`).
2. Construct corresponding Zod schemas using `z.object()`, `z.string().email()`, `z.number().int().positive()`, etc.
3. Export inferred TypeScript types using `z.infer<typeof Schema>` and verify they match existing interfaces.
4. Add input sanitization transforms where appropriate (e.g., `.trim()`, `.toLowerCase()` on emails).

Constraints:
- Ensure required vs optional fields strictly match the TypeScript interface definitions.

Verification:
Run `npm test -- tests/schemas/user.schema.test.ts` to validate parsing and rejection behavior.
```

#### Recipe 17: Rust / Go Linter & Idiom Remediation
```text
Target: Entire repository

Objective:
Resolve all warnings generated by standard linter suites (`cargo clippy` or `golangci-lint`).

Instructions:
1. Run the project linter to gather all existing warnings.
2. Refactor non-idiomatic constructs (e.g., replace unneeded clones, simplify pattern matching, handle unchecked error returns).
3. Do not silence warnings with global suppression attributes unless approved by project conventions.

Constraints:
- No functional regressions or breaking API changes.

Verification:
For Rust: Run `cargo clippy --all-targets -- -D warnings && cargo test`.
For Go: Run `golangci-lint run ./... && go test ./...`.
```

---

### Category E: Security & Hardening

#### Recipe 18: Automated Dependency Vulnerability Remediation
```text
Target: package.json and package-lock.json (or requirements.txt / poetry.lock)

Objective:
Resolve high and critical security vulnerabilities reported by dependency security audits.

Instructions:
1. Run `npm audit` (or `pip-audit`) to identify vulnerable packages and their dependency paths.
2. Upgrade minimum required package versions in the lockfile to patched releases.
3. If a direct dependency upgrade introduces breaking API changes, adapt our call sites in `src/` to remain compatible.

Constraints:
- Do not run blind major version upgrades across non-vulnerable packages.
- Keep lockfile diffs minimal.

Verification:
Run `npm audit --audit-level=high` (verify zero high/critical issues) AND run `npm test` to ensure full test suite passes.
```

#### Recipe 19: SQL Injection Audit & Query Parameterization
```text
Target: src/db/repositories/

Objective:
Audit all database access files and eliminate manual string interpolation in SQL queries.

Instructions:
1. Scan all repository files for template literals or string concatenation inside database execution calls (e.g., `db.query(\`SELECT ... \${id}\`)`).
2. Replace all raw interpolations with parameterized queries (e.g., `$1, $2` or `?`) passed through the database driver query parameters.
3. Validate dynamic `ORDER BY` and `SORT` clauses against a strict whitelist of allowed column identifiers.

Constraints:
- Do not alter the database schema or data models.

Verification:
Run `npm test -- tests/db/` and execute static analysis security scans (`npx @microsoft/eslint-formatter-sarif` or project security linter).
```

#### Recipe 20: Environment Variable Schema & Startup Validation
```text
Target: src/config/env.ts

Objective:
Implement runtime environment variable validation on server startup using envalid or Zod.

Instructions:
1. Audit `.env.example` and code usage of `process.env.*`.
2. Define a strict schema validating:
   - `PORT`: Valid port number, defaults to 3000.
   - `DATABASE_URL`: Valid URL format, required.
   - `NODE_ENV`: Enum of `development | test | production`.
   - `API_KEY`: Minimum length string, required in production.
3. Export a typed, frozen `env` object and fail immediately with a readable error list if startup configuration is invalid.

Constraints:
- Do not commit secrets or modified `.env` files to git.

Verification:
Run `npm test -- tests/config/env.test.ts` validating both successful startup and intentional exit on missing variables.
```

#### Recipe 21: Express / Fastify Security Middleware & Rate Limiting
```text
Target: src/server.ts and src/middleware/security.ts

Objective:
Harden API server headers and configure global + route-specific rate limiting.

Instructions:
1. Add/configure `helmet` with appropriate Content Security Policy (CSP), HSTS, and frameguard settings.
2. Configure CORS middleware with strict origin reflection from environment variables (no wildcard `*` allowed in production mode).
3. Set up an IP-based rate limiter on auth routes (`/api/v1/auth/*`) allowing a maximum of 10 requests per minute.

Constraints:
- Ensure health check endpoints (`/health`, `/metrics`) are excluded from rate limiting.

Verification:
Run `npm test -- tests/security/middleware.test.ts` and verify headers on test requests.
```

---

### Category F: DevOps, Build & Tooling

#### Recipe 22: Multi-Stage Dockerfile Optimization & Image Slimming
```text
Target: Dockerfile and .dockerignore

Objective:
Refactor Dockerfile to use multi-stage builds, minimize image footprint, and run as a non-root user.

Instructions:
1. Split the build into stages: `deps` (cache dependencies), `builder` (compile assets/TypeScript), and `runner` (minimal runtime image using alpine or distroless).
2. Copy only production node_modules/wheels and built artifacts into the final runtime stage.
3. Create a dedicated non-root user and group (`appuser:appgroup`) and switch to `USER appuser`.
4. Ensure `.dockerignore` excludes `.git`, `node_modules`, test files, and local documentation.

Constraints:
- Keep exposed ports, entrypoint binaries, and environment variable requirements unchanged.

Verification:
Run `docker build -t test-build .` and verify the build finishes successfully with reduced image size.
```

#### Recipe 23: GitHub Actions CI Pipeline Matrix Setup
```text
Target: .github/workflows/ci.yml

Objective:
Establish a robust GitHub Actions CI workflow running linting, typechecking, and matrix testing across supported Node/Python versions.

Instructions:
1. Configure trigger on pull requests targeting `main` and pushes to `main`.
2. Set up jobs with concurrency cancellation so outdated commits do not waste runner minutes:
   - `lint`: Runs linter and code style formatting checks.
   - `typecheck`: Runs compiler checks without emitting code.
   - `test`: Runs test matrix across Node 18, 20, and 22 (or Python 3.10, 3.11, 3.12).
3. Enable dependency caching actions (`actions/setup-node` with `cache: 'npm'`).

Constraints:
- Use SHA-pinned or vetted official GitHub actions (`actions/checkout@v4`, `actions/setup-node@v4`).

Verification:
Run `npx action-validator .github/workflows/ci.yml` or use `rhysd/actionlint` to ensure syntax validity.
```

#### Recipe 24: Pre-Commit Hook & Lint-Staged Configuration
```text
Target: package.json, .husky/, and .lintstagedrc.json

Objective:
Configure automated pre-commit hooks to enforce formatting and linting on staged files before commits are created.

Instructions:
1. Install and initialize `husky` and `lint-staged`.
2. Configure pre-commit hooks that run:
   - Prettier formatting on staged `.json`, `.md`, `.yml`.
   - ESLint / Biome / Ruff with `--fix` on staged `.ts`, `.tsx`, `.py`.
   - Typechecking on modified projects.
3. Ensure the git hook fails gracefully with actionable error output if lint errors cannot be auto-fixed.

Constraints:
- Avoid long-running end-to-end test executions in pre-commit hooks to preserve developer velocity.

Verification:
Test hook script manually by staging a dummy file and executing `.husky/pre-commit`.
```

#### Recipe 25: Database Migration & Schema Sync Script
```text
Target: prisma/schema.prisma (or migrations/ directory)

Objective:
Generate a clean, reversible database migration adding an `audit_logs` table.

Instructions:
1. Add an `AuditLog` model with fields:
   - `id`: UUID primary key.
   - `userId`: Foreign key with cascade/nullify rules.
   - `action`: String enum (`CREATE`, `UPDATE`, `DELETE`, `LOGIN`).
   - `resource`: String identifier.
   - `payload`: JSON/JSONB metadata.
   - `createdAt`: Timestamp with index.
2. Add necessary composite indexes for frequent queries on `(userId, createdAt)`.
3. Generate the SQL migration file using the project's migration CLI tool.

Constraints:
- Do not alter or drop any existing tables or columns.

Verification:
Run `npx prisma migrate dev --create-only` (or equivalent framework command) and verify the generated SQL syntax.
```