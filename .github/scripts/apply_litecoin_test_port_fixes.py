from pathlib import Path


def replace_exact(path: str, old: str, new: str, *, expected: int = 1) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    found = text.count(old)
    if found != expected:
        raise SystemExit(
            f"{path}: expected {expected} match(es), found {found}: {old!r}"
        )
    p.write_text(text.replace(old, new), encoding="utf-8")


# tests/test_bitcoin.py: finish porting positive Litecoin message-signing vectors.
path = "tests/test_bitcoin.py"
replace_exact(
    path,
    "        self.assertEqual(sig1_b64, b'IHGAMaPxjrn3CD19S7J5KAq4xF6mdLznsSL8SrqhNwficUHlK5wSth6/JiZ/pEyo92nkUoA+kL9VJpjLnKJKTmM=')",
    "        self.assertEqual(sig1_b64, b'ICzNsKuXKK99r36McDcxN8YpB3Bwe+wZpCIeiSCIv0IMMdY1gFymqipODrpO5E9qff3+qtqib7X8zOKQKiGD5pA=')",
)
replace_exact(
    path,
    "        self.assertEqual(sig2_b64, b'G14KtfFZQYjyhz4PUzX/yz8eEC1BFHsaEKZOJGLeTWJoNp/umpi5zPeCvhUcgSoMtAkmw3pATrM2bcDdYi1tqIs=')",
    "        self.assertEqual(sig2_b64, b'G777Nqh3YlTVpWqGxSSVHtX013bTzdU/lmgzrRVuL6qYGnpd87PyI9T/LIZvbq7KdfPK2A5Ij1xUkujZwR1sl6M=')",
)
replace_exact(
    path,
    '        addr = "15hETetDmcXm1mM4sEf7U2KXC9hDHFMSzz"',
    '        addr = "LPvBisC3rGmpGa3E3NeQk3PHQN4VS237y2"',
)
replace_exact(
    path,
    "        sig_low_s = b'Hzsu0U/THAsPz/MSuXGBKSULz2dTfmrg1NsAhFp+wH5aKfmX4Db7ExLGa7FGn0m6Mf43KsbEOWpvUUUBTM3Uusw='",
    "        sig_low_s = b'ICzNsKuXKK99r36McDcxN8YpB3Bwe+wZpCIeiSCIv0IMMdY1gFymqipODrpO5E9qff3+qtqib7X8zOKQKiGD5pA='",
)
replace_exact(
    path,
    "        sig_high_s = b'IDsu0U/THAsPz/MSuXGBKSULz2dTfmrg1NsAhFp+wH5a1gZoH8kE7O05lE65YLZFzLx3sh/rDzXMbo1dQAJhhnU='",
    "        sig_high_s = b'HyzNsKuXKK99r36McDcxN8YpB3Bwe+wZpCIeiSCIv0IMzinKf6NZVdWx8UWxG7CVgLywMgwM2Oo+8u/OYq6yWrE='",
)
replace_exact(
    path,
    "b'H3nh1AqVvauwclOAPs2serBtro9Iei1Q7vZZfmivo6ioQ6EzNYq5No90CU5RXM17d05eO+bXd0p/r/Sl5fPz390='",
    "b'IHy4YwzlygjztfZnLoKZVLaKHFUijI1bJNX9oaE7JufBN2ZUJR4y4fp7g4dDb8+qkhJGB0HRiAViE+qDH9zoSRc='",
    expected=2,
)
replace_exact(
    path,
    '        addr1 = "MS2NsKymog9TrEVq4wbrjn1oYS7MiPDkqR"',
    '        addr1 = "MKkwVip3KDUb2WFJqr8bGebGPHNAXwGG1f"',
)
replace_exact(
    path,
    '        addr2 = "ltc1qnw6a545d64e94r4vts80n89nmcpud5fdftvryq"',
    '        addr2 = "ltc1qq2tmmcngng78nllq2pvrkchcdukemtj57q7cpl"',
)
replace_exact(
    path,
    '        sig1 = bytes.fromhex("23744de4516fac5c140808015664516a32fead94de89775cec7e24dbc24fe133075ac09301c4cc8e197bea4b6481661d5b8e9bf19d8b7b8a382ecdb53c2ee0750d")',
    '        sig1 = bytes.fromhex("24d3ee707f82dee697957009a75802c6a2edb58f5b0b407aafbc55b98e6d8356590c24a081c9014be1da50f14392d700a9eea6255fafc4236a5094bfcdcd404f1f")',
)
replace_exact(
    path,
    '        sig2 = bytes.fromhex("28b55d7600d9e9a7e2a49155ddf3cfdb8e796c207faab833010fa41fb7828889bc47cf62348a7aaa0923c0832a589fab541e8f12eb54fb711c90e2307f0f66b194")',
    '        sig2 = bytes.fromhex("28d3ee707f82dee697957009a75802c6a2edb58f5b0b407aafbc55b98e6d8356590c24a081c9014be1da50f14392d700a9eea6255fafc4236a5094bfcdcd404f1f")',
)
replace_exact(
    path,
    '        sig1_wrongtype = bytes.fromhex("27744de4516fac5c140808015664516a32fead94de89775cec7e24dbc24fe133075ac09301c4cc8e197bea4b6481661d5b8e9bf19d8b7b8a382ecdb53c2ee0750d")',
    "        sig1_wrongtype = sig2",
)
replace_exact(
    path,
    '        sig2_wrongtype = bytes.fromhex("24b55d7600d9e9a7e2a49155ddf3cfdb8e796c207faab833010fa41fb7828889bc47cf62348a7aaa0923c0832a589fab541e8f12eb54fb711c90e2307f0f66b194")',
    "        sig2_wrongtype = sig1",
)

