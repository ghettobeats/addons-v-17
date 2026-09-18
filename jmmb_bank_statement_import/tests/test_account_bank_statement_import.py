import xlrd
import base64

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.modules.module import get_module_resource

from .stmt_lines import (
    stmt_lines,
    stmt_balance_end_real,
    stmt_balance_start,
    stmt_currency_code,
)


@tagged("post_install", "-at_install")
class AccountBankStatementImportTest(AccountTestInvoicingCommon):
    def test_001_jmmb_statement_import(self):
        """
        Check jmmb statement file is processed correctly
        """

        # File Test Call
        jmmb_file_path = get_module_resource(
            "jmmb_bank_statement_import", "jmmb_stmt_file", "jmmb_statement.xls"
        )

        jmmb_file = base64.b64encode(open(jmmb_file_path, "rb").read())

        # Journal
        bank_journal = self.env["account.journal"].create(
            {"name": "Bank 123456", "code": "BNK67", "type": "bank"}
        )

        # Checking whether the journal company's currency_id is different
        # from the file's  currency_id
        # in which case the journal currency_id is set to the one
        # in file
        #
        # as the bank_statement_import module
        # takes the currency_id of the user's company
        # when no currency_id is specified in the journal
        # which can lead to wrong currency on statements
        dop_currency_id = self.env.ref("base.DOP")
        if bank_journal.company_id.currency_id != dop_currency_id:
            bank_journal.write({"currency_id": dop_currency_id.id})

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "jmmb_stmt.xls", "datas": jmmb_file})
                    ]
                }
            )
        )

        import_wizard.import_file()

        statement_id = self.env["account.bank.statement"].search(
            [("journal_id", "=", bank_journal.id)]
        )

        self.assertEqual(
            round(statement_id.balance_start, 2),
            stmt_balance_start,
            "wrong balance start on statement",
        )
        self.assertEqual(
            round(statement_id.balance_end_real, 2),
            stmt_balance_end_real,
            "wong balance end real on statement",
        )
        self.assertEqual(
            statement_id.currency_id.name,
            stmt_currency_code,
            "wrong currency name on statement",
        )

        for stmt_line in stmt_lines:
            stmt_line["date"] = fields.Date.from_string(stmt_line["date"])

        self.assertRecordValues(statement_id.line_ids.sorted("id"), stmt_lines)

    def test_002_jmmb_statement_file_validation(self):
        """
        Check jmmb file format validation works correctly
        """

        jmmb_file_path = get_module_resource(
            "jmmb_bank_statement_import", "jmmb_stmt_file", "jmmb_statement.xls"
        )
        jmmb_file = xlrd.open_workbook(jmmb_file_path)
        self.assertTrue(
            self.env["account.bank.statement.import"]._is_jmmb_file(jmmb_file)
        )

        bad_jmmb_file_path = get_module_resource(
            "jmmb_bank_statement_import", "jmmb_stmt_file", "bad_jmmb_statement.xls"
        )
        bad_jmmb_file = xlrd.open_workbook(bad_jmmb_file_path)
        self.assertFalse(
            self.env["account.bank.statement.import"]._is_jmmb_file(bad_jmmb_file)
        )

    def test_003_jmmb_statement_in_state_open(self):
        """
        Check jmmb statement file is passed to the "Open" state
        """

        jmmb_file_path = get_module_resource(
            "jmmb_bank_statement_import", "jmmb_stmt_file", "jmmb_statement.xls"
        )

        jmmb_file = base64.b64encode(open(jmmb_file_path, "rb").read())

        # Journal
        bank_journal = self.env["account.journal"].create(
            {"name": "Bank 123456", "code": "BNK67", "type": "bank"}
        )

        # Checking whether the journal company's currency_id is different
        # from the file's  currency_id
        # in which case the journal currency_id is set to the one
        # in file
        #
        # as the bank_statement_import module
        # takes the currency_id of the user's company
        # when no currency_id is specified in the journal
        # which can lead to wrong currency on statements
        dop_currency_id = self.env.ref("base.DOP")
        if bank_journal.company_id.currency_id != dop_currency_id:
            bank_journal.write({"currency_id": dop_currency_id.id})

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "jmmb_stmt.xls", "datas": jmmb_file})
                    ]
                }
            )
        )

        bank_journal.company_id.create_statement_draft = True

        import_wizard.import_file()

        statement_id = self.env["account.bank.statement"].search(
            [("journal_id", "=", bank_journal.id),
             ("state", "=", "open")]
        )

        self.assertTrue(statement_id)
        self.assertFalse(statement_id.state != "open")
