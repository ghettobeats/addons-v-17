from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_do_reconcile_invoice_id = fields.Many2one(
        "account.move",
        string="Reconciled Payment Invoice",
        copy=False,
        help="Technical field to map reconciled moves items with invoices",
    )
