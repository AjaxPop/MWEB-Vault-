import os
import asyncio
from decimal import Decimal
from unittest.mock import patch

from electrum import SimpleConfig, bitcoin, constants, segwit_addr
from electrum.invoices import Invoice
from electrum.lnaddr import LnAddr, lnencode
from electrum.payment_identifier import (
    maybe_extract_bech32_lightning_payment_identifier, PaymentIdentifier, PaymentIdentifierType,
    PaymentIdentifierState, invoice_from_payment_identifier, remove_uri_prefix,
)
from electrum.lnurl import LNURL6Data, LNURL3Data, LNURLError
from electrum.transaction import PartialTxOutput

from . import ElectrumTestCase
from . import restore_wallet_from_text__for_unittest


_RHASH = bytes.fromhex('0001020304050607080900010203040506070809000102030405060708090102')
_PAYMENT_SECRET = bytes.fromhex('11' * 32)
_PRIVKEY = bytes.fromhex('e126f68f7eafcc8b74f54d269fe206be715000f94dac067d1c04a8ca3b2db734')


def _ltc_bech32_from_bitcoin(address: str) -> str:
    """Re-encode a Bitcoin Bech32 test vector for Litecoin without changing its witness program."""
    witver, witprog = segwit_addr.decode_segwit_address('bc', address)
    assert witprog is not None
    converted = segwit_addr.encode_segwit_address(constants.net.SEGWIT_HRP, witver, bytes(witprog))
    assert converted is not None
    return converted


def _ltc_p2pkh_from_bitcoin(address: str) -> str:
    """Re-encode a legacy Bitcoin P2PKH test vector using Litecoin's network byte."""
    _, hash160 = bitcoin.b58_address_to_hash160(address)
    return bitcoin.hash160_to_b58_address(hash160, constants.net.ADDRTYPE_P2PKH)


def _make_ltc_bolt11(*, amount: Decimal = None, fallback: str = None) -> str:
    tags = [('d', 'unit_test'), ('9', 33282)]
    if fallback is not None:
        tags.append(('f', fallback))
    lnaddr = LnAddr(
        date=1615922274,
        paymenthash=_RHASH,
        payment_secret=_PAYMENT_SECRET,
        amount=amount,
        tags=tags,
    )
    return lnencode(lnaddr, _PRIVKEY)


class WalletMock:
    def __init__(self, electrum_path):
        self.config = SimpleConfig({
            'electrum_path': electrum_path,
            'decimal_point': 5
        })
        self.contacts = None


