from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10ndoAccountBatchPaymentBase(models.TransientModel):
    _name = "l10n_do.account.batch.payment"
    _description = "Dominican Batch Payment"

    journal_id = fields.Many2one(
        "account.journal",
        "Journal",
        domain=[("type", "=", "bank")],
        required=True,
    )
    payment_ids = fields.Many2many(
        "account.payment",
        string="Payments",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.user.company_id.currency_id,
    )
    total_to_pay = fields.Monetary(
        string="Total Amount",
        compute="_compute_total_to_pay",
        currency_field="currency_id",
    )
    file = fields.Binary(string="Download File")
    filename = fields.Char(string="File Name")
    email = fields.Char(string="Email")

    @api.depends("payment_ids")
    def _compute_total_to_pay(self):
        for record in self:
            record.total_to_pay = record._get_total_to_pay()

    def _get_total_to_pay(self):
        return sum([p.amount for p in self.payment_ids])

    @api.onchange("journal_id")
    def _onchange_journal_id(self):
        self.payment_ids = False

    def _get_wizard_action(self):
        # lol... this is a really fucking huge external id
        module = "l10n_do_account_batch_payment_base"
        xml_id = "l10n_do_account_batch_payment_wizard_action"
        action = self.env.ref("%s.%s" % (module, xml_id)).read()[0]
        action["res_id"] = self.id
        return action

    def generate_bank_file(self):
        """
        Each module adding a bank support must extends this method. Its generates
        the file depending on each bank format and write it to *file* field to be
        downloaded.
        """
        raise UserError(
            _(
                "Could not generate any bank file.\n"
                "Did you install the module to support %s bank?" % self.journal_id.name
            )
        )
