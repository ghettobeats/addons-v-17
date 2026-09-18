# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    _description = 'Register Payment'

    # == Business fields ==
    journal_id = fields.Many2one('account.journal', store=True, readonly=False,
        compute='_compute_journal_id',
        domain="[('company_id', '=', company_id), ('type', 'in', ('bank', 'cash', 'general'))]")
    journal_id_type = fields.Selection(related="journal_id.type")

    investor_id = fields.Many2one('res.partner', "Accionista", store=True, tracking=True)
    is_investor_related = fields.Boolean('Esta relacionado a accionista?', store=True)

