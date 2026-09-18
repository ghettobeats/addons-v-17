from odoo import api, fields, models, _


class Payment(models.Model):
    _inherit = "account.payment"

    issued_cheque_history_ids = fields.One2many(
        "issued.bank.cheque.history",
        "payment_id",
        "Printed Cheques",
        copy=False,
        readonly=True,
    )
    cheque_count = fields.Integer("Cheque Count", compute="_get_cheque_count")

    @api.depends("issued_cheque_history_ids")
    def _get_cheque_count(self):
        for payment in self:
            payment.cheque_count = len(payment.issued_cheque_history_ids)

    def action_view_cheque(self):
        cheques = self.mapped("issued_cheque_history_ids")
        action = self.env.ref("odoo_cheque_features.bank_cheque_issued_action").read()[
            0
        ]
        if len(cheques) > 1:
            action["domain"] = [("id", "in", cheques.ids)]
        elif len(cheques) == 1:
            form_view = [
                (
                    self.env.ref(
                        "odoo_cheque_features.bank_cheque_issued_view_form"
                    ).id,
                    "form",
                )
            ]
            action["views"] = form_view
            action["res_id"] = cheques.id
        else:
            action = {"type": "ir.actions.act_window_close"}
        return action

    @api.onchange("amount", "currency_id")
    def _onchange_amount_words(self):
        amount_i, amount_d = divmod(self.amount, 1)
        amount_d = round(amount_d, 2)
        amount_d = int(round(amount_d * 100, 2))
        words = (
            self.currency_id.with_context(lang=self.partner_id.lang or "es_ES")
            .amount_to_text(amount_i)
            .upper()
        )
        self.check_amount_in_words = _("%(words)s WITH %(amount_d)s/100") % dict(
            words=words, amount_d=amount_d
        )
