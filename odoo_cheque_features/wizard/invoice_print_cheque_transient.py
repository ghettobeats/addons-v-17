from odoo import api, fields, models, _


class InvoicePrintBankChequeWizard(models.TransientModel):
    _inherit = "invoice.print.bank.cheque.wizard"

    user_is_cheque_manager = fields.Boolean(compute="_compute_user_is_cheque_manager")
    cheque_history_id = fields.Many2one(
        "issued.bank.cheque.history",
        "Cheque Number",
        domain='[("issued", "=", False), ("state", "!=", "cancelled")]',
    )
    date = fields.Date("Date On Cheque", default=lambda self: self._default_date())

    @api.model
    def _default_date(self):
        """Compute date by default."""
        if self.env.context.get(
            "active_model"
        ) == "account.payment" and self.env.context.get("active_id"):
            payment = self.env["account.payment"].browse(self.env.context["active_id"])
            return payment.date

    def print_cheque(self):
        res = super(InvoicePrintBankChequeWizard, self).print_cheque()
        if self._context.get("active_model") == "account.payment":
            active_obj = self.env["account.payment"].browse(
                self._context.get("active_id")
            )
        self.cheque_history_id.write(
            {
                "payment_id": active_obj,
            }
        )
        return res

    @api.depends("date")
    def _compute_user_is_cheque_manager(self):
        for record in self:
            record.user_is_cheque_manager = self.user_has_groups(
                "odoo_cheque_management.group_bank_cheque_manager"
            )

    @api.onchange("cheque_book_id")
    def onchange_cheque_book_id(self):
        if self.cheque_book_id:
            self.onchange_amount()
            x = self.env["issued.bank.cheque.history"].search(
                [
                    ("bank_cheque_book_id", "=", self.cheque_book_id.id),
                    ("issued", "=", False),
                    ("state", "!=", "cancelled"),
                ],
                order="cheque_number asc",
                limit=1,
            )
            if x:
                self.cheque_history_id = x.id
            return {
                "domain": {
                    "cheque_history_id": [
                        ("bank_cheque_book_id", "=", self.cheque_book_id.id),
                        ("issued", "=", False),
                        ("state", "!=", "cancelled"),
                    ]
                }
            }
        return {}
