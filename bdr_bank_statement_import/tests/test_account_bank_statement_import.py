import base64

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.modules.module import get_module_resource

from .stmt_lines import stmt_lines, stmt_balance_end_real, stmt_account_number


@tagged("post_install", "-at_install")
class AccountBankStatementImportTest(AccountTestInvoicingCommon):
    def test_001_bdr_statement_import(self):
        """
        Check bdr statement file is processed correctly
        """

        bdr_file_path = get_module_resource(
            "bdr_bank_statement_import", "bdr_stmt_file", "bdr_statement.csv"
        )
        bdr_file = base64.b64encode(open(bdr_file_path, "rb").read())

        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bdr_statement.csv", "datas": bdr_file})
                    ]
                }
            )
        )

        import_wizard.with_context(skip_csv_check=True).import_file()

        statement_id = self.env["account.bank.statement"].search(
            [("journal_id", "=", bank_journal.id)]
        )

        for stmt_line in stmt_lines:
            stmt_line["date"] = fields.Date.from_string(stmt_line["date"])
            stmt_line["account_number"] = stmt_account_number

        self.assertRecordValues(statement_id.line_ids.sorted("id"), stmt_lines)

    def get_reader(self, file_name):

        bdr_file_path = get_module_resource(
            "bdr_bank_statement_import", "bdr_stmt_file", file_name
        )
        bdr_file = open(bdr_file_path, "rb").read().decode("UTF-16").split("\r\n")
        return [x.split(",") for x in bdr_file]

    def test_002_bdr_statement_file_validation(self):
        """
        Check bdr file format validation works correctly
        """

        account_bank_statement_import = self.env["account.bank.statement.import"]

        self.assertTrue(
            account_bank_statement_import._is_bdr_file(
                self.get_reader("bdr_statement.csv")
            )
        )
        self.assertFalse(
            account_bank_statement_import._is_bdr_file(
                self.get_reader("bad_bdr_statement.csv")
            )
        )

    def test_003_bdr_statement_in_state_open(self):
        """
        Check bdr statement file is passed to the "Open" state
        """

        bdr_file_path = get_module_resource(
            "bdr_bank_statement_import", "bdr_stmt_file", "bdr_statement.csv"
        )
        bdr_file = base64.b64encode(open(bdr_file_path, "rb").read())

        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bdr_statement.csv", "datas": bdr_file})
                    ]
                }
            )
        )

        bank_journal.company_id.create_statement_draft = True

        import_wizard.with_context(skip_csv_check=True).import_file()

        statement_id = self.env["account.bank.statement"].search(
            [("journal_id", "=", bank_journal.id),
             ("state", "=", "open")]
        )

        self.assertTrue(statement_id)
        self.assertFalse(statement_id.state != "open")
