from odoo import models, fields



class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    account_check_printing_layout = fields.Selection(related='company_id.account_check_printing_layout', string="Check Layout", readonly=False,
        help="Select the format corresponding to the check paper you will be printing your checks on.\n")
