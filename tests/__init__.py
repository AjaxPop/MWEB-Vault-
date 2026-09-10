import asyncio
import os
import unittest
import threading
import tempfile
import shutil
import functools
import inspect
import re
from typing import TYPE_CHECKING, List

import electrum
import electrum.logging
from electrum import bitcoin, constants, segwit_addr
from electrum import util
from electrum.util import OldTaskGroup
from electrum.logging import Logger
from electrum.wallet import restore_wallet_from_text

if TYPE_CHECKING:
    from .test_lnpeer import MockLNWallet


# Set this locally to make the test suite run faster.
# If set, unit tests that would normally test functions with multiple implementations,
# will only be run once, using the fastest implementation.
# e.g. libsecp256k1 vs python-ecdsa. pycryptodomex vs pyaes.
FAST_TESTS = False


electrum.logging._configure_stderr_logging(verbosity="*")

electrum.util.AS_LIB_USER_I_WANT_TO_MANAGE_MY_OWN_ASYNCIO_LOOP = True



def _convert_legacy_bitcoin_wallet_fixture_address(value):
    """Re-encode inherited Bitcoin wallet-fixture addresses for Litecoin tests."""
    if not isinstance(value, str):
        return value

    lower = value.lower()
    for old_hrp, new_hrp in (("bc", "ltc"), ("tb", "tltc")):
        if lower.startswith(old_hrp + "1"):
            witver, witprog = segwit_addr.decode_segwit_address(old_hrp, value)
            if witprog is None:
                return value
            converted = segwit_addr.encode_segwit_address(
                new_hrp, witver, bytes(witprog)
            )
            return converted if converted is not None else value

    try:
        payload = bitcoin.DecodeBase58Check(value)
    except Exception:
        return value
    if len(payload) != 21:
        return value

    # Bitcoin mainnet P2PKH/P2SH and Bitcoin-testnet P2SH use different
    # display prefixes from Litecoin. Testnet P2PKH uses 111 on both chains.
    version_map = {
        0: constants.BitcoinMainnet.ADDRTYPE_P2PKH,
        5: constants.BitcoinMainnet.ADDRTYPE_P2SH,
        196: constants.BitcoinTestnet.ADDRTYPE_P2SH,
    }
    new_version = version_map.get(payload[0])
    if new_version is None or new_version == payload[0]:
        return value
    return bitcoin.EncodeBase58Check(bytes([new_version]) + payload[1:])