# A mixed-case validity test must use Litecoin's HRP, not Bitcoin's.
replace_exact(
    path,
    "        bech32_mixed_case1 = 'BC1QW508D6QEJXTDG4Y5R3zarvary0c5xw7kv8f3t4'",
    "        bech32_mixed_case1 = 'LTC1QW508D6QEJXTDG4Y5R3zarvary0c5xw7kgmn4n9'",
)

# Cover Litecoin MWEB and Ltub extended-key headers already declared in constants.py.
replace_exact(
    path,
    "            'p2wsh':       'Zprv',\n        }",
    "            'p2wsh':       'Zprv',\n            'mweb':        'nprv' if constants.net.TESTNET else 'mprv',\n        }",
)
replace_exact(
    path,
    "            'p2wsh':       'Zpub',\n        }",
    "            'p2wsh':       'Zpub',\n            'p2wpkh2':     'Ltub',\n            'mweb':        'npub' if constants.net.TESTNET else 'mpub',\n        }",
)

# BIP341's expected script/address pair is Bitcoin-encoded. Keep the script vector,
# but re-encode the witness program with the active Litecoin HRP for address comparison.
replace_exact(
    path,
    '            self.assertEqual(tcase["expected"]["bip350Address"], bitcoin.script_to_address(spk))',
    '''            expected_witver, expected_witprog = segwit_addr.decode_segwit_address(
                "bc", tcase["expected"]["bip350Address"]
            )
            self.assertIsNotNone(expected_witprog)
            expected_ltc_address = segwit_addr.encode_segwit_address(
                constants.net.SEGWIT_HRP, expected_witver, bytes(expected_witprog)
            )
            self.assertEqual(expected_ltc_address, bitcoin.script_to_address(spk))''',
)


# tests/__init__.py: convert only display-address encodings in inherited Bitcoin
# wallet JSON fixtures. The original fixtures, raw tx data, keys and hashes stay untouched.
path = "tests/__init__.py"
replace_exact(path, "import inspect\n", "import inspect\nimport json\n")
replace_exact(
    path,
    "from electrum import constants, segwit_addr",
    "from electrum import bitcoin, constants, segwit_addr",
)

