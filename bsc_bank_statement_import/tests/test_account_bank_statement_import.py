import base64

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.modules.module import get_module_resource

from .stmt_lines import stmt_lines


@tagged("post_install", "-at_install")
class AccountBankStatementImportTest(AccountTestInvoicingCommon):
    def test_001_bsc_statement_import(self):
        """
        Check BSC statement file is processed correctly
        """

        bsc_file_path = get_module_resource(
            "bsc_bank_statement_import", "bsc_stmt_file", "bsc_stmt.csv"
        )
        bsc_file = base64.b64encode(open(bsc_file_path, "rb").read())

        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bsc_stmt.csv", "datas": bsc_file})
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

        self.assertRecordValues(statement_id.line_ids.sorted("id"), stmt_lines)

    def test_002_bsc_statement_file_validation(self):
        """
        Check bsc file format validation works correctly
        """

        bsc_file_path = get_module_resource(
            "bsc_bank_statement_import", "bsc_stmt_file", "bad_bsc_stmt.csv"
        )
        bsc_file = open(bsc_file_path, "r").read()
        self.assertFalse(
            self.env["account.bank.statement.import"]._is_bsc_file(bsc_file)
        )

    def test_003_bsc_statement_in_state_open(self):
        """
        Check bsc statement file is passed to the "Open" state
        """

        bsc_file_path = get_module_resource(
            "bsc_bank_statement_import", "bsc_stmt_file", "bsc_stmt.csv"
        )
        bsc_file = base64.b64encode(open(bsc_file_path, "rb").read())

        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bsc_stmt.csv", "datas": bsc_file})
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
