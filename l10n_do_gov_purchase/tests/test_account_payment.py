from odoo import tools
from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource


class AccountPaymentTest(TransactionCase):
    def _load(self, module, *args):
        tools.convert_file(
            self.cr,
            "l10n_do_gov_purchase",
            get_module_resource(module, *args),
            {},
            "init",
            False,
            "test",
            self.registry._assertion_report,
        )

    def setUp(self):
        super(AccountPaymentTest, self).setUp()

        # Minimal accounting setup
        self._load("account", "test", "account_minimal_test.xml")

        self.account_payment_obj = self.env["account.payment"]
        self.account_register_payment_obj = self.env["account.register.payments"]
        self.account_invoice_obj = self.env["account.invoice"]
        journal_obj = self.env["account.journal"]
        account_id = self.env.ref("l10n_do_gov_purchase.a_sale")

        # Accounting setup
        self.bank_journal = journal_obj.create(
            {"name": "Bank 123456", "code": "BNK67", "type": "bank"}
        )

        journal_ids = journal_obj.search([("type", "in", ("bank", "cash"))])
        journal_ids.write({"allow_check_release": True})

        # Create partner
        partner = self.env["res.partner"].create({"name": "Jimmy"})

        # Create invoice
        self.invoice_id = self.account_invoice_obj.create(
            {
                "type": "out_invoice",
                "partner_id": partner.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.env.ref("product.product_product_4").id,
                            "quantity": 1,
                            "name": "text",
                            "account_id": account_id.id,
                            "price_unit": 110.0,
                        },
                    )
                ],
            }
        )
        self.invoice_id.action_invoice_open()

    def test_001_account_payment(self):
        """
        Check that when making a payment it is saved in account payment
        """
        # Creating wizard account payment
        payment_id = self.account_payment_obj.with_context(
            active_ids=self.invoice_id.ids
        ).create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "payment_method_id": self.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
                "amount": 80,
                "payment_date": "2020-07-15",
                "journal_id": self.bank_journal.id,
                "release_number": "333",
            }
        )
        # Validate payment
        payment_id.post()

        # Check new payment has correct release_number
        payment = self.account_payment_obj.search(
            [("journal_id", "=", self.bank_journal.id)]
        )
        self.assertEqual(payment.release_number, "333")

    def test_002_account_register_payment(self):
        """
        Check that a payment has been created from outside the
        invoice and that it has been saved in the account payment
        """

        # Register invoice payment
        register_payments = self.account_register_payment_obj.with_context(
            active_model="account.invoice", active_ids=self.invoice_id.ids
        ).create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "payment_method_id": self.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
                "amount": 80,
                "payment_date": "2020-07-15",
                "journal_id": self.bank_journal.id,
                "release_number": "777",
            }
        )

        # Validate payment
        register_payments.create_payments()

        # Check new payment has correct release_number
        payment = self.account_payment_obj.search(
            [("journal_id", "=", self.bank_journal.id)]
        )
        self.assertEqual(payment.release_number, "777")
