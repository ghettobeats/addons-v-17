from odoo import api, fields, models

class AccountPayment(models.Model):
    _inherit = "account.payment"

    check_number = fields.Char(
        string="Check Number",
        store=True,
        readonly=True,
        tracking=True,
        copy=False,
        compute='_compute_check_number',
        inverse='_inverse_check_number',
        help="The selected journal is configured to print check numbers. If your pre-printed check paper already has numbers "
             "or if the current numbering is wrong, you can change it in the journal configuration page.",
    )
