from odoo.tests import tagged
from odoo.addons.l10n_do_accounting.tests.common import L10nDOTestsCommon


@tagged("external_l10n", "post_install", "-at_install", "-standard", "external")
class AccountRegisterPaymentsTestCommon(L10nDOTestsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_do.do_chart_template"):
        super(AccountRegisterPaymentsTestCommon, cls).setUpClass(
            chart_template_ref=chart_template_ref
        )

        # Journals
        cls.purchase_journal = cls.env["account.journal"].search(
            [("company_id", "=", cls.do_company.id), ("type", "=", "purchase")], limit=1
        )
        cls.bank_journal = cls.env["account.journal"].search(
            [("company_id", "=", cls.do_company.id), ("type", "=", "bank")], limit=1
        )
        cls.bank_journal_2 = cls.bank_journal.copy(
            {"name": "Bank", "type": "bank", "code": "BNK02"}
        )
        cls.misc_journal = (
            cls.env["account.journal"]
            .search(
                [("company_id", "=", cls.do_company.id), ("type", "=", "general")],
                limit=1,
            )
            .copy(
                {
                    "l10n_do_reconciled_payments_journal": True,
                    "name": "Withholding Journal",
                    "code": "WH01",
                }
            )
        )

        # Taxes
        cls.ret_100_itbis = cls.env.ref(
            "l10n_do.%s_ret_100_tax_person" % cls.do_company.id
        )
        cls.ret_10_isr = cls.env.ref(
            "l10n_do.%s_ret_10_income_person" % cls.do_company.id
        )

        # Payment stuffs
        cls.payment_method_manual_out = cls.env.ref(
            "account.account_payment_method_manual_out"
        )
        cls._get_tax_account = cls.env["account.payment.register"]._get_tax_account
        cls._get_invoice_reconcile_move_account = cls.env[
            "account.payment.register"
        ]._get_invoice_reconcile_move_account
