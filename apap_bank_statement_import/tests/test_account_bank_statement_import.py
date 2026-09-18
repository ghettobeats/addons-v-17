import base64
import re
from odoo import fields
from odoo.tests.common import TransactionCase, tagged
from odoo.modules.module import get_module_resource
from datetime import datetime as dt
import csv
from .stmt_lines import stmt_lines


@tagged("post_install", "-at_install")
class AccountBankStatementImportTest(TransactionCase):

    def get_reader(self, file_name):

        apap_file_path = get_module_resource(
            "apap_bank_statement_import", "apap_stmt_file", file_name
        )
        apap_file = []
        with open(apap_file_path, newline="") as data:
            reader = csv.reader(
                (x.replace("\0", "").replace("ï»¿", "").replace(" :", "").replace("\ufeff", "") for x in data),
                delimiter=",",
                quotechar='"',
            )

            for i, row in enumerate(reader):
                apap_file.append(row)
        return apap_file

    def test_001_apap_statement_import(self):
        """
        Check apap statement file is processed correctly
        """

        apap_file_path = get_module_resource(
            "apap_bank_statement_import", "apap_stmt_file", "apap_statement.csv"
        )
        apap_file = base64.b64encode(open(apap_file_path, "rb").read())

        bank_journal = self.env["account.journal"].create(
            {"name": "Bank 123456", "code": "BNK67", "type": "bank"}
        )

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "apap_statement.csv", "datas": apap_file})
                    ]
                }
            )
        )

        import_wizard.import_file()

        statement_id = self.env["account.bank.statement"].search(
            [("journal_id", "=", bank_journal.id)]
        )
        for i, line in enumerate(statement_id.line_ids.sorted("id")):
            for k, v in stmt_lines[i].items():
                if k == "amount":
                    self.assertEqual(
                        round(line.mapped(k)[0], 2), v, "Wrong value item %s" % k
                    )
                else:
                    self.assertEqual(line.mapped(k)[0], v, "Wrong value item %s" % k)

    def test_002_apap_statement_file_validation(self):
        """
        Check apap file format validation works correctly
        """
        self.assertFalse(
            self.env["account.bank.statement.import"]._is_apap_file(self.get_reader("bad_apap_statement.csv"))
        )

        self.assertTrue(
            self.env["account.bank.statement.import"]._is_apap_file(self.get_reader("apap_statement.csv"))
        )

    def test_003_apap_statement_in_state_open(self):
        """
        Check apap statement file is passed to the "Open" state
        """

        apap_file_path = get_module_resource(
            "apap_bank_statement_import", "apap_stmt_file", "apap_statement.csv"
        )
        apap_file = base64.b64encode(open(apap_file_path, "rb").read())

        bank_journal = self.env["account.journal"].create(
            {"name": "Bank 123456", "code": "BNK67", "type": "bank"}
        )

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "apap_statement.csv", "datas": apap_file})
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
