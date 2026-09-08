# MWEB Vault Coding Standards

This document defines the code-quality, security, testing, and repair standard for MWEB Vault.

It is intentionally written so that a human developer or an automated coding assistant can use it as an operational checklist when reviewing or repairing the repository.

> **Repair instruction:** When instructed to "repair the repository according to `CODING_STANDARDS.md`", inspect the affected code, classify each problem, make the smallest safe correction, add or update appropriate tests, run the applicable validation, and do not weaken production security or compatibility rules simply to make a test pass.

No document can guarantee that every defect is found. Passing this standard means that known issues in the reviewed scope have been handled systematically and that the applicable automated checks pass.

## 1. Priorities

When requirements conflict, use this order:

1. **Protect wallet funds, keys, and user privacy.**
2. **Preserve consensus, protocol, serialization, and backward compatibility.**
3. **Correct functional behavior.**
4. **Keep tests accurate and meaningful.**
5. **Keep code understandable and maintainable.**
6. **Apply style and formatting.**

A cleaner-looking diff is never more important than preserving correct wallet behavior.

## 2. Supported language baseline

The current Python package declares Python **3.10 or later**. New Python code must remain compatible with the minimum supported version unless the project intentionally raises that requirement in a dedicated change.

Repository text files should continue to follow `.editorconfig`: UTF-8, LF line endings, spaces instead of tabs, trailing whitespace removed, and four-space indentation for Python and shell files.

## 3. Python style and automated tooling

### Required style

Python code should follow **PEP 8** except where existing project-specific conventions deliberately differ.

Use:

- clear `snake_case` function and variable names,
- `PascalCase` class names,
- constants in `UPPER_CASE`,
- four-space indentation,
- explicit, readable control flow,
- imports grouped and kept free of unused entries,
- descriptive names instead of unnecessary abbreviations.

Avoid style-only rewrites mixed into security or behavioral fixes. Formatting an entire legacy file while changing one security-sensitive line makes review harder.

### Preferred lint/format tool: Ruff

Ruff is the preferred Python linter and formatter for new and modified code.

Reference: <https://docs.astral.sh/ruff/>

Adoption should be incremental:

1. New and materially modified Python code should satisfy Ruff.
2. Existing untouched legacy code does not need to be reformatted merely because a nearby bug is being fixed.
3. Repository-wide formatting or lint cleanup should be done in dedicated commits or pull requests.
4. Once the legacy baseline is clean enough, CI may enforce Ruff repository-wide.

This avoids burying wallet changes under thousands of cosmetic lines.

## 4. Type safety

Use Python type annotations for new public functions, security-sensitive logic, transaction/wallet APIs, MWEB interfaces, and substantially modified code.

The preferred static type checker is **mypy**.

Reference: <https://mypy.readthedocs.io/>

Typing must be introduced gradually rather than forcing a full legacy-code rewrite at once.

Rules:

- Prefer precise types over `Any`.
- Use `Optional[T]` or `T | None` only when `None` is actually valid.
- Do not make a required security dependency optional merely to silence a type or test failure.
- Avoid unsafe casts unless the invariant is clear and documented.
- New typed code should not introduce new mypy errors in the checked scope.
- Prioritize typing code that moves money, signs transactions, handles keys, selects coins, constructs addresses, parses network data, or crosses the MWEB boundary.

## 5. Wallet and money rules

Money-handling code receives extra scrutiny.

- Represent Litecoin values internally with integer atomic units where practical. Do not use binary floating point for transaction amounts, fees, balances, or consensus-relevant arithmetic.
- Validate amount ranges and signs at trust boundaries.
- Fee calculations must be deterministic and covered by tests.
- Coin-selection and change logic must preserve required wallet context such as the keystore.
- RBF/fee-bump paths must be tested separately from initial transaction creation.
- Never weaken dust, reserve, fee, or other wallet policy solely to accommodate an outdated test fixture.
- Any code path capable of spending funds should fail closed when required signing or wallet context is missing.

## 6. Cryptography and key material

Cryptographic code is security-sensitive by default.

### Do not

- invent custom cryptographic primitives,
- silently change message magic, signature domains, derivation rules, checksums, key versions, or network prefixes,
- log seeds, seed words, private keys, xprv values, decrypted key material, passwords, authentication tokens, payment preimages, or equivalent secrets,
- convert a cryptographic vector by blindly replacing human-readable prefixes,
- replace a historical encrypted compatibility fixture simply because its contents look outdated.

