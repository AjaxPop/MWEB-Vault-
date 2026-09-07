# MWEB Vault for Litecoin

*An Electrum-LTC fork focused on MWEB and wallet security.*

MWEB Vault is based on **Electrum-LTC 4.7.2** and continues development as an independent Litecoin wallet focused on MWEB functionality, security, and privacy.

## Project Information

**Repository:**  
https://github.com/AjaxPop/MWEB-Vault-

**Base version:** Electrum-LTC `4.7.2`

MWEB Vault maintains its historical Electrum-LTC lineage while being developed as its own independent project.

MWEB Vault is not an official release of the Electrum-LTC project.

```
Licence: MIT Licence
Original Author: Thomas Voegtlin
Original Port Maintainer: Hector Chu
Language: Python (>= 3.10)
Repository: https://github.com/AjaxPop/MWEB-Vault-
```

## SPV Merkle-Proof Hardening

This repository includes the saved patch tooling and documentation for the CVE-2012-2459-style left-sibling duplicate Merkle-proof hardening work.

- `open_electrum_ltc_spv_pr.sh` applies the verifier change and regression tests to an Electrum-LTC source tree.
- `electrum_ltc_spv_pr_body.md` documents the security rationale, upstream references, and testing approach.

## License

MWEB Vault is distributed under the **MIT License**, consistent with the Electrum-LTC codebase from which it was forked.

The MIT License permits use, copying, modification, merging, publication, distribution, sublicensing, and sale of copies of the software, provided that the copyright and permission notice are retained.

See the repository's [`LICENCE`](LICENCE) file for the complete license terms and original copyright notices.

## AI Usage

Portions of MWEB Vault may be developed with assistance from ChatGPT by OpenAI.

OpenAI's Terms of Use state:

> “As between you and OpenAI, and to the extent permitted by applicable law, you … own the Output. We hereby assign to you all our right, title, and interest, if any, in and to Output.”

**OpenAI Terms of Use:** Updated October 23, 2024  
**Archived copy retrieved September 7, 2026:**  
https://web.archive.org/web/20260907212205/https://openai.com/en-GB/policies/oct-2024-row-terms/

AI-generated or AI-assisted contributions incorporated into this repository remain subject to the project's MIT License and any applicable third-party license obligations.
