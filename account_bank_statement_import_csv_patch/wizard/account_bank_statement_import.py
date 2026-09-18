from odoo import models


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def _check_csv(self, filename):

        if self.env.context.get("skip_csv_check", True):
            return False

        return super(AccountBankStatementImport, self)._check_csv(filename)

    def _create_bank_statements(self, stmts_vals):
        statement_imported = super(AccountBankStatementImport, self)._create_bank_statements(stmts_vals)
        statement = self.env['account.bank.statement'].browse(statement_imported[0])

        if statement.company_id.create_statement_draft:
            statement.button_reopen()

        return statement_imported[0], statement_imported[1], statement_imported[2]
