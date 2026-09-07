#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_REPO="ltc-electrum/electrum-ltc"
BASE_BRANCH="mweb"
BRANCH="fix/spv-cve-2012-2459"

for cmd in git gh python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "$cmd is required." >&2
    exit 1
  fi
done

gh auth status >/dev/null

if [[ ! -d .git ]]; then
  echo "Run this script from inside your electrum-ltc clone." >&2
  exit 1
fi

origin_url="$(git remote get-url origin 2>/dev/null || true)"
if [[ "$origin_url" != *"ltc-electrum/electrum-ltc"* ]]; then
  echo "Warning: origin does not appear to be ltc-electrum/electrum-ltc: $origin_url" >&2
fi

git fetch origin "$BASE_BRANCH"
git switch "$BASE_BRANCH"
git pull --ff-only origin "$BASE_BRANCH"

if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git switch "$BRANCH"
  git reset --hard "origin/$BASE_BRANCH"
else
  git switch -c "$BRANCH" "origin/$BASE_BRANCH"
fi

python3 - <<'PY'
from pathlib import Path

verifier = Path("electrum/verifier.py")
tests = Path("tests/test_verifier.py")

if not verifier.exists():
    raise SystemExit("electrum/verifier.py not found")
if not tests.exists():
    raise SystemExit("tests/test_verifier.py not found")

v = verifier.read_text()

exc_old = "class InnerNodeOfSpvProofIsValidTx(MerkleVerificationFailure): pass\n\n\nclass SPV"
exc_new = (
    "class InnerNodeOfSpvProofIsValidTx(MerkleVerificationFailure): pass\n"
    "class LeftSiblingDuplicate(MerkleVerificationFailure): pass\n\n\nclass SPV"
)
if "class LeftSiblingDuplicate(MerkleVerificationFailure): pass" not in v:
    if exc_old not in v:
        raise SystemExit("Could not find expected verifier exception block; refusing to patch blindly.")
    v = v.replace(exc_old, exc_new, 1)

loop_old = '''        for item in merkle_branch_bytes:
            if len(item) != 32:
                raise MerkleVerificationFailure('all merkle branch items have to be 32 bytes long')
            inner_node = (item + h) if (index & 1) else (h + item)
            cls._raise_if_valid_tx(inner_node.hex())
            h = sha256d(inner_node)
            index >>= 1
'''

loop_new = '''        for sibling in merkle_branch_bytes:
            if len(sibling) != 32:
                raise MerkleVerificationFailure('all merkle branch items have to be 32 bytes long')
            is_right_child = (index & 1)
            inner_node = (sibling + h) if is_right_child else (h + sibling)
            # CVE-2017-12842 protection: inner node must not be a valid tx
            cls._raise_if_valid_tx(inner_node.hex())
            # CVE-2012-2459 protection: reject left-sibling duplicates
            if is_right_child and sibling == h:
                raise LeftSiblingDuplicate()
            h = sha256d(inner_node)
            index >>= 1
'''

if "if is_right_child and sibling == h:" not in v:
    if loop_old not in v:
        raise SystemExit("Could not find expected Merkle loop; refusing to patch blindly.")
    v = v.replace(loop_old, loop_new, 1)

old_comment = "        # If an inner node of the merkle proof is also a valid tx, chances are, this is an attack.\n"
new_comment = "        # CVE-2017-12842: If an inner node of the merkle proof is also a valid tx, chances are, this is an attack.\n"
if old_comment in v:
    v = v.replace(old_comment, new_comment, 1)

verifier.write_text(v)

t = tests.read_text()

old_import = "from electrum.verifier import SPV, InnerNodeOfSpvProofIsValidTx"
new_import = "from electrum.verifier import SPV, InnerNodeOfSpvProofIsValidTx, LeftSiblingDuplicate"
if "LeftSiblingDuplicate" not in t:
    if old_import not in t:
        raise SystemExit("Could not find expected test import; refusing to patch blindly.")
    t = t.replace(old_import, new_import, 1)

