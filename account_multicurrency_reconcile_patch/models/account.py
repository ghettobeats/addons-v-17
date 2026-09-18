from odoo import models, api


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _reconcile_lines(self, debit_moves, credit_moves, field):

        if debit_moves.currency_id != credit_moves.currency_id:
            field = "amount_residual_currency"
            self = self.with_context(patched=True)

        return super(AccountMoveLine, self)._reconcile_lines(
            debit_moves, credit_moves, field
        )


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    @api.model
    def create(self, vals):
        patched = self.env.context.get("patched", False)
        if patched and "currency_id" in vals:
            vals["currency_id"] = False

        return super(AccountPartialReconcile, self).create(vals)
