from odoo import fields, models


class BankChequeBook(models.Model):
    _inherit = "bank.cheque.book"

    bank_cheque_id = fields.Many2one(domain=False)
    company_id = fields.Many2one(
        "res.company",
        "Company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )


class BankChequeAttribute(models.Model):
    _inherit = "bank.cheque.attribute"

    free_text = fields.Char()
    attribute = fields.Selection(
        selection_add=[
            ("free_text", "Free Text"),
        ],
        required=True,
        default="cheque_date",
        ondelete={"free_text": "set default"},
    )
