from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    account_check_printing_layout = fields.Selection(selection_add=[
            ('mitur_check_printing.action_print_custom_report', 'custom report')
        ])