fixture_helpers = r'''


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
'''
replace_exact(
    path,
    "\n\nclass ElectrumTestCase(unittest.IsolatedAsyncioTestCase, Logger):",
    fixture_helpers + "\n\nclass ElectrumTestCase(unittest.IsolatedAsyncioTestCase, Logger):",
)
replace_exact(
    path,
    '''    def get_wallet_file_path(self, wallet_name: str) -> str:
        return os.path.join(self.WALLET_FILES_DIR, wallet_name)''',
    '''    def get_wallet_file_path(self, wallet_name: str) -> str:
        source_path = os.path.join(self.WALLET_FILES_DIR, wallet_name)
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                original_data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return source_path

        converted_data = _convert_legacy_bitcoin_wallet_fixture(original_data)
        if converted_data == original_data:
            return source_path

        converted_path = os.path.join(
            self.unittest_base_path, f"ltc-fixture-{wallet_name}"
        )
        with open(converted_path, "w", encoding="utf-8") as f:
            json.dump(converted_data, f)
        return converted_path''',
)


# tests/test_commands.py: expected display addresses for the converted testnet fixture.
replace_exact(
    "tests/test_commands.py",
    "tb1qr5mf6sumdlhjrq9t6wlyvdm960zu0n0t5d60ug",
    "tltc1qr5mf6sumdlhjrq9t6wlyvdm960zu0n0td9c3vp",
)
replace_exact(
    "tests/test_commands.py",
    "tb1qp3p2d72gj2l7r6za056tgu4ezsurjphper4swh",
    "tltc1qp3p2d72gj2l7r6za056tgu4ezsurjphpqthw77",
)


# tests/test_lnpeer.py: preserve the test's intended directional liquidity while
# making channel totals large enough for Litecoin's channel reserve/dust floor.
replace_exact(
    "tests/test_lnpeer.py",
    '''        graph_definition['alice']['channels']['carol']['local_balance_msat'] = 200_000_000
        graph_definition['alice']['channels']['carol']['remote_balance_msat'] = 200_000_000
        graph_definition['carol']['channels']['dave']['local_balance_msat'] = 50_000_000
        graph_definition['carol']['channels']['dave']['remote_balance_msat'] = 200_000_000
        graph_definition['alice']['channels']['bob']['local_balance_msat'] = 200_000_000
        graph_definition['alice']['channels']['bob']['remote_balance_msat'] = 200_000_000
        graph_definition['bob']['channels']['dave']['local_balance_msat'] = 200_000_000
        graph_definition['bob']['channels']['dave']['remote_balance_msat'] = 200_000_000''',
    '''        graph_definition['alice']['channels']['carol']['local_balance_msat'] = 200_000_000
        graph_definition['alice']['channels']['carol']['remote_balance_msat'] = 400_000_000
        graph_definition['carol']['channels']['dave']['local_balance_msat'] = 50_000_000
        graph_definition['carol']['channels']['dave']['remote_balance_msat'] = 550_000_000
        graph_definition['alice']['channels']['bob']['local_balance_msat'] = 200_000_000
        graph_definition['alice']['channels']['bob']['remote_balance_msat'] = 400_000_000
        graph_definition['bob']['channels']['dave']['local_balance_msat'] = 200_000_000
        graph_definition['bob']['channels']['dave']['remote_balance_msat'] = 400_000_000''',
)


# Clean up the transport files in the resulting source commit.
for temp_path in (
    ".github/workflows/apply-litecoin-test-port-fixes.yml",
    ".github/scripts/apply_litecoin_test_port_fixes.py",
    ".ci-trigger-litecoin-fixes",
):
    p = Path(temp_path)
    if p.exists():
        p.unlink()
