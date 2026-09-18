from odoo import fields
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class AccountRegisterPaymentsTest(AccountTestInvoicingCommon):
    def setUp(self):
        super(AccountRegisterPaymentsTest, self).setUp()
        # Objects
        self.tax_obj = self.env["account.tax"]
        self.tax_group_obj = self.env["account.tax.group"]
        self.journal_obj = self.env["account.journal"]
        self.account_obj = self.env["account.account"]
        self.invoice_obj = self.env["account.move"]
        self.payment_obj = self.env["account.payment"]
        self.move_obj = self.invoice_obj
        self.register_payments_obj = self.env["account.payment.register"]

        # Helper function
        self._get_invoice_reconcile_move_account = (
            self.register_payments_obj._get_invoice_reconcile_move_account
        )
        self._get_tax_account = self.register_payments_obj._get_tax_account

        # Payment stuffs
        self.payment_method_manual_out = self.env.ref(
            "account.account_payment_method_manual_out"
        )

        # Journals
        self.bank_journal = self.journal_obj.create(
            {"name": "Bank", "type": "bank", "code": "BNK01"}
        )
        self.bank_journal_2 = self.journal_obj.create(
            {"name": "Bank", "type": "bank", "code": "BNK02"}
        )
        self.misc_journal = self.journal_obj.create(
            {
                "name": "Withholding",
                "type": "general",
                "code": "WH001",
                "l10n_do_reconciled_payments_journal": True,
            }
        )

        # Accounts
        self.account_1 = self.account_obj.create(
            {
                "code": "xxxxxxx1",
                "name": "ITBIS Retenido",
                "user_type_id": self.ref(
                    "account.data_account_type_non_current_liabilities"
                ),
            }
        )
        self.account_2 = self.account_obj.create(
            {
                "code": "xxxxxxx2",
                "name": "ISR Retenido",
                "user_type_id": self.ref(
                    "account.data_account_type_non_current_liabilities"
                ),
            }
        )
        self.account_3 = self.account_obj.create(
            {
                "code": "xxxxxxx3",
                "name": "Costos de Bienes",
                "user_type_id": self.ref("account.data_account_type_direct_costs"),
            }
        )
        self.account_4 = self.account_obj.create(
            {
                "code": "xxxxxxx4",
                "name": "ITBIS por Venta Bienes",
                "user_type_id": self.ref(
                    "account.data_account_type_non_current_liabilities"
                ),
            }
        )

        # Taxes
        tax_group_1 = self.tax_group_obj.create({"name": "ITBIS"})
        tax_group_2 = self.tax_group_obj.create({"name": "ISR"})
        self.tax_1 = self.tax_obj.create(
            {
                "name": "Retención 100% ITBIS",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": -18.0000,
                "invoice_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": self.account_1.id,
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": self.account_1.id,
                        },
                    ),
                ],
                "tax_group_id": tax_group_1.id,
            }
        )
        self.tax_2 = self.tax_obj.create(
            {
                "name": "Retención 10% ISR",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": -10.0000,
                "invoice_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": self.account_2.id,
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": self.account_2.id,
                        },
                    ),
                ],
                "tax_group_id": tax_group_2.id,
            }
        )
        self.tax_3 = self.tax_obj.create(
            {
                "name": "18% ITBIS",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 18.0000,
                "invoice_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": self.account_4.id,
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": self.account_4.id,
                        },
                    ),
                ],
                "tax_group_id": tax_group_1.id,
            }
        )
        self.tax_4 = self.tax_obj.create(
            {
                "name": "Exento ITBIS Compras ",
                "type_tax_use": "purchase",
                "amount_type": "percent",
                "amount": 0,
                "invoice_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": self.account_4.id,
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (0, 0, {"factor_percent": 100, "repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "tax",
                            "account_id": self.account_4.id,
                        },
                    ),
                ],
                "tax_group_id": tax_group_1.id,
            }
        )

        invoice_line_ids = [
            (
                0,
                0,
                {
                    "name": "Product 1",
                    "price_unit": 100.0,
                    "quantity": 1.0,
                    "account_id": self.account_3.id,
                    "tax_ids": [(6, 0, self.tax_3.ids)],
                },
            ),
            (
                0,
                0,
                {
                    "name": "Product 2",
                    "price_unit": 100.0,
                    "quantity": 1.0,
                    "account_id": self.account_3.id,
                    "tax_ids": [(6, 0, self.tax_4.ids)],
                },
            ),
        ]

        # Vendor bills
        self.invoice_1 = self.invoice_obj.create(
            {
                "move_type": "in_invoice",
                "partner_id": self.ref("base.res_partner_1"),
                "invoice_line_ids": invoice_line_ids,
                "l10n_latam_document_number": "B0100000001",
                "invoice_date": fields.Date.today(),
            }
        )
        self.invoice_2 = self.invoice_obj.create(
            {
                "move_type": "in_invoice",
                "partner_id": self.ref("base.res_partner_1"),
                "invoice_line_ids": invoice_line_ids,
                "l10n_latam_document_number": "B0100000002",
                "invoice_date": fields.Date.today(),
            }
        )

    def test_reconcile_payments(self):

        # Merge invoices in one recordset
        invoices = self.invoice_obj.browse([self.invoice_1.id, self.invoice_2.id])

        # Merge taxes in one recordset
        taxes = self.tax_obj.browse([self.tax_1.id, self.tax_2.id])

        # Validate invoices
        invoices._post()

        # Launch register payments wizard
        register_payments = self.register_payments_obj.with_context(
            active_model="account.move",
            active_ids=invoices.ids,
            default_journal_id=self.bank_journal.id,
            default_amount=sum([i.amount_total for i in invoices]),
        ).create(
            {
                "payment_method_id": self.payment_method_manual_out.id,
            }
        )

        # Turn on reconcile taxes features
        register_payments.l10n_do_reconcile_taxes = True
        register_payments.onchange_l10n_do_reconcile_taxes()
        register_payments._onchange_l10n_do_payments_invoice_ids()

        for line in register_payments.l10n_do_payments_invoice_ids:
            # Add taxes to invoices
            line.tax_ids = [(6, 0, taxes.ids)]
        register_payments._compute_amount()  # update payment amount

        # Validate payment
        register_payments._create_payments()

        self.assertEqual(
            set(invoices.mapped("payment_state")),
            {"in_payment"},
            "Not all bills were paid",
        )

        payment_id = self.payment_obj.search(
            [
                ("journal_id", "=", self.bank_journal.id),
                ("partner_id", "=", self.ref("base.res_partner_1")),
            ],
            limit=1,
        )

        # Check payment amount
        self.assertEqual(payment_id.amount, 380, "Wrong payment amount")

        move_id = self.move_obj.search(
            [("journal_id", "=", self.misc_journal.id)], limit=1
        )

        # Check Journal entry was created
        assert move_id, "No Reconciliation move created"

        expected_vals = [
            {
                "account_id": self._get_tax_account(self.tax_1),
                "credit": 36.0,
                "debit": 0.0,
                "name": self.tax_1.name,
            },
            {
                "account_id": self._get_invoice_reconcile_move_account(self.invoice_1),
                "credit": 0.0,
                "debit": 36.0,
                "name": self.tax_1.name,
            },
            {
                "account_id": self._get_tax_account(self.tax_2),
                "credit": 20.0,
                "debit": 0.0,
                "name": self.tax_2.name,
            },
            {
                "account_id": self._get_invoice_reconcile_move_account(self.invoice_1),
                "credit": 0.0,
                "debit": 20.0,
                "name": self.tax_2.name,
            },
            {
                "account_id": self._get_tax_account(self.tax_1),
                "credit": 36.0,
                "debit": 0.0,
                "name": self.tax_1.name,
            },
            {
                "account_id": self._get_invoice_reconcile_move_account(self.invoice_2),
                "credit": 0.0,
                "debit": 36.0,
                "name": self.tax_1.name,
            },
            {
                "account_id": self._get_tax_account(self.tax_2),
                "credit": 20.0,
                "debit": 0.0,
                "name": self.tax_2.name,
            },
            {
                "account_id": self._get_invoice_reconcile_move_account(self.invoice_2),
                "credit": 0.0,
                "debit": 20.0,
                "name": self.tax_2.name,
            },
        ]

        # Check Journal entry lines values
        self.assertRecordValues(move_id.line_ids, expected_vals)
