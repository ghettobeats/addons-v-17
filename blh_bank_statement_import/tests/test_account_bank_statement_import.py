import base64

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.modules.module import get_module_resource

from .stmt_lines import stmt_lines


@tagged("post_install", "-at_install")
class AccountBankStatementImportTest(AccountTestInvoicingCommon):
    def test_001_blh_statement_import(self):
        """
        Check BLH statement file is processed correctly
        """

        blh_file_path = get_module_resource(
            "blh_bank_statement_import", "blh_stmt_file", "blh_statement.csv"
        )
        blh_file = base64.b64encode(open(blh_file_path, "rb").read())

        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bpd_file.txt", "datas": blh_file})
                    ]
                }
            )
        )

        import_wizard.with_context(skip_csv_check=True).import_file()

        statement_id = self.env["account.bank.statement"].search([("journal_id", "=", bank_journal.id)])

        for stmt_line in stmt_lines:
            stmt_line["date"] = fields.Date.from_string(stmt_line["date"])

        self.assertRecordValues(statement_id.line_ids.sorted("date"), stmt_lines)

    def validate_file(self, file_path):
        """
        This method gets the resource file path
        gets the file clean structure
        and validates it using the
        file validation function for this bank

        :param file_path: String
        :return: file_validation: boolean
        """

        path = get_module_resource(
            "blh_bank_statement_import", "blh_stmt_file", file_path
        )
        file = open(path, "r").read().split("\n")
        file = [line.split(",") for line in file]

        return self.env["account.bank.statement.import"]._is_blh_file(file)

    def test_002_blh_statement_file_validation(self):
        """
        Check blh file format validation works correctly
        """

        self.assertTrue(self.validate_file("blh_statement.csv"))
        self.assertFalse(self.validate_file("bad_blh_stmt.csv"))

    def test_003_blh_statement_in_state_open(self):
        """
        Check blh statement file is passed to the "Open" state
        """

        blh_file_path = get_module_resource(
            "blh_bank_statement_import", "blh_stmt_file", "blh_statement.csv"
        )
        blh_file = base64.b64encode(open(blh_file_path, "rb").read())

        bank_journal = self.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )

        bank_journal.company_id.create_statement_draft = True

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bpd_file.txt", "datas": blh_file})
                    ]
                }
            )
        )

        import_wizard.with_context(skip_csv_check=True).import_file()

        statement_id = self.env["account.bank.statement"].search(
            [("journal_id", "=", bank_journal.id),
             ("state", "=", "open")]
        )

        self.assertTrue(statement_id)
        self.assertFalse(statement_id.state != "open")
