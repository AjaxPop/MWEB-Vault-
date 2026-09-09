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


# 1. Testnet extended-key expectations must include Litecoin MWEB headers.
replace_exact(
    "tests/test_bitcoin.py",
    "            'p2wsh':       'Vprv',\n        }\n        xpub_headers_b58 = {",
    "            'p2wsh':       'Vprv',\n            'mweb':        'nprv',\n        }\n        xpub_headers_b58 = {",
)
replace_exact(
    "tests/test_bitcoin.py",
    "            'p2wsh':       'Vpub',\n        }\n        for xtype, xkey_header_bytes in constants.net.XPRV_HEADERS.items():",
    "            'p2wsh':       'Vpub',\n            'mweb':        'npub',\n        }\n        for xtype, xkey_header_bytes in constants.net.XPRV_HEADERS.items():",
)

# Keep the remaining legacy-signature failure maximally diagnostic. The next CI
# failure will print the complete deterministic Litecoin signature, rather than a
# shortened pytest diff, so we can update the vector from exact evidence.
replace_exact(
    "tests/test_bitcoin.py",
    "        self.assertEqual(sig2_b64, b'G777Nqh3YlTVpWqGxSSVHtX013bTzdU/lmgzrRVuL6qYGnpd87PyI9T/LIZvbq7KdfPK2A5Ij1xUkujZwR1sl6M=')",
    "        print(f'actual Litecoin sig2_b64: {sig2_b64!r}')\n        self.assertEqual(sig2_b64, b'G777Nqh3YlTVpWqGxSSVHtX013bTzdU/lmgzrRVuL6qYGnpd87PyI9T/LIZvbq7KdfPK2A5Ij1xUkujZwR1sl6M=')",
)

# 2. TxInput JSON now includes the Litecoin MWEB pegout marker.
replace_exact(
    "tests/test_commands.py",
    "                            'coinbase': False,\n                            'nsequence': 4294967293,",
    "                            'coinbase': False,\n                            'pegout': False,\n                            'nsequence': 4294967293,",
)

# 3. Historical Electrum wallet fixtures can contain an initial JSON document
# followed by a JSON-patch journal. Convert address strings in the raw text copy
# instead of parsing/dumping the file, which preserves that journal exactly.
replace_exact("tests/__init__.py", "import json\n", "import re\n")
replace_exact(
    "tests/__init__.py",
    """    def get_wallet_file_path(self, wallet_name: str) -> str:
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
        return converted_path
""",
    """    def get_wallet_file_path(self, wallet_name: str) -> str:
        source_path = os.path.join(self.WALLET_FILES_DIR, wallet_name)
        try:
            with open(source_path, "r", encoding="utf-8") as f:
                original_text = f.read()
        except OSError:
            return source_path

        # Wallet files can be an initial JSON document followed by newline-delimited
        # JSON-patch entries. Work on JSON string tokens in the raw text so the
        # journal, tx hex, hashes, keys, and other historical material stay intact.
        json_string_re = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')

        def convert_json_string(match):
            value = match.group(1)
            if "\\" in value:
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
""",
)

# 4. Imported private-key fixtures: preserve private scalars and compression bits,
# but encode stale Bitcoin WIF version 0x80 with Litecoin mainnet version 0xb0.
replace_exact(
    "tests/test_wallet.py",
    "p2wpkh:L24GxnN7NNUAfCXA6hFzB1jt59fYAAiFZMcLaJ2ZSawGpM3uqhb1",
    "p2wpkh:T7tYQXfHmkSmS3A2eLCrPNHG21JrEFj9NZWbS6f71Z7SLEgRqD97",
)
replace_exact(
    "tests/test_wallet.py",
    "p2wpkh:KzuqaaLp9zYjVuj8vQtCwFdiZFreW3NJNBachgVS8S9XMgj5y78b",
    "p2wpkh:T6k72KdzZNXLGkN1U3q59cB6W7Vxa8PCBPUsZV7yhQKgsaFSu28Y",
)
replace_exact(
    "tests/test_wallet.py",
    'self.assertEqual("1NNkttn1YvVGdqBW4PR6zvc3Zx3H5owKRf", addr)',
    'self.assertEqual("LgbiA75qdajKtdsfEXQQGwfonAQZEEEbjS", addr)',
)

