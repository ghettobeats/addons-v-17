#  Copyright (c) 2019 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    due_days = fields.Integer(
        compute='_compute_due_days',
        store=True,
        default=0,
    )

    @api.depends('payment_term_id', 'date_due', 'state')
    def _compute_due_days(self):

        for invoice in self.filtered(lambda i: i.state == 'open'):

            today = fields.Date.today()
            date_due = invoice.date_due or today
            rd = today - date_due

            invoice.due_days = rd.days if rd.days > 0 else 0
