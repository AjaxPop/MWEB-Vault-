## Summary

Backport upstream Electrum's SPV hardening for CVE-2012-2459 to Electrum-LTC.

Due to the way Bitcoin-style transaction Merkle trees duplicate odd nodes, multiple different leaf layouts can produce the same Merkle root. For an SPV client, that means Merkle-root validation alone is not sufficient to validate the claimed **position** of a transaction in the block.

This patch rejects a duplicated hash when it appears as a **left sibling** while walking the proof. Legitimate balancing duplicates appear as right siblings, so valid proofs remain accepted.

## Changes

- add `LeftSiblingDuplicate` as a dedicated Merkle verification failure
- track whether the current hash is the right child while walking the Merkle proof
- reject a proof when a left sibling is identical to the current hash
- preserve legitimate right-sibling duplication used to balance odd Merkle-tree levels
- add regression tests covering both the valid and malicious duplicate cases

## Security context / original references

This is a direct backport of the security hardening merged upstream in Electrum:

- Electrum PR #10568: https://github.com/spesmilo/electrum/pull/10568
- Electrum 4.8.0 release notes, which list this as a low-severity SPV security fix: https://github.com/spesmilo/electrum/blob/master/RELEASE-NOTES
- Original BitcoinTalk discussion referenced by the upstream Electrum PR: https://bitcointalk.org/?topic=102395
- Electron Cash implementation that upstream Electrum ported from: https://github.com/Electron-Cash/Electron-Cash/commit/165146362b4cb0ad74770b36aca1f9acb2800195
- Original Bitcoin.org CVE-2012-2459 security notice: https://bitcoin.org/en/alert/2012-05-14-dos
- Bitcoin Core's current Merkle implementation documents the duplicate-txid flaw as CVE-2012-2459: https://github.com/bitcoin/bitcoin/blob/master/src/consensus/merkle.cpp

## Testing

Regression coverage is added to `tests/test_verifier.py` for:

1. a legitimate right-sibling duplicate, which must continue to verify
2. a forged left-sibling duplicate, which must raise `LeftSiblingDuplicate`

Suggested test command:

```bash
python3 -m pytest tests/test_verifier.py -v
```

## Upstream assessment

Upstream Electrum described the issue as **low severity** for Electrum and released the fix in Electrum 4.8.0.
