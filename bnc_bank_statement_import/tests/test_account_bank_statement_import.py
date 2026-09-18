import base64

from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource

from .stmt_lines import stmt_lines


class AccountBankStatementImportTest(TransactionCase):
    def test_001_bnc_statement_import(self):
        """
        Check banesco statement file is processed correctly
        """

        bnc_file_path = get_module_resource(
            "bnc_bank_statement_import", "bnc_stmt_file", "bnc_stmt.txt"
        )

        bnc_file = base64.b64encode(open(bnc_file_path, "rb").read())

        bank_journal = self.env["account.journal"].create(
            {"name": "Bank 123456", "code": "BNK67", "type": "bank"}
        )

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bnc_file.txt", "datas": bnc_file})
                    ]
                }
            )
        )
        import_wizard.import_file()

        statement_id = self.env["account.bank.statement"].search(
            [("journal_id", "=", bank_journal.id)]
        )

        for stmt_line in stmt_lines:
            stmt_line["date"] = fields.Date.from_string(stmt_line["date"])

        self.assertRecordValues(statement_id.line_ids.sorted("date"), stmt_lines)

    def test_002_bnc_statement_file_validation(self):
        """
        Check banesco file format validation works correctly
        """

        bnc_file_path = get_module_resource(
            "bnc_bank_statement_import", "bnc_stmt_file", "bad_bnc_stmt.txt"
        )
        bnc_file = open(bnc_file_path, "r").readline()

        self.assertFalse(
            self.env["account.bank.statement.import"]._is_bnc_file(bnc_file)
        )

    def test_003_bnc_statement_in_state_open(self):
        """
        Check banesco statement file is passed to the "Open" state
        """

        bnc_file_path = get_module_resource(
            "bnc_bank_statement_import", "bnc_stmt_file", "bnc_stmt.txt"
        )

        bnc_file = base64.b64encode(open(bnc_file_path, "rb").read())

        bank_journal = self.env["account.journal"].create(
            {"name": "Bank 123456", "code": "BNK67", "type": "bank"}
        )

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bnc_file.txt", "datas": bnc_file})
                    ]
                }
            )
        )

        import_wizard.import_file()

        statement_id = self.env["account.bank.statement"].search(
            [("journal_id", "=", bank_journal.id),
             ("state", "=", "open")]
        )

        self.assertFalse(statement_id)
        self.assertTrue(statement_id.state != "open")
