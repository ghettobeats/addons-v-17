# -*- coding: utf-8 -*-
#  Copyright (c) 2018 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_default_commission_journal(self):
        journal_id = self.env['account.journal'].sudo().search(
            [('type', '=', 'general'), ('company_id', '=', self.id)], order='id asc', limit=1)
        return journal_id if journal_id else False

    commission_journal_id = fields.Many2one('account.journal', 'Commission Journal', domain=[('type', '=', 'general')],
                                            default=_get_default_commission_journal)
    commission_debit_account = fields.Many2one('account.account', company_dependent=True,
                                               string="Debit Account")
    commission_credit_account = fields.Many2one('account.account', company_dependent=True,
                                                string="Credit Account")
