from odoo import fields
from odoo.tests.common import tagged, Form
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install")
class AccountPaymentWithholdingTest(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_do.do_chart_template"):
        super(AccountPaymentWithholdingTest, cls).setUpClass(
            chart_template_ref=chart_template_ref
        )

        cls.my_company = cls.company_data["company"]
        cls.my_company.write(
            {
                "currency_id": cls.env.ref("base.DOP").id,
                "name": "INDEXA SRL",
                "vat": "131793916",
                "country_id": cls.env.ref("base.do").id,
            }
        )

        # Objects
        cls.register_payments_obj = cls.env["account.payment.register"]
        cls.payment_obj = cls.env["account.payment"]
        cls.move_obj = cls.env["account.move"]

        # Setup withholding accounts
        cls.isr_account_acc = cls.env.ref(
            "l10n_do.%s_do_niif_21030301" % cls.my_company.id
        )
        cls.itbis_30_acc = cls.env.ref(
            "l10n_do.%s_do_niif_21030201" % cls.my_company.id
        )
        cls.isr_account_acc.is_l10n_do_withholding_account = True
        cls.itbis_30_acc.is_l10n_do_withholding_account = True

        # Payment stuffs
        cls.payment_method_manual_out = cls.env.ref(
            "account.account_payment_method_manual_out"
        )

        # Journals
        cls.bank_journal = cls.company_data["default_journal_bank"]
        cls.misc_journal = cls.company_data["default_journal_misc"]

        cls.invoice_1 = cls.init_invoice(
            move_type="in_invoice",
            partner=cls.env.ref("base.res_partner_4"),
            invoice_date=fields.Date.today(),
            post=False,
            products=[
                cls.env.ref("product.product_product_1"),
                cls.env.ref("product.product_product_2"),
                cls.env.ref("product.product_product_3"),
            ],
            amounts=[100, 200, 300],
        )

        cls.invoice_2 = cls.init_invoice(
            move_type="in_invoice",
            partner=cls.env.ref("base.res_partner_4"),
            invoice_date=fields.Date.today(),
            post=False,
            products=[
                cls.env.ref("product.product_product_1"),
                cls.env.ref("product.product_product_2"),
                cls.env.ref("product.product_product_3"),
            ],
            amounts=[100, 150, 250],
        )

        # The following shit is waiting for Odoo PR to be merged
        # https://github.com/odoo/odoo/pull/98613
        taxes = (
            cls.env.ref("l10n_do.%s_tax_18_purch" % cls.my_company.id)
            + cls.env.ref("l10n_do.%s_ret_30_tax_moral" % cls.my_company.id)
            + cls.env.ref("l10n_do.%s_ret_10_income_person" % cls.my_company.id)
        )
        invoice_2_form = Form(cls.invoice_2)
        with invoice_2_form.invoice_line_ids.new() as line_form:
            line_form.tax_ids.clear()
            for tax in taxes:
                line_form.tax_ids.add(tax)
        invoice_2_form.save()

    def test_001_l10n_do_withholding_type_payment(self):
        """
        Payment difference to withholding account
        """

        self.invoice_1._post()
        register_payment = self.register_payments_obj.with_context(
            active_model="account.move",
            active_ids=self.invoice_1.id,
            default_journal_id=self.bank_journal.id,
        ).create(
            {
                "payment_date": fields.Date.today(),
                # "payment_method_id": self.payment_method_manual_out.id,
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.invoice_1.partner_id.id,
                "amount": 549.72,
                "journal_id": self.bank_journal.id,
                "payment_difference_handling": "reconcile",
                "writeoff_account_id": self.isr_account_acc.id,
            }
        )
        register_payment._create_payments()

        payment_id = self.invoice_1._get_reconciled_info_JSON_values()[0][
            "account_payment_id"
        ]

        payment = self.payment_obj.browse(payment_id)

        self.assertTrue(payment.has_l10n_do_withholding)
        self.assertEqual(payment.l10n_do_withholding_type, "payment")

    def test_002_l10n_do_withholding_type_tax(self):
        """
        Withholding in invoice taxes
        """
        self.invoice_2._post()
        register_payment = self.register_payments_obj.with_context(
            active_model="account.move",
            active_ids=self.invoice_2.id,
            default_journal_id=self.bank_journal.id,
        ).create(
            {
                "payment_date": fields.Date.today(),
                # "payment_method_id": self.payment_method_manual_out.id,
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.env.ref("base.res_partner_4").id,
                "amount": self.invoice_2.amount_residual,
                "journal_id": self.bank_journal.id,
            }
        )
        register_payment._create_payments()

        payment_id = self.invoice_2._get_reconciled_info_JSON_values()[0][
            "account_payment_id"
        ]

        payment = self.payment_obj.browse(payment_id)

        self.assertTrue(payment.has_l10n_do_withholding)
        self.assertEqual(payment.l10n_do_withholding_type, "tax")

    def test_003_l10n_do_withholding_type_entry(self):
        """
        Journal entry withholding
        """
        self.invoice_1._post()

        move_journal_id = self.misc_journal.id

        payable_account_id = self.invoice_1.line_ids.filtered(
            lambda ml: ml.account_id.user_type_id.id
            == self.ref("account.data_account_type_payable")
            and ml.credit > 0
        )[0].account_id

        move_line_1 = {
            "name": "Retención ITBIS",
            "account_id": self.itbis_30_acc.id,
            "debit": 0.0,
            "credit": 32.4108,
            "journal_id": move_journal_id,
            "partner_id": self.invoice_1.partner_id.id,
        }
        move_line_2 = {
            "name": "Retención ITBIS",
            "account_id": payable_account_id.id,
            "debit": 32.4108,
            "credit": 0.0,
            "journal_id": move_journal_id,
            "partner_id": self.invoice_1.partner_id.id,
        }
        move_vals = {
            "ref": "Retenciones",
            "invoice_date": fields.Date.today(),
            "journal_id": move_journal_id,
            "line_ids": [(0, 0, move_line_1), (0, 0, move_line_2)],
            "move_type": "entry",
        }

        move = self.move_obj.create(move_vals)
        move._post()

        aml_id = move.line_ids.filtered(lambda ml: ml.debit > 0)
        self.invoice_1.js_assign_outstanding_line(aml_id.id)

        register_payment = self.register_payments_obj.with_context(
            active_model="account.move",
            active_ids=self.invoice_1.id,
            default_journal_id=self.bank_journal.id,
        ).create(
            {
                "payment_date": fields.Date.today(),
                # "payment_method_id": self.payment_method_manual_out.id,
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.invoice_1.partner_id.id,
                "amount": self.invoice_1.amount_residual,
                "journal_id": self.bank_journal.id,
            }
        )
        register_payment._create_payments()

        payment_id = [
            vals["account_payment_id"]
            for vals in self.invoice_1._get_reconciled_info_JSON_values()
            if vals["account_payment_id"]
        ][0]

        payment = self.payment_obj.browse(payment_id)

        self.assertTrue(payment.has_l10n_do_withholding)
        self.assertEqual(payment.l10n_do_withholding_type, "entry")