# FakeWallet is a test double. WalletDB.get_transaction now annotates returned
# transaction objects with _cached_txid, so use an object instead of the literal
# string "Tx" while keeping verified_tx independent.
replace_exact(
    "tests/test_wallet.py",
    "        self.db.transactions = self.db.verified_tx = {'abc':'Tx'}",
    "        self.db.transactions = {'abc': mock.Mock()}\n        self.db.verified_tx = {'abc': 'Tx'}",
)

# 5. Remaining mainnet wallet-integrity expectations inherited from Bitcoin.
# Re-encode the same script hashes/witness programs with Litecoin address prefixes.
address_replacements = {
    '35L8XmCDoEBKeaWRjvmZvoZvhp8BXMMMPV': 'MBYGqecBkM2kT5nKqokukSpL2WidauKrDi',
    '3PeZEcumRqHSPNN43hd4yskGEBdzXgY8Cy': 'MVrhYWKjNx8sBsdx9acQoWzfYtESZAcsCV',
    '39XK9VBGiK4bqNJYrajfKE8C1ky4gYA5Zy': 'MFjTTNbEfRv2dsaSxTj18sNbLTZWggpXsi',
    '3PKtHrjiKdsZ73ULZ4Sf1vDBnrUoAEtLDe': 'MVY2bk9gGkiyuYkEewRzqZTb7Z5FBZgLTu',
    '3Bw5jczNModhFAbvfwvUHbdGrC2Lh2qRQp': 'MJ9E3WQLJvV83fspmpup7EsgAtcnabsLi7',
    '3Ke6pKrmtSyyQaMob1ES4pk8siAAkRmst9': 'MRrF8DGjqZqQD5dhgtDmtTzYCQkchV2JYT',
    'bc1qpmufh0zjp5prfsrk2yskcy82sa26srqkd97j0457andc6m0gh5asw7kqd2': 'ltc1qpmufh0zjp5prfsrk2yskcy82sa26srqkd97j0457andc6m0gh5asd6csh0',
    'bc1qd4q50nft7kxm9yglfnpup9ed2ukj3tkxp793y0zya8dc9m39jcwq308dxz': 'ltc1qd4q50nft7kxm9yglfnpup9ed2ukj3tkxp793y0zya8dc9m39jcwqjtfau8',
    '38diDMcH7japAtpJjVKviBroQfTdvgpdqX': 'MEqrXF2F4rSEyQ6CqNKGXq7CjN45w8gvqi',
    '36Hd2PnEvJpN9pUdhpZWh3aQccbRp46FVc': 'MCVmLHCCsRfnxKkXohYrWgpowKBsqEuw3k',
    '1N4hqJRTVqUbwT5WCbbsQSwKRPPPzG1TSo': 'LgHf6WjHaVifCFmfNjbAgU15dbkg8DBcrh',
    '1FW3QQzbYRSUoNDDYGWPvSCoom8fBhPC9k': 'LZizfdJRd5gY4AuNiQVhCTGa1yVwJVkmq2',
    'bc1qs2svwhfz47qv9qju2waa6prxzv5f522fc4p06t': 'ltc1qs2svwhfz47qv9qju2waa6prxzv5f522fufmtzm',
    'bc1qmjq5nenac3vjwltldk5qsq4yd8mttw2dpkmx06': 'ltc1qmjq5nenac3vjwltldk5qsq4yd8mttw2d92pzh2',
    '3JDN4wF5BphZqcJFFYuDA7N1apzfPYyJLG': 'MQRWNpf38wYze7a9MRtYykcQuXb7U6LH87',
    '3J8zNvhJndqzBcuPuarzUn1kWs9N4ZY7HS': 'MQM8gp7GjkhQz8BJ1TrLJRG9qZjp1MDzTf',
}
for old, new in address_replacements.items():
    replace_exact("tests/test_wallet_vertical.py", old, new)