class TestPaymentIdentifier(ElectrumTestCase):
    def setUp(self):
        super().setUp()
        self.wallet = WalletMock(self.electrum_path)

        self.config = SimpleConfig({
            'electrum_path': self.electrum_path,
            'decimal_point': 5
        })
        self.wallet2_path = os.path.join(self.electrum_path, "somewallet2")

    def test_maybe_extract_bech32_lightning_payment_identifier(self):
        bolt11 = _make_ltc_bolt11()
        lnurl = "lnurl1dp68gurn8ghj7um9wfmxjcm99e5k7telwy7nxenrxvmrgdtzxsenjcm98pjnwxq96s9"
        self.assertEqual(bolt11, maybe_extract_bech32_lightning_payment_identifier(f"{bolt11}".upper()))
        self.assertEqual(bolt11, maybe_extract_bech32_lightning_payment_identifier(f"lightning:{bolt11}"))
        self.assertEqual(bolt11, maybe_extract_bech32_lightning_payment_identifier(f"  lightning:{bolt11}   ".upper()))
        self.assertEqual(lnurl, maybe_extract_bech32_lightning_payment_identifier(lnurl))
        self.assertEqual(lnurl, maybe_extract_bech32_lightning_payment_identifier(f"  lightning:{lnurl}   ".upper()))

        self.assertEqual(None, maybe_extract_bech32_lightning_payment_identifier(f"bitcoin:{bolt11}"))
        self.assertEqual(None, maybe_extract_bech32_lightning_payment_identifier(f":{bolt11}"))
        self.assertEqual(None, maybe_extract_bech32_lightning_payment_identifier(f"garbage text"))

    def test_remove_uri_prefix(self):
        lightning, bitcoin_scheme = 'lightning', 'bitcoin'
        tests = (
            (lightning, '', ''),
            (lightning, 'lightning:test', 'test'),
            (lightning, 'bitcoin:test', 'bitcoin:test'),
            (lightning, 'lightningtest', 'lightningtest'),
            (lightning, 'lightning test', 'lightning test'),
            (bitcoin_scheme, 'lightning:test', 'lightning:test'),
            (bitcoin_scheme, 'bitcoin:test', 'test'),
            (bitcoin_scheme, 'bitcoin', 'bitcoin'),
            (bitcoin_scheme, 'bitcoin:', ''),
        )
        for prefix, input_str, expected_output_str in tests:
            output_str = remove_uri_prefix(input_str, prefix=prefix)
            self.assertEqual(expected_output_str, output_str, msg=output_str)
        with self.assertRaises(AssertionError):
            remove_uri_prefix(data=1234, prefix="test")

    def test_bolt11(self):
        # Native Litecoin invoice, no amount and no fallback address.
        bolt11 = _make_ltc_bolt11()
        for pi_str in [
            f'{bolt11}',
            f'  {bolt11}',
            f'{bolt11}  ',
            f'lightning:{bolt11}',
            f'  lightning:{bolt11}',
            f'lightning:{bolt11}  ',
            f'lightning:{bolt11.upper()}',
            f'lightning:{bolt11}'.upper(),
        ]:
            pi = PaymentIdentifier(None, pi_str)
            self.assertTrue(pi.is_valid())
            self.assertEqual(PaymentIdentifierType.BOLT11, pi.type)
            self.assertFalse(pi.is_amount_locked())
            self.assertFalse(pi.is_error())
            self.assertIsNotNone(pi.bolt11)

        for pi_str in [
            f'lightning:  {bolt11}',
            f'bitcoin:{bolt11}'
        ]:
            pi = PaymentIdentifier(None, pi_str)
            self.assertFalse(pi.is_valid())

        # Native Litecoin invoice with amount and Litecoin fallback address.
        fallback = _ltc_p2pkh_from_bitcoin('1RustyRX2oai4EYYDpQGWvEL62BBGqN9T')
        bolt_11_w_fallback = _make_ltc_bolt11(amount=Decimal('0.02'), fallback=fallback)
        pi = PaymentIdentifier(None, bolt_11_w_fallback)
        self.assertTrue(pi.is_valid())
        self.assertEqual(PaymentIdentifierType.BOLT11, pi.type)
        self.assertIsNotNone(pi.bolt11)
        self.assertTrue(pi.is_lightning())
        self.assertTrue(pi.is_onchain())
        self.assertTrue(pi.is_amount_locked())

        self.assertFalse(pi.is_error())
        self.assertFalse(pi.need_resolve())
        self.assertFalse(pi.need_finalize())
        self.assertFalse(pi.is_multiline())

    def test_bip21(self):
        address1 = _ltc_bech32_from_bitcoin('bc1qj3zx2zc4rpv3npzmznxhdxzn0wm7pzqp8p2293')
        address2 = _ltc_bech32_from_bitcoin('bc1qy7ps80x5csdqpfcekn97qfljxtg2lrya8826ds')
        legacy_address = _ltc_p2pkh_from_bitcoin('1RustyRX2oai4EYYDpQGWvEL62BBGqN9T')

        bip21 = f'litecoin:{address1}?message=unit_test'
        for pi_str in [
            f'{bip21}',
            f'  {bip21}',
            f'{bip21}  ',
            f'{bip21}'.upper(),
        ]:
            pi = PaymentIdentifier(None, pi_str)
            self.assertTrue(pi.is_available())
            self.assertFalse(pi.is_lightning())
            self.assertTrue(pi.is_onchain())
            self.assertIsNotNone(pi.bip21)

        # amount, expired, message
        bip21 = f'litecoin:{address2}?amount=0.001&message=unit_test&time=1707382023&exp=3600'

        pi = PaymentIdentifier(None, bip21)
        self.assertTrue(pi.is_available())
        self.assertFalse(pi.is_lightning())
        self.assertTrue(pi.is_onchain())
        self.assertIsNotNone(pi.bip21)

        self.assertTrue(pi.has_expired())
        self.assertEqual('unit_test', pi.bip21.get('message'))

        # amount, expired, message, lightning with matching amount
        bolt11 = _make_ltc_bolt11(amount=Decimal('0.02'), fallback=legacy_address)
        bip21 = f'litecoin:{legacy_address}?amount=0.02&message=unit_test&time=1707382023&exp=3600&lightning={bolt11}'

        pi = PaymentIdentifier(None, bip21)
        self.assertTrue(pi.is_available())
        self.assertTrue(pi.is_lightning())
        self.assertTrue(pi.is_onchain())
        self.assertIsNotNone(pi.bip21)
        self.assertIsNotNone(pi.bolt11)

        self.assertTrue(pi.has_expired())
        self.assertEqual('unit_test', pi.bip21.get('message'))

        # amount, expired, message, lightning with non-matching amount
        bip21 = f'litecoin:{legacy_address}?amount=0.01&message=unit_test&time=1707382023&exp=3600&lightning={bolt11}'

        pi = PaymentIdentifier(None, bip21)
        self.assertFalse(pi.is_valid())

        # amount bounds for Litecoin
        bip21 = f'litecoin:{legacy_address}?amount=-1'
        pi = PaymentIdentifier(None, bip21)
        self.assertFalse(pi.is_valid())

        bip21 = f'litecoin:{legacy_address}?amount=84000001'
        pi = PaymentIdentifier(None, bip21)
        self.assertFalse(pi.is_valid())

        bip21 = f'litecoin:{legacy_address}?amount=0'
        pi = PaymentIdentifier(None, bip21)
        self.assertFalse(pi.is_valid())

    def test_lnurl_basic(self):
        """Test basic LNURL parsing without resolve"""
        valid_lnurl = 'lnurl1dp68gurn8ghj7um9wfmxjcm99e5k7telwy7nxenrxvmrgdtzxsenjcm98pjnwxq96s9'
        pi = PaymentIdentifier(None, valid_lnurl)
        self.assertTrue(pi.is_valid())
        self.assertEqual(PaymentIdentifierType.LNURL, pi.type)
        self.assertFalse(pi.is_available())
        self.assertTrue(pi.need_resolve())
        self.assertEqual(PaymentIdentifierState.NEED_RESOLVE, pi.state)

        # Test with lightning: prefix
        lightning_lnurl = f'lightning:{valid_lnurl}'
        pi = PaymentIdentifier(None, lightning_lnurl)
        self.assertTrue(pi.is_valid())
        self.assertEqual(PaymentIdentifierType.LNURL, pi.type)
        self.assertTrue(pi.need_resolve())

    @patch('electrum.payment_identifier.request_lnurl')
    def test_lnurl_pay_resolve(self, mock_request_lnurl):
        """Test LNURL-pay (LNURL6) with mocked resolve"""
        valid_lnurl = 'LNURL1DP68GURN8GHJ7MRWVF5HGUEWD3HXZERYWFJHXUEWVDHK6TMVDE6HYMRS9ANRV46DXETQPJQCS4'

        mock_lnurl6_data = LNURL6Data(
            callback_url='https://example.com/lnurl-pay',
            max_sendable_sat=1_000_000,
            min_sendable_sat=1_000,
            metadata_plaintext='Test payment',
            comment_allowed=100,
        )
        mock_request_lnurl.return_value = mock_lnurl6_data

        pi = PaymentIdentifier(None, valid_lnurl)
        self.assertTrue(pi.need_resolve())
        self.assertEqual(PaymentIdentifierType.LNURL, pi.type)

        async def run_resolve():
            await pi._do_resolve()

        asyncio.run(run_resolve())

        self.assertEqual(PaymentIdentifierType.LNURLP, pi.type)
        self.assertEqual(PaymentIdentifierState.LNURLP_FINALIZE, pi.state)
        self.assertTrue(pi.need_finalize())
        self.assertIsNotNone(pi.lnurl_data)
        self.assertTrue(isinstance(pi.lnurl_data, LNURL6Data))
        self.assertEqual(1_000, pi.lnurl_data.min_sendable_sat)
        self.assertEqual(1_000_000, pi.lnurl_data.max_sendable_sat)
        self.assertEqual('Test payment', pi.lnurl_data.metadata_plaintext)
        self.assertEqual(100, pi.lnurl_data.comment_allowed)

    @patch('electrum.payment_identifier.request_lnurl')
    def test_lnurl_withdraw_resolve(self, mock_request_lnurl):
        """Test LNURL-withdraw (LNURL3) with mocked resolve"""
        valid_lnurl = 'LNURL1DP68GURN8GHJ7MRWVF5HGUEWD3HXZERYWFJHXUEWVDHK6TM4WPNHYCTYV4EJ7DFCVGENSDPH8QCRZETXVGCXGCMPVFJR' \
                        'WENP8P3NJEP3XE3NQWRPXFJR2VRRVSCX2V33V5UNVC3SXP3RXCFSVFSKVWPCV3SKZWTP8YUZ7AMFW35XGUNPWUHKZURF9AMRZT' \
                        'MVDE6HYMP0FETHVUNZDAMHQ7JSF4RX73TZ2VU9Z3J3GVMSLCJ57F'

        mock_lnurl3_data = LNURL3Data(
            callback_url='https://example.com/lnurl-withdraw',
            k1='test-k1-value',
            default_description='Test withdrawal',
            min_withdrawable_sat=1_000,
            max_withdrawable_sat=500_000,
        )
        mock_request_lnurl.return_value = mock_lnurl3_data

        pi = PaymentIdentifier(None, valid_lnurl)
        self.assertTrue(pi.need_resolve())
        self.assertEqual(PaymentIdentifierType.LNURL, pi.type)

        async def run_resolve():
            await pi._do_resolve()

        asyncio.run(run_resolve())

        self.assertEqual(PaymentIdentifierType.LNURLW, pi.type)
        self.assertEqual(PaymentIdentifierState.LNURLW_FINALIZE, pi.state)
        self.assertIsNotNone(pi.lnurl_data)
        self.assertEqual('test-k1-value', pi.lnurl_data.k1)
        self.assertEqual('Test withdrawal', pi.lnurl_data.default_description)
        self.assertEqual(1000, pi.lnurl_data.min_withdrawable_sat)
        self.assertEqual(500000, pi.lnurl_data.max_withdrawable_sat)

    @patch('electrum.payment_identifier.request_lnurl')
    def test_lnurl_resolve_error(self, mock_request_lnurl):
        """Test LNURL resolve error handling"""
        lnurl = 'LNURL1DP68GURN8GHJ7MRWVF5HGUEWD3HXZERYWFJHXUEWVDHK6TM4WPNHYCTYV4EJ7DFCVGENSDPH8QCRZETXVGCXGCMPVFJR' \
                  'WENP8P3NJEP3XE3NQWRPXFJR2VRRVSCX2V33V5UNVC3SXP3RXCFSVFSKVWPCV3SKZWTP8YUZ7AMFW35XGUNPWUHKZURF9AMRZT' \
                  'MVDE6HYMP0FETHVUNZDAMHQ7JSF4RX73TZ2VU9Z3J3GVMSLCJ57F'

        mock_request_lnurl.side_effect = LNURLError("Server error")

        pi = PaymentIdentifier(None, lnurl)
        self.assertTrue(pi.need_resolve())

        async def run_resolve():
            await pi._do_resolve()

        asyncio.run(run_resolve())

        self.assertEqual(PaymentIdentifierState.ERROR, pi.state)
        self.assertTrue(pi.is_error())
        self.assertIn("Server error", pi.get_error())

    def test_multiline(self):
        addr1 = _ltc_bech32_from_bitcoin('bc1qj3zx2zc4rpv3npzmznxhdxzn0wm7pzqp8p2293')
        addr2 = _ltc_bech32_from_bitcoin('bc1q66ex4c3vek4cdmrfjxtssmtguvs3r30pf42jpj')
        addr3 = _ltc_bech32_from_bitcoin('bc1qy7ps80x5csdqpfcekn97qfljxtg2lrya8826ds')

        pi_str = '\n'.join([
            f'{addr1},0.01',
            f'{addr2},0.01',
        ])
        pi = PaymentIdentifier(self.wallet, pi_str)
        self.assertTrue(pi.is_valid())
        self.assertTrue(pi.is_multiline())
        self.assertFalse(pi.is_multiline_max())
        self.assertIsNotNone(pi.multiline_outputs)
        self.assertEqual(2, len(pi.multiline_outputs))
        self.assertTrue(all(lambda x: isinstance(x, PartialTxOutput) for x in pi.multiline_outputs))
        self.assertEqual(1000, pi.multiline_outputs[0].value)
        self.assertEqual(1000, pi.multiline_outputs[1].value)

        pi_str = '\n'.join([
            f'{addr1},0.01',
            f'{addr2},0.01',
            f'{addr3},!',
        ])
        pi = PaymentIdentifier(self.wallet, pi_str)
        self.assertTrue(pi.is_valid())
        self.assertTrue(pi.is_multiline())
        self.assertTrue(pi.is_multiline_max())
        self.assertIsNotNone(pi.multiline_outputs)
        self.assertEqual(3, len(pi.multiline_outputs))
        self.assertTrue(all(lambda x: isinstance(x, PartialTxOutput) for x in pi.multiline_outputs))
        self.assertEqual(1000, pi.multiline_outputs[0].value)
        self.assertEqual(1000, pi.multiline_outputs[1].value)
        self.assertEqual('!', pi.multiline_outputs[2].value)

        pi_str = '\n'.join([
            f'{addr1},0.01',
            f'{addr2},2!',
            f'{addr3},3!',
        ])
        pi = PaymentIdentifier(self.wallet, pi_str)
        self.assertTrue(pi.is_valid())
        self.assertTrue(pi.is_multiline())
        self.assertTrue(pi.is_multiline_max())
        self.assertIsNotNone(pi.multiline_outputs)
        self.assertEqual(3, len(pi.multiline_outputs))
        self.assertTrue(all(lambda x: isinstance(x, PartialTxOutput) for x in pi.multiline_outputs))
        self.assertEqual(1000, pi.multiline_outputs[0].value)
        self.assertEqual('2!', pi.multiline_outputs[1].value)
        self.assertEqual('3!', pi.multiline_outputs[2].value)

        pi_str = '\n'.join([
            f'{addr1},0.01',
            'script(OP_RETURN baddc0ffee),0'
        ])
        pi = PaymentIdentifier(self.wallet, pi_str)
        self.assertTrue(pi.is_valid())
        self.assertTrue(pi.is_multiline())
        self.assertIsNotNone(pi.multiline_outputs)
        self.assertEqual(2, len(pi.multiline_outputs))
        self.assertTrue(all(lambda x: isinstance(x, PartialTxOutput) for x in pi.multiline_outputs))
        self.assertEqual(1000, pi.multiline_outputs[0].value)
        self.assertEqual(0, pi.multiline_outputs[1].value)

    def test_spk(self):
        address = _ltc_bech32_from_bitcoin('bc1qj3zx2zc4rpv3npzmznxhdxzn0wm7pzqp8p2293')
        for pi_str in [
            f'{address}',
            f'  {address}',
            f'{address}  ',
            f'{address}'.upper(),
        ]:
            pi = PaymentIdentifier(None, pi_str)
            self.assertTrue(pi.is_valid())
            self.assertTrue(pi.is_available())

        spk = 'script(OP_RETURN baddc0ffee)'
        for pi_str in [
            f'{spk}',
            f'  {spk}',
            f'{spk}  ',
        ]:
            pi = PaymentIdentifier(None, pi_str)
            self.assertTrue(pi.is_valid())
            self.assertTrue(pi.is_available())

    def test_email_and_domain(self):
        # TODO resolve mock
        domain_pi_strings = (
            'some.domain',
            'some.weird.but.valid.domain',
            'lnltcsome.weird.but.valid.domain',
            'ltc1qsome.weird.but.valid.domain',
            'lnurlsome.weird.but.valid.domain',
        )
        for pi_str in domain_pi_strings:
            pi = PaymentIdentifier(None, pi_str)
            self.assertTrue(pi.is_valid())
            self.assertEqual(PaymentIdentifierType.DOMAINLIKE, pi.type)
            self.assertFalse(pi.is_available())
            self.assertTrue(pi.need_resolve())

        email_pi_strings = (
            'user@some.domain',
            'user@some.weird.but.valid.domain',
            'lnltcuser@some.domain',
            'lnurluser@some.domain',
            'ltc1quser@some.domain',
            'lightning:user@some.domain',
            'lightning:user@some.weird.but.valid.domain',
            'lightning:lnltcuser@some.domain',
            'lightning:lnurluser@some.domain',
            'lightning:ltc1quser@some.domain',
        )
        for pi_str in email_pi_strings:
            pi = PaymentIdentifier(None, pi_str)
            self.assertTrue(pi.is_valid())
            self.assertEqual(PaymentIdentifierType.EMAILLIKE, pi.type)
            self.assertFalse(pi.is_available())
            self.assertTrue(pi.need_resolve())

    async def test_invoice_from_payment_identifier(self):
        legacy_address = _ltc_p2pkh_from_bitcoin('1RustyRX2oai4EYYDpQGWvEL62BBGqN9T')
        bolt11_amount = _make_ltc_bolt11(amount=Decimal('0.02'), fallback=legacy_address)

        # amount, expired, message, lightning with matching amount
        bip21 = f'litecoin:{legacy_address}?amount=0.02&message=unit_test&time=1707382023&exp=3600&lightning={bolt11_amount}'

        pi = PaymentIdentifier(None, bip21)
        invoice = invoice_from_payment_identifier(pi, None, None)
        self.assertTrue(isinstance(invoice, Invoice))
        self.assertTrue(invoice.is_lightning())
        self.assertEqual(2_000_000_000, invoice.amount_msat)

        text = 'bitter grass shiver impose acquire brush forget axis eager alone wine silver'
        d = restore_wallet_from_text__for_unittest(text, path=self.wallet2_path, config=self.config)
        wallet2 = d['wallet']

        # no amount bip21+lightning, MAX amount passed
        bolt11_no_amount = _make_ltc_bolt11()
        bip21 = f'litecoin:{legacy_address}?message=unit_test&time=1707382023&exp=3600&lightning={bolt11_no_amount}'
        pi = PaymentIdentifier(None, bip21)
        invoice = invoice_from_payment_identifier(pi, wallet2, '!')
        self.assertTrue(isinstance(invoice, Invoice))
        self.assertFalse(invoice.is_lightning())

        # no amount lightning, MAX amount passed -> expect raise
        pi = PaymentIdentifier(None, f'lightning:{bolt11_no_amount}')
        with self.assertRaises(AssertionError):
            invoice_from_payment_identifier(pi, wallet2, '!')
        invoice = invoice_from_payment_identifier(pi, wallet2, 1)
        self.assertEqual(1000, invoice.amount_msat)
