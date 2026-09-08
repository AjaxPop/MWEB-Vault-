# MWEB Vault Development Guide

This file documents the long-lived branch model, release flow, and high-level repository structure for MWEB Vault.

## Branch model

MWEB Vault uses three long-lived branches:

### `dev`

`dev` is the active integration branch.

- New features, bug fixes, test ports, and refactors should normally be developed on short-lived topic branches.
- Topic branches should open pull requests into `dev`.
- CI should run before changes are merged.
- `dev` may contain work that is not ready to ship yet.

### `main`

`main` is the validated project branch.

- Changes move from `dev` to `main` after the development batch is tested and considered ready.
- `main` should remain in a substantially healthier state than `dev`.
- Release candidates should come from `main`, not directly from feature branches.

### `release`

`release` is the long-lived shipping branch.

- Only software that is actually being released should be promoted from `main` to `release`.
- The branch is not recreated for every version. It moves forward as new MWEB Vault versions are published.
- Each published version should also receive an immutable Git tag such as `v1.0.0`, `v1.0.1`, or `v1.1.0` so historical releases remain easy to identify even as the `release` branch advances.
- Emergency release fixes should be merged back into `main` and `dev` so the branches do not drift apart.

Normal flow:

```text
feature/fix branch
        |
        v
       dev
        |
        v
       main
        |
        v
     release
        |
        v
   version tag
```

The important rule is that code moves toward release through testing and promotion. Production checks should not be weakened merely to make inherited tests green.

## Project structure

### `electrum/`

The main Python wallet implementation.

Important areas include:

- `wallet.py` - wallet behavior, transaction creation, fee bumping, and wallet-level operations.
- `coinchooser.py` - input/coin selection and transaction funding logic.
- `mwebd.py` - Python-side integration with the MWEB daemon/library.
- `bitcoin.py`, `bip32.py`, `bip21.py`, and related modules - protocol, key, address, and serialization logic inherited from Electrum and adapted for Litecoin where required.
- `gui/` - user interfaces, including Qt, QML, text, and stdio front ends.
- `plugins/` - hardware-wallet and optional service integrations.
- `chains/` - chain-related support data/code.

Some module names still contain historical Bitcoin/Electrum terminology. A filename containing `bitcoin` does not by itself mean that its logic should be replaced or renamed; network-dependent behavior must be evaluated case by case.

### `contrib/`

Build, packaging, release, platform, and helper tooling.

Of particular importance:

- `contrib/mwebd/` - Go module used to build the MWEB daemon/library integration (`go.mod`, `go.sum`, and `main.go`).
- Platform-specific build tooling, including Android and other packaging helpers, also lives under `contrib/`.

### `tests/`

The Python/pytest test suite and test data.

It contains wallet, blockchain, Lightning, descriptor, cryptographic, plugin, QML, regtest, and protocol tests, along with external or inherited test vectors.

Because MWEB Vault descends from Electrum-LTC and ultimately carries inherited Electrum/Bitcoin test material, a failing Bitcoin-oriented fixture is not automatically a production bug. Network-specific fixtures such as addresses, signed-message vectors, extended-key versions, BOLT11 invoices, Taproot data, descriptors, headers, and Lightning assumptions must be ported using Litecoin constants and rules.

Do not perform blanket replacements such as changing every `bc1` string to `ltc1`. Some vectors contain checksums, signatures, version bytes, witness programs, encrypted historical data, or other values that must be regenerated or deliberately preserved.

### `.github/workflows/`

GitHub Actions continuous-integration workflows. Pull-request build and test automation lives here.

CI is expected to validate native dependencies, Python imports/compilation, and the pytest suite before promotion toward a release.

### `fastlane/`

Mobile release metadata and automation used by the project packaging/release process.

### `pubkeys/`

Public-key material used by the inherited project/release tooling. Treat signing and trust-related files as security-sensitive and review changes carefully.

### `run_electrum`

Primary launcher/entry script for running the wallet from the source tree.

### `setup.py`, `setup.cfg`, and `MANIFEST.in`

Python packaging and distribution configuration.

### `README.md`, `SECURITY.md`, `RELEASE-NOTES`, `LICENCE`, and `AUTHORS`

Top-level project documentation covering the project overview, security reporting, release history, licensing, and attribution.

## Development rule of thumb

When a test fails, first determine which category it belongs to:

1. a real MWEB Vault/Litecoin wallet defect,
2. a Litecoin-specific fixture or policy difference,
3. an inherited compatibility vector that must remain unchanged, or
4. CI/build infrastructure.

Fix the underlying category rather than changing production behavior solely to satisfy a stale assertion.