### Required for cryptographic changes

- identify the network/protocol rule being implemented,
- preserve byte-level compatibility where required,
- add or update deterministic test vectors,
- verify both success and rejection cases,
- keep conversions between bytes, hex, integers, and strings explicit,
- document non-obvious domain separation or serialization assumptions.

Sensitive values should be retained in memory no longer than necessary. Python cannot guarantee secure memory erasure, so code and comments must not claim that ordinary object deletion cryptographically wipes secrets.

## 7. Litecoin, Bitcoin, and inherited Electrum behavior

MWEB Vault contains inherited Electrum and Bitcoin-oriented names and test material. Treat these deliberately.

### Never assume

- a file named `bitcoin.py` is wrong merely because this is a Litecoin wallet,
- `bc1` can always be replaced with `ltc1`,
- Bitcoin xpub/xprv version bytes apply to Litecoin,
- Bitcoin signed-message vectors remain valid on Litecoin,
- Bitcoin Taproot, descriptor, BOLT11, block-header, Lightning, or network fixtures are valid without regeneration or verification.

### Before changing an inherited vector

Classify it as one of:

1. network-independent and valid unchanged,
2. network-specific and requiring a correctly regenerated Litecoin value,
3. a historical compatibility vector that must remain unchanged,
4. evidence of an actual production-code defect.

Do not modify production code to imitate a stale Bitcoin fixture.

## 8. MWEB-specific standards

MWEB logic is treated as security-sensitive wallet code.

- Required keystore or wallet context must remain required when MWEB operation depends on it.
- MWEB address, output, proof, and transaction handling must validate lengths and encodings using the actual Litecoin/MWEB rules.
- Do not cache event-loop-bound asynchronous resources across incompatible event loops.
- gRPC/channel/socket lifecycle must be explicit enough that tests and application shutdown do not inherit stale resources.
- Tests involving `mwebd` must use isolated temporary state and must not depend on a stale socket left by another test run.
- MWEB failures must not silently downgrade a private transaction into a different transaction type unless that behavior is an intentional, documented user-facing feature.

## 9. Network and serialization code

All untrusted network data must be treated as hostile input.

- Check lengths before indexing or allocating based on received values.
- Validate enums, versions, prefixes, counts, and ranges.
- Bound resource consumption where attacker-controlled input could cause excessive CPU, memory, disk, or recursion.
- Avoid ambiguous parsing.
- Reject malformed input explicitly rather than partially accepting it.
- Preserve canonical serialization when the protocol requires it.
- Network-dependent constants should come from central network/configuration definitions rather than unexplained literals scattered through wallet code.

SPV and proof-verification paths must verify the cryptographic proof needed for the claimed blockchain state before trusting server-provided transaction data.

## 10. Exceptions and failure behavior

- Catch specific exceptions rather than using bare `except:`.
- Do not suppress unexpected failures silently.
- Do not use exceptions as ordinary control flow when a simple explicit condition is clearer.
- Preserve useful causal context when translating exceptions.
- User-facing errors should explain what failed without exposing secrets.
- Security validation should fail closed.
- Cleanup code should run reliably even when an operation fails.

## 11. Logging and privacy

Logs are potentially persistent data.

Never log:

- seeds or mnemonics,
- private keys or xprvs,
- passwords,
- decrypted wallet secrets,
- authentication credentials,
- full sensitive RPC payloads,
- unnecessary personally identifying or wallet-linking information.

Debug logging must not quietly become a privacy leak. If sensitive identifiers are necessary for diagnostics, minimize, redact, or hash them where that still allows the issue to be diagnosed.

## 12. Async and concurrency

- Clearly define which event loop owns asynchronous resources.
- Do not share loop-bound objects across loops unless the library explicitly supports it.
- Avoid hidden mutable global state.
- Protect shared mutable state with the appropriate synchronization strategy.
- Cancellation must leave wallet and network state consistent.
- Background work must have an explicit lifecycle and shutdown path.
- Tests must clean up tasks, sockets, channels, temporary processes, and files they create.

## 13. Tests

The test suite is part of the product, not an obstacle to it.

### Bug fixes

Every production bug fix should normally include a regression test that:

1. fails before the fix,
2. passes after the fix,
3. exercises the real failing path rather than an unrelated mock,
4. protects against recurrence.

If a regression test is genuinely impractical, the PR must explain why.

