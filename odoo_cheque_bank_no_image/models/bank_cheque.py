from odoo import fields, models


class BankChequeBook(models.Model):
    _inherit = "bank.cheque.book"

    bank_cheque_id = fields.Many2one(domain=False)
