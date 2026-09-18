import base64

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.modules.module import get_module_resource

from .stmt_lines import stmt_lines


@tagged("post_install", "-at_install")
class AccountBankStatementImportTest(AccountTestInvoicingCommon):
    def test_001_bhd_statement_import(self):
        """
        Check BHD statement file is processed correctly
        """

        bhd_file_path = get_module_resource(
            "bhd_bank_statement_import", "bhd_stmt_file", "bhd_statement.csv"
        )
        bhd_file = base64.b64encode(open(bhd_file_path, "rb").read())

        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bhd_stmt.csv", "datas": bhd_file})
                    ]
                }
            )
        )

        import_wizard.with_context(skip_csv_check=True).import_file()

        statement_id = self.env["account.bank.statement"].search([("journal_id", "=", bank_journal.id)])

        for stmt_line in stmt_lines:
            stmt_line["date"] = fields.Date.from_string(stmt_line["date"])

        self.assertRecordValues(statement_id.line_ids.sorted("id"), stmt_lines)

    def test_002_bhd_statement_file_validation(self):
        """
        Check bhd file format validation works correctly
        """

        bhd_file_path = get_module_resource(
            "bhd_bank_statement_import", "bhd_stmt_file", "bad_bhd_statement.csv"
        )
        bhd_file = open(bhd_file_path, "rb").read()
        bhd_file = bhd_file.decode("latin1")

        self.assertFalse(
            self.env["account.bank.statement.import"]._is_bhd_file(bhd_file)
        )

    def test_003_bhd_statement_in_state_open(self):
        """
        Check bhd statement file is passed to the "Open" state
        """

        bhd_file_path = get_module_resource(
            "bhd_bank_statement_import", "bhd_stmt_file", "bhd_statement.csv"
        )
        bhd_file = base64.b64encode(open(bhd_file_path, "rb").read())

        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bhd_stmt.csv", "datas": bhd_file})
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
