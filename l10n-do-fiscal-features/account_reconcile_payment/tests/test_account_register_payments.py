from odoo import fields

from . import common
from odoo.tests import tagged


@tagged("post_install")
class AccountRegisterPaymentsTestCommon(common.AccountRegisterPaymentsTestCommon):
    def test_001_reconcile_payments(self):

        # Vendor bills
        invoice_1 = self._create_l10n_do_invoice(
            data={
                "document_number": "B0100000001",
                "invoice_date": fields.Date.today(),
                "expense_type": "02",
                "journal": self.purchase_journal.id,
            },
            invoice_type="in_invoice",
        )
        invoice_2 = self._create_l10n_do_invoice(
            data={
                "document_number": "B0100000002",
                "invoice_date": fields.Date.today(),
                "expense_type": "02",
                "journal": self.purchase_journal.id,
            },
            invoice_type="in_invoice",
        )

        # Merge invoices in one recordset
        invoices = self.env["account.move"].browse([invoice_1.id, invoice_2.id])

        # Merge taxes in one recordset
        taxes = self.env["account.tax"].browse(
            [self.ret_100_itbis.id, self.ret_10_isr.id]
        )

        # Validate invoices
        invoices._post()

        # Launch register payments wizard
        register_payments = (
            self.env["account.payment.register"]
            .with_context(
                active_model="account.move",
                active_ids=invoices.ids,
                default_journal_id=self.bank_journal.id,
                default_amount=sum([i.amount_total for i in invoices]),
            )
            .create({})
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

        payment_id = self.env["account.payment"].search(
            [
                ("journal_id", "=", self.bank_journal.id),
                ("partner_id", "=", self.fiscal_partner.id),
            ],
            limit=1,
        )

        # Check payment amount
        self.assertEqual(
            payment_id.amount, register_payments.amount, "Wrong payment amount"
        )

        move_id = self.env["account.move"].search(
            [("journal_id", "=", self.misc_journal.id)], limit=1
        )

        # Check Journal entry was created
        assert move_id, "No Reconciliation move created"

        expected_vals = [
            {
                "account_id": self.env["account.account"]
                .search(
                    [("code", "=", "21030202"), ("company_id", "=", self.do_company.id)]
                )
                .id,
                "credit": 18.0,
                "debit": 0.0,
                "name": "Retención 100% ITBIS Servicios a Físicas (R293-11)",
            },
            {
                "account_id": self.env["account.account"]
                .search(
                    [("code", "=", "21010200"), ("company_id", "=", self.do_company.id)]
                )
                .id,
                "credit": 0.0,
                "debit": 18.0,
                "name": "Retención 100% ITBIS Servicios a Físicas (R293-11)",
            },
            {
                "account_id": self.env["account.account"]
                .search(
                    [("code", "=", "21030301"), ("company_id", "=", self.do_company.id)]
                )
                .id,
                "credit": 10.0,
                "debit": 0.0,
                "name": "Retención 10% ISR Honorarios a Físicas",
            },
            {
                "account_id": self.env["account.account"]
                .search(
                    [("code", "=", "21010200"), ("company_id", "=", self.do_company.id)]
                )
                .id,
                "credit": 0.0,
                "debit": 10.0,
                "name": "Retención 10% ISR Honorarios a Físicas",
            },
            {
                "account_id": self.env["account.account"]
                .search(
                    [("code", "=", "21030202"), ("company_id", "=", self.do_company.id)]
                )
                .id,
                "credit": 18.0,
                "debit": 0.0,
                "name": "Retención 100% ITBIS Servicios a Físicas (R293-11)",
            },
            {
                "account_id": self.env["account.account"]
                .search(
                    [("code", "=", "21010200"), ("company_id", "=", self.do_company.id)]
                )
                .id,
                "credit": 0.0,
                "debit": 18.0,
                "name": "Retención 100% ITBIS Servicios a Físicas (R293-11)",
            },
            {
                "account_id": self.env["account.account"]
                .search(
                    [("code", "=", "21030301"), ("company_id", "=", self.do_company.id)]
                )
                .id,
                "credit": 10.0,
                "debit": 0.0,
                "name": "Retención 10% ISR Honorarios a Físicas",
            },
            {
                "account_id": self.env["account.account"]
                .search(
                    [("code", "=", "21010200"), ("company_id", "=", self.do_company.id)]
                )
                .id,
                "credit": 0.0,
                "debit": 10.0,
                "name": "Retención 10% ISR Honorarios a Físicas",
            },
        ]

        # # Check Journal entry lines values
        self.assertRecordValues(move_id.line_ids, expected_vals)
