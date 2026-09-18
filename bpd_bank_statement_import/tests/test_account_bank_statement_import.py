import base64

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.modules.module import get_module_resource

from .stmt_lines import stmt_lines


@tagged("post_install", "-at_install")
class AccountBankStatementImportTest(AccountTestInvoicingCommon):
    def test_001_bpd_statement_import(self):
        """
        Check BPD statement file is processed correctly
        """

        bpd_file_path = get_module_resource(
            "bpd_bank_statement_import", "bpd_stmt_file", "bpd_stmt.txt"
        )

        bpd_file = base64.b64encode(open(bpd_file_path, "rb").read())

        bank_journal = self.env["account.journal"].create(
            {
                "name": "Bank 123456",
                "code": "BNK67",
                "type": "bank",
                "bank_acc_number": "809972854",
            }
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
        dop_currency_id = self.env.ref("base.DOP")
        if bank_journal.company_id.currency_id != dop_currency_id:
            bank_journal.write({"currency_id": dop_currency_id.id})

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bpd_file.txt", "datas": bpd_file})
                    ]
                }
            )
        )
        statement = import_wizard.import_file()

        statement_id = self.env["account.bank.statement"].browse(statement["res_id"])

        for stmt_line in stmt_lines:
            stmt_line["date"] = fields.Date.from_string(stmt_line["date"])

        self.assertRecordValues(statement_id.line_ids.sorted("date"), stmt_lines)

    def test_002_bpd_statement_file_validation(self):
        """
        Check bpd file format validation works correctly
        """

        bpd_file_path = get_module_resource(
            "bpd_bank_statement_import", "bpd_stmt_file", "bad_bpd_stmt.txt"
        )
        bpd_file = open(bpd_file_path, "r").readline()

        self.assertFalse(
            self.env["account.bank.statement.import"]._is_bpd_file(bpd_file)
        )

    def test_003_bdp_statement_in_state_open(self):
        """
        Check bdr statement file is passed to the "Open" state
        """

        bpd_file_path = get_module_resource(
            "bpd_bank_statement_import", "bpd_stmt_file", "bpd_stmt.txt"
        )

        bpd_file = base64.b64encode(open(bpd_file_path, "rb").read())

        bank_journal = self.env["account.journal"].create(
            {
                "name": "Bank 123456",
                "code": "BNK67",
                "type": "bank",
                "bank_acc_number": "809972854",
            }
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
        dop_currency_id = self.env.ref("base.DOP")
        if bank_journal.company_id.currency_id != dop_currency_id:
            bank_journal.write({"currency_id": dop_currency_id.id})

        import_wizard = (
            self.env["account.bank.statement.import"]
            .with_context(journal_id=bank_journal.id)
            .create(
                {
                    "attachment_ids": [
                        (0, 0, {"name": "bpd_file.txt", "datas": bpd_file})
                    ]
                }
            )
        )
        import_wizard.import_file()

        statement_id = self.env["account.bank.statement"].search(
            [("journal_id", "=", bank_journal.id),
             ("state", "=", "open")]
        )

        self.assertTrue(statement_id)
        self.assertFalse(statement_id.state != "open")
