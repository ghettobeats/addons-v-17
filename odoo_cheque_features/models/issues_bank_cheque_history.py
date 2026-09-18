from odoo import api, fields, models, _


class IssuesBankChequeHistory(models.Model):
    _inherit = "issued.bank.cheque.history"

    cheque_date = fields.Date("Date on cheque")
    payment_id = fields.Many2one("account.payment", "Payment", copy=False)
    company_id = fields.Many2one(
        related="bank_cheque_book_id.company_id",
        string="Company",
        store=True,
        readonly=True,
        index=True,
    )

    @api.onchange("customer_id")
    def onchange_customer_id(self):
        if self.customer_id:
            self.paid_to = self.customer_id.name