def _convert_legacy_bitcoin_wallet_fixture(value):
    if isinstance(value, dict):
        return {
            _convert_legacy_bitcoin_wallet_fixture_address(key):
                _convert_legacy_bitcoin_wallet_fixture(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_convert_legacy_bitcoin_wallet_fixture(item) for item in value]
    return _convert_legacy_bitcoin_wallet_fixture_address(value)


class ElectrumTestCase(unittest.IsolatedAsyncioTestCase, Logger):
    """Base class for our unit tests."""

    TESTNET = False  # there is also an @as_testnet decorator to run single tests in testnet mode
    REGTEST = False
    TEST_ANCHOR_CHANNELS = False
    WALLET_FILES_DIR = os.path.join(os.path.dirname(__file__), "test_storage_upgrade")
    # maxDiff = None  # for debugging

    # some unit tests are modifying globals... so we run sequentially:
    _test_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        Logger.__init__(self)
        unittest.IsolatedAsyncioTestCase.__init__(self, *args, **kwargs)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        assert not (cls.REGTEST and cls.TESTNET), "regtest and testnet are mutually exclusive"
        if cls.REGTEST:
            constants.BitcoinRegtest.set_as_network()
        elif cls.TESTNET:
            constants.BitcoinTestnet.set_as_network()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if cls.TESTNET or cls.REGTEST:
            constants.BitcoinMainnet.set_as_network()

    def setUp(self):
        have_lock = self._test_lock.acquire(timeout=0.1)
        if not have_lock:
            # This can happen when trying to run the tests in parallel,
            # or if a prior test raised  during `setUp` or `asyncSetUp` and never released the lock.
            raise Exception("timed out waiting for test_lock")
        super().setUp()
        self.unittest_base_path = tempfile.mkdtemp(prefix="electrum-unittest-base-")
        self.electrum_path = os.path.join(self.unittest_base_path, "electrum")
        util.make_dir(self.electrum_path)
        assert util._asyncio_event_loop is None, "global event loop already set?!"
        self._lnworkers_created = []  # type: List[MockLNWallet]

    async def asyncSetUp(self):
        await super().asyncSetUp()
        loop = util.get_asyncio_loop()
        # IsolatedAsyncioTestCase creates event loops with debug=True, which makes the tests take ~4x time
        if not (os.environ.get("PYTHONASYNCIODEBUG") or os.environ.get("PYTHONDEVMODE")):
            loop.set_debug(False)
        util._asyncio_event_loop = loop

    async def asyncTearDown(self):
        # clean up lnworkers
        async with OldTaskGroup() as group:
            for lnworker in self._lnworkers_created:
                await group.spawn(lnworker.stop())
        self._lnworkers_created.clear()
        await super().asyncTearDown()

    def tearDown(self):
        util.callback_mgr.clear_all_callbacks()
        shutil.rmtree(self.unittest_base_path)
        super().tearDown()
        util._asyncio_event_loop = None  # cleared here, at the ~last possible moment. asyncTearDown is too early.
        self._test_lock.release()

    def create_mock_lnwallet(
        self,
        *,
        name: str,
        has_anchors: bool,
    ) -> 'MockLNWallet':
        from .test_lnpeer import _create_mock_lnwallet
        data_dir = tempfile.mkdtemp(prefix="lnwallet-", dir=self.unittest_base_path)
        lnwallet = _create_mock_lnwallet(name=name, has_anchors=has_anchors, data_dir=data_dir)
        self._lnworkers_created.append(lnwallet)
        return lnwallet

    def get_wallet_file_path(self, wallet_name: str) -> str:
        source_path = os.path.join(self.WALLET_FILES_DIR, wallet_name)
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                original_text = f.read()
        except OSError:
            return source_path

        # Wallet files can be an initial JSON document followed by newline-delimited
        # JSON-patch entries. Work on JSON string tokens in the raw text so the
        # journal, tx hex, hashes, keys, and other historical material stay intact.
        escaped_backslash = re.escape(chr(92))
        json_string_re = re.compile(
            '"' + '([^"' + escaped_backslash + ']*(?:'
            + escaped_backslash + '.[^"' + escaped_backslash + ']*)*)' + '"'
        )

        def convert_json_string(match):
            value = match.group(1)
            if chr(92) in value:
                return match.group(0)
            # Patch paths can contain addresses as slash-separated path segments.
            parts = value.split("/")
            converted_parts = [
                _convert_legacy_bitcoin_wallet_fixture_address(part)
                for part in parts
            ]
            converted = "/".join(converted_parts)
            if converted == value:
                return match.group(0)
            return f'"{converted}"'

        converted_text = json_string_re.sub(convert_json_string, original_text)
        if converted_text == original_text:
            return source_path

        converted_path = os.path.join(
            self.unittest_base_path, f"ltc-fixture-{wallet_name}"
        )
        with open(converted_path, "w", encoding="utf-8") as f:
            f.write(converted_text)
        return converted_path


def as_testnet(func):
    """Function decorator to run a single unit test in testnet mode.

    NOTE: this is inherently sequential; tests running in parallel would break things
    """
    old_net = constants.net
    if inspect.iscoroutinefunction(func):
        async def run_test(*args, **kwargs):
            try:
                constants.BitcoinTestnet.set_as_network()
                return await func(*args, **kwargs)
            finally:
                constants.net = old_net
    else:
        def run_test(*args, **kwargs):
            try:
                constants.BitcoinTestnet.set_as_network()
                return func(*args, **kwargs)
            finally:
                constants.net = old_net
    return run_test


def _convert_legacy_testnet_address_import(text):
    """Re-encode inherited Bitcoin-testnet address-only wallet imports for Litecoin testnet.

    Electrum-LTC inherited a few tests that import whitespace-separated ``tb1`` addresses.
    The witness programs are network-independent; only the human-readable prefix and checksum
    need to be re-encoded. Keep this deliberately narrow so seeds, keys, negative vectors, and
    mixed input are never rewritten behind a test's back.
    """
    if not isinstance(text, str) or constants.net.SEGWIT_HRP != 'tltc':
        return text
    tokens = text.split()
    if not tokens or not all(token.lower().startswith('tb1') for token in tokens):
        return text
    converted = []
    for token in tokens:
        witver, witprog = segwit_addr.decode_segwit_address('tb', token)
        if witprog is None:
            return text
        address = segwit_addr.encode_segwit_address('tltc', witver, bytes(witprog))
        if address is None:
            return text
        converted.append(address)
    return ' '.join(converted)


@functools.wraps(restore_wallet_from_text)
def restore_wallet_from_text__for_unittest(*args, gap_limit=2, gap_limit_for_change=1, **kwargs):
    """much lower default gap limits (to save compute time)"""
    if args:
        args = (_convert_legacy_testnet_address_import(args[0]), *args[1:])
    elif 'text' in kwargs:
        kwargs['text'] = _convert_legacy_testnet_address_import(kwargs['text'])
    return restore_wallet_from_text(
        *args,
        gap_limit=gap_limit,
        gap_limit_for_change=gap_limit_for_change,
        **kwargs,
    )
