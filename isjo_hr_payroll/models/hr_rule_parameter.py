# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api


class HrSalaryRuleParameter(models.Model):
    _inherit = 'hr.rule.parameter'
    _description = 'Salary Rule Parameter'

    def write(self, vals):
        self.clear_caches()  # Clear the cache in order to recompute _get_parameter_from_code
        return super(HrSalaryRuleParameter, self).write(vals)
