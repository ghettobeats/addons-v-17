# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _


class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    house_rent_allowance = fields.Monetary(
        string='House Rent Allowance', help="House rent allowance.", tracking=True)
    dearness_allowance = fields.Monetary(
        string="Dearness Allowance", help="Dearness allowance")
    travel_allowance = fields.Monetary(
        string="Travel Allowance", help="Travel allowance")
    meal_allowance = fields.Monetary(
        string="Meal Allowance", help="Meal allowance")
    medical_allowance = fields.Monetary(
        string="Medical Allowance", help="Medical allowance")
    other_allowance = fields.Monetary(
        string="Other Allowance", help="Other allowances")
