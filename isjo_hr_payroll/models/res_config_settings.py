# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_hr_payroll_account = fields.Boolean(string='Payroll with Accounting', default=True)

    @api.model
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('hr_payroll.module_hr_payroll_account',
                                                         self.module_hr_payroll_account)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            module_hr_payroll_account=self.env['ir.config_parameter'].sudo().get_param(
                'hr_payroll.module_hr_payroll_account', default=True)
        )
        return res
