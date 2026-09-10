"""Pytest-only compatibility fixtures for the Litecoin port.

Keep inherited Bitcoin test vectors out of production code.  The helpers here only
replace test data whose network-specific encoding is known to be wrong for Litecoin.
"""

import hashlib
import struct
import sys


def _hash_header(raw_header: bytes) -> str:
    return hashlib.sha256(hashlib.sha256(raw_header).digest()).digest()[::-1].hex()


def _make_litecoin_regtest_headers(count: int = 13) -> dict[int, bytes]:
    """Build a deterministic header chain rooted at Litecoin's regtest genesis.

    Interface tests only need a self-consistent short chain.  Regtest/testnet header
    verification skips proof-of-work in Electrum-LTC, but height zero still has to be
    Litecoin's real regtest genesis because it is checked against constants.net.GENESIS.
    """
    genesis = bytes.fromhex(
        "01000000"
        + "00" * 32
        + "d9ced4ed1130f7b7faad9be25323ffafa33232a17c3edf6cfd97bee6bafbdd97"
        + "dae5494d"
        + "ffff7f20"
        + "00000000"
    )
    assert _hash_header(genesis) == "530827f38f93b43ed12af0b3ad25a288dc02ed74d6d7857862df51fc56c416f9"

    headers = {0: genesis}
    prev_hash = _hash_header(genesis)
    for height in range(1, count):
        merkle_root = hashlib.sha256(f"mweb-vault-regtest-{height}".encode()).digest()
        raw_header = (
            struct.pack("<I", 1)
            + bytes.fromhex(prev_hash)[::-1]
            + merkle_root
            + struct.pack("<III", 1296688602 + height, 0x207FFFFF, height)
        )
        headers[height] = raw_header
        prev_hash = _hash_header(raw_header)
    return headers


def pytest_collection_modifyitems(session, config, items):
    """Replace the inherited Bitcoin-regtest interface header fixture after collection."""
    test_interface = sys.modules.get("tests.test_interface")
    if test_interface is not None:
        test_interface.BLOCK_HEADERS = _make_litecoin_regtest_headers()
