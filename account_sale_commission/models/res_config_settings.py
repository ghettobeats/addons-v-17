# -*- coding: utf-8 -*-
#  Copyright (c) 2018 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    commission_journal_id = fields.Many2one('account.journal', 'Commission Journal', domain=[('type', '=', 'general')],
                                            related='company_id.commission_journal_id', readonly=False)
    commission_debit_account = fields.Many2one('account.account', company_dependent=True, string="Debit Account",
                                               related='company_id.commission_debit_account', readonly=False)
    commission_credit_account = fields.Many2one('account.account', company_dependent=True, string="Credit Account",
                                                related='company_id.commission_credit_account', readonly=False)
    commission_schema = fields.Selection([('pays', 'Pays'), ('liquidate', 'Liquidate')], default='liquidate')
    commission_base = fields.Selection([('net', 'Net Amount'), ('gross', 'Gross Amount')], default='gross')
    commission_beneficiary = fields.Selection([('invoice', 'Invoice Salesperson'),
                                               ('partner', 'Customer Salesperson'),
                                               ('payment', 'Payment collector')], default='invoice')
    commission_currency_rate = fields.Selection([('invoice', 'Invoice date rate'), ('current', 'Current rate')],
                                                default='invoice')
    move_date = fields.Selection(
        [('create_date', 'Payment create date'),
         ('assignment_date', 'Payment assignment date')],
        default='create_date',
        help="Create date: payment creation date\n"
        "Assignment date: when payment was applied"
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        commission_schema = ICPSudo.get_param(
            'account_sale_commission.commission_schema')
        commission_base = ICPSudo.get_param(
            'account_sale_commission.commission_base')
        commission_beneficiary = ICPSudo.get_param(
            'account_sale_commission.commission_beneficiary'
        )
        commission_currency_rate = ICPSudo.get_param(
            'account_sale_commission.commission_currency_rate'
        )
        move_date = ICPSudo.get_param(
            'account_sale_commission.move_date'
        )
        res.update(
            commission_schema=commission_schema if commission_schema else 'liquidate',
            commission_base=commission_base if commission_base else 'gross',
            commission_beneficiary=commission_beneficiary if commission_beneficiary else 'invoice',
            commission_currency_rate=commission_currency_rate if commission_currency_rate else 'invoice',
            move_date=move_date if move_date else 'create_date'
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        ICPSudo.set_param('account_sale_commission.commission_schema',
                          self.commission_schema if self.commission_schema else 'liquidate')
        ICPSudo.set_param('account_sale_commission.commission_base',
                          self.commission_base if self.commission_base else 'gross')
        ICPSudo.set_param('account_sale_commission.commission_beneficiary',
                          self.commission_beneficiary if self.commission_beneficiary else 'invoice')
        ICPSudo.set_param('account_sale_commission.commission_currency_rate',
                          self.commission_currency_rate if self.commission_currency_rate else 'invoice')
        ICPSudo.set_param('account_sale_commission.move_date',
                          self.move_date if self.move_date else 'create_date')
