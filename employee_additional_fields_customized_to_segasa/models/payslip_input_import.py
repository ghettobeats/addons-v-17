# -*- coding: utf-8 -*-

from odoo import fields, models


class PayslipInputImport(models.Model):
    _inherit = "payslip.input.import"

    active = fields.Boolean(related="employee_id.active")