### Test quality

Tests should be:

- deterministic,
- isolated,
- repeatable,
- independent of execution order,
- independent of stale temporary files or sockets,
- free of unnecessary live-network dependencies,
- explicit about Litecoin/MWEB network assumptions.

Use temporary directories/resources for filesystem and daemon tests.

Never lower production validation just to make a fixture pass.

### Failing inherited tests

For each failure, classify it before editing:

- **PRODUCTION BUG** - fix product code and add regression coverage.
- **LITECOIN FIXTURE** - regenerate or correct the test using Litecoin rules.
- **HISTORICAL COMPATIBILITY** - preserve the stored vector and fix the surrounding expectation/setup if needed.
- **CI/ENVIRONMENT** - repair the build/test environment without changing wallet behavior.

## 14. Go code (`contrib/mwebd`)

Go changes should:

- be formatted with `gofmt`,
- pass `go test ./...` for the applicable module,
- pass `go vet ./...` where supported,
- handle returned errors explicitly,
- avoid unnecessary global mutable state,
- bound untrusted inputs and resource use,
- preserve clean shutdown and socket/process lifecycle behavior.

A Go build succeeding is not a substitute for tests.

## 15. Shell, CI, and build scripts

- Shell scripts should use clear failure handling appropriate to the script and should not silently ignore failed security/build commands.
- Quote shell variables unless intentional word splitting is required.
- Pin or deliberately constrain important build dependencies/actions where reproducibility and supply-chain safety require it.
- CI changes must not hide failing tests with broad exclusions, unconditional `|| true`, or similar bypasses.
- Temporary diagnostic flags such as pytest `--maxfail` may limit output while porting tests, but they must not convert failures into success.
- Build output should be reproducible enough that a release can be traced back to its source commit and version tag.

## 16. Dependencies

- Add a dependency only when its value clearly outweighs the new maintenance and supply-chain surface.
- Prefer established, maintained libraries for cryptographic and protocol primitives.
- Pin or constrain dependencies consistently with the repository's release process.
- Review dependency updates for security and compatibility, not merely version freshness.
- Automated dependency/security scanning should be part of CI as the project matures.

## 17. Documentation and comments

Comments should explain **why**, invariants, security assumptions, protocol quirks, or compatibility constraints. Do not narrate obvious syntax.

Document:

- security-sensitive invariants,
- non-obvious Litecoin-vs-Bitcoin behavior,
- MWEB assumptions,
- backward-compatibility constraints,
- unusual lifecycle/concurrency requirements,
- public APIs that are not self-explanatory.

If behavior changes for users or release operators, update the appropriate user/developer documentation and release notes.

## 18. Commit and pull-request standards

Keep commits small and reviewable.

A good commit should usually represent one logical change, for example:

```text
fix(wallet): pass keystore during fee bump

test(wallet): cover RBF coinchooser path

fix(tests): scale Litecoin Lightning channel fixture

docs: document release branch policy
```

Do not combine unrelated formatting, fixture ports, wallet fixes, dependency upgrades, and refactors in one commit.

PRs should explain:

- the problem,
- whether it is a production bug, fixture issue, compatibility issue, or CI issue,
- the security impact if applicable,
- how the fix was tested,
- any known limitations or follow-up work.

### AI-assisted pull requests

When an AI system materially creates or modifies code, tests, documentation, build configuration, or other repository content submitted through a pull request, the AI system should identify itself in the pull request description.

The disclosure should identify the AI tool or provider clearly, for example:

- `AI contributor: ChatGPT — OpenAI`
- `AI contributor: Claude — Anthropic`
- `AI contributor: Grok — SpaceXAI`
- `AI contributor: Gemini — Google`
- `AI contributor: GitHub Copilot — GitHub`

If multiple AI systems materially contributed to the same pull request, list each one.

AI identification is required at the **pull-request level**, not for every individual commit. Once an AI system has been identified in an existing pull request, additional commits made by that same AI while continuing work on that pull request do not require separate attribution.

If a different AI system later materially contributes to the same pull request, the pull-request description should be updated to identify that additional system.

AI attribution does not replace human review, testing, licensing review, or responsibility for the submitted change. AI-assisted code must satisfy the same coding, security, compatibility, and testing standards as any other contribution.

## 19. Definition of done

Code is not considered complete until all applicable items below are true:

