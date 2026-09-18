import xlrd
import base64

from odoo import fields
from odoo.tests.common import TransactionCase, tagged
from odoo.modules.module import get_module_resource

from .stmt_lines import (
    stmt_lines,
    stmt_balance_end_real,
    stmt_balance_start,
)


@tagged("post_install", "-at_install")
class AccountBankStatementImportTest(TransactionCase):
    def test_001_bhd_panama_statement_import(self):
        """
        Check bhd statement file is processed correctly
        """

        bhd_panama_file_path = get_module_resource(
            "bhd_panama_bank_statement_import", "bhd_panama_stmt_file", "bhd_panama_statement.xlsx"
        )

        bhd_panama_file = base64.b64encode(open(bhd_panama_file_path, "rb").read())

        bank_journal = self.env["account.journal"].create(
            {"name": "Bank 123456", "code": "BNK67", "type": "bank"}
        )

        # Checking whether the journal company's currency_id is different
        # from the file's currency_id
        # in which case the journal currency_id is set to the one
        # in file
        #
        # as the bank_statement_import module
        # takes the currency_id of the user's company
        # when no currency_id is specified in the journal
        # which can lead to wrong currency on statements

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bhd_panama_stmt.xlsx", "datas": bhd_panama_file})
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

        for stmt_line in stmt_lines:
            stmt_line["date"] = fields.Date.from_string(stmt_line["date"])

        self.assertRecordValues(statement_id.line_ids.sorted("id"), stmt_lines)

    def test_002_bhd_panama_statement_file_validation(self):
        """
        Check bhd file format validation works correctly
        """

        bhd_panama_file_path = get_module_resource(
            "bhd_panama_bank_statement_import", "bhd_panama_stmt_file", "bhd_panama_statement.xlsx"
        )
        bhd_panama_file = xlrd.open_workbook(bhd_panama_file_path)
        self.assertTrue(
            self.env["account.bank.statement.import"]._is_bhd_panama_file(bhd_panama_file)
        )

    def test_003_bhd_panama_statement_in_state_open(self):
        """
        Check bhd statement file is passed to the "Open" state
        """

        bhd_panama_file_path = get_module_resource(
            "bhd_panama_bank_statement_import", "bhd_panama_stmt_file", "bhd_panama_statement.xlsx"
        )

        bhd_panama_file = base64.b64encode(open(bhd_panama_file_path, "rb").read())

        bank_journal = self.env["account.journal"].create(
            {"name": "Bank 123456", "code": "BNK67", "type": "bank"}
        )

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bhd_panama_stmt.xlsx", "datas": bhd_panama_file})
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