test_class = '''

class TestVerifier_CVE_2012_2459(ElectrumTestCase):
    """Regression tests for left-sibling duplicate Merkle proofs."""

    TESTNET = True

    # Bitcoin testnet3 block 4909055. The hashing rule being tested is shared
    # by Bitcoin-style transaction Merkle trees and is chain-independent here.
    MERKLE_BRANCH = [
        '9b2c7e407188465594832cfbe84c9758029084527c855ea29a16603e5d1c51b6',
        'a8484ccbaa74ffa060d0a500f7ce3ea4953beace18df8384024dfa9290385b1c',
    ]
    MERKLE_ROOT = '3465af659f6438b133c6d980accbb61b7be43f8ad899e40054e33b37aecba28e'
    TXID = '9b2c7e407188465594832cfbe84c9758029084527c855ea29a16603e5d1c51b6'

    def test_valid_right_sibling_duplicate(self):
        leaf_pos_in_tree = 2
        self.assertEqual(
            self.MERKLE_ROOT,
            SPV.hash_merkle_root(self.MERKLE_BRANCH, self.TXID, leaf_pos_in_tree),
        )

    def test_malicious_left_sibling_duplicate(self):
        leaf_pos_in_tree = 3
        with self.assertRaises(LeftSiblingDuplicate):
            SPV.hash_merkle_root(self.MERKLE_BRANCH, self.TXID, leaf_pos_in_tree)
'''

if "class TestVerifier_CVE_2012_2459" not in t:
    t = t.rstrip() + test_class + "\n"

tests.write_text(t)
PY

git diff --check
python3 -m pytest tests/test_verifier.py -v

git add electrum/verifier.py tests/test_verifier.py
git diff --cached

if git diff --cached --quiet; then
  echo "No changes to commit."
  exit 0
fi

git commit -m "verifier.py: reject left-sibling duplicate Merkle proofs"

GH_USER="$(gh api user --jq .login)"
FORK_REPO="$GH_USER/electrum-ltc"

if ! gh repo view "$FORK_REPO" >/dev/null 2>&1; then
  gh repo fork "$UPSTREAM_REPO" --clone=false
fi

FORK_URL="https://github.com/${FORK_REPO}.git"
if git remote get-url fork >/dev/null 2>&1; then
  git remote set-url fork "$FORK_URL"
else
  git remote add fork "$FORK_URL"
fi

git push -u fork "$BRANCH"

BODY_FILE="$(mktemp)"
cat > "$BODY_FILE" <<'EOF'
## Summary

Backport upstream Electrum's CVE-2012-2459 SPV hardening to Electrum-LTC.

Bitcoin-style Merkle trees duplicate odd nodes when balancing a level. Without a position-sensitive duplicate check, a malicious proof can reinterpret a duplicated subtree as containing real leaves and claim a phantom transaction position while producing the same Merkle root.

## Changes

- add `LeftSiblingDuplicate` as a dedicated Merkle verification failure
- track whether the current hash is the right child while walking the proof
- reject a proof when a left sibling is identical to the current hash
- preserve legitimate right-sibling duplication used to balance odd Merkle-tree levels
- add regression tests covering both valid and malicious duplicate cases

## Testing

`python3 -m pytest tests/test_verifier.py -v`

## Upstream reference

Ported from Electrum PR #10568:
https://github.com/spesmilo/electrum/pull/10568

Upstream described this as a low-severity SPV verification issue.
EOF

gh pr create \
  --repo "$UPSTREAM_REPO" \
  --base "$BASE_BRANCH" \
  --head "${GH_USER}:${BRANCH}" \
  --title "verifier.py: fix CVE-2012-2459 left-sibling duplicates" \
  --body-file "$BODY_FILE"

rm -f "$BODY_FILE"