- [ ] The root cause was identified rather than merely masked.
- [ ] The change is the smallest safe change that solves the problem.
- [ ] Existing security checks were preserved or intentionally strengthened.
- [ ] Litecoin/MWEB behavior was distinguished from inherited Bitcoin assumptions.
- [ ] Required wallet/keystore/signing context remains required.
- [ ] No secret or privacy-sensitive data was added to logs.
- [ ] Amount/fee arithmetic avoids unsafe floating-point behavior.
- [ ] Untrusted input is validated and resource use is reasonably bounded.
- [ ] New or modified Python code follows the project style and applicable Ruff rules.
- [ ] New/security-sensitive Python interfaces have useful type annotations.
- [ ] Go code is formatted and applicable Go checks pass.
- [ ] A production bug fix has regression coverage where practical.
- [ ] Tests are deterministic and isolated.
- [ ] Historical compatibility vectors were not rewritten without a valid compatibility reason.
- [ ] Python compilation/import checks pass.
- [ ] Applicable focused tests pass.
- [ ] The full pytest suite passes before promotion to a release-quality branch, except for failures explicitly documented as pre-existing during an active migration period.
- [ ] CI/build changes do not suppress real failures.
- [ ] Documentation/release notes were updated when behavior changed.
- [ ] Any AI system that materially contributed to the pull request is identified in the pull-request description.
- [ ] The diff contains no unrelated cleanup that obscures review.

## 20. Repository repair procedure

When asked to review or repair code under this standard, use the following sequence:

### Step 1 - Establish a baseline

Record the current commit/branch and run or inspect the existing build, compile, and test checks before making broad changes.

### Step 2 - Inventory failures

Group failures by subsystem and root cause instead of treating every red assertion as a separate bug.

### Step 3 - Classify each issue

Use one of these labels:

- `SECURITY`
- `PRODUCTION BUG`
- `LITECOIN PORT`
- `MWEB`
- `COMPATIBILITY`
- `TEST FIXTURE`
- `CI/BUILD`
- `STYLE/TYPE`
- `DOCUMENTATION`

### Step 4 - Prioritize

Repair in this order:

1. fund/key/security vulnerabilities,
2. consensus/proof/serialization defects,
3. transaction/signing/fee/wallet defects,
4. MWEB lifecycle and privacy defects,
5. network/parser/resource-exhaustion defects,
6. incorrect Litecoin test fixtures,
7. CI/build reliability,
8. type/style/documentation debt.

### Step 5 - Fix narrowly

Prefer a targeted change over an architectural rewrite. Preserve existing public behavior unless the behavior itself is the bug.

### Step 6 - Add regression evidence

Create the smallest test that demonstrates the fixed failure and important rejection paths.

### Step 7 - Validate locally/CI

Run the narrow test first, then the affected module/subsystem, then the full applicable suite.

### Step 8 - Review the diff as an attacker

Ask:

- Can this bypass validation?
- Can malformed input crash or exhaust resources?
- Can a missing keystore/signing object now slip through?
- Can an async resource escape its lifecycle?
- Can this leak wallet metadata or secrets?
- Did a test get weakened rather than repaired?
- Did a Bitcoin constant get substituted without regeneration?

### Step 9 - Keep commits granular

Separate production fixes, regression tests, fixture ports, and unrelated cleanup whenever practical.

### Step 10 - Promote only when appropriate

Normal branch flow is:

```text
feature/fix -> dev -> main -> release -> immutable version tag
```

Do not promote code toward `release` until the applicable release gates are green and the known failures are understood.

## 21. Recommended enforcement roadmap

To avoid a disruptive legacy rewrite, adopt enforcement in stages.

### Stage A - immediately

- Existing pytest/compile checks.
- Regression tests for production fixes.
- Ruff on new or materially changed Python code.
- `gofmt` and Go tests for changed Go code.
- Manual use of this checklist during PR review.

### Stage B - after the inherited Litecoin test port is green

- Repository-wide Ruff lint check.
- Ruff formatting check.
- Gradual mypy checks beginning with wallet, transaction, coin selection, network parsing, and MWEB boundaries.
- Dependency/security scanning in CI.

### Stage C - release hardening

- Required CI status checks for promotion.
- Broader static typing coverage.
- Dedicated security/static-analysis job.
- Reproducible release verification tied to immutable version tags.

The goal is a steadily tightening ratchet: new code should not add debt, and existing debt should be removed without obscuring security-relevant behavior changes.