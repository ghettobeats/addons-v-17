# -*- coding: utf-8 -*-
from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
import json


class AccountMoveInherit(models.Model):
    _inherit = "account.move.line"

    line_caja_chica_id = fields.Many2one('petty.expense.lines',
                                         string='Lineas de Caja Chica Relacionada')


class AccountMoveInherit(models.Model):
    _inherit = "account.move"

    caja_chica_id = fields.Many2one('petty.cash.expense',
                                    string='Caja Chica Relacionada')

    def _get_invoice_payment_widget(self):
        if self.invoice_payments_widget:
            j = json.loads(self.invoice_payments_widget)
            return j['content'] if j else []
        else:
            return []

    @api.constrains('invoice_payments_widget', 'caja_chica_id')
    def assign_payment_caja_chica(self):
        for rec in self:
            if rec.move_type == 'in_invoice' and rec.caja_chica_id and rec.state == 'posted':
                for payment in rec._get_invoice_payment_widget():
                    if 'account_payment_id' in payment:
                        payment_id = self.env['account.payment'].browse(payment['account_payment_id'])

                        if not payment_id.id in rec.caja_chica_id.payment_ids.ids:
                            rec.caja_chica_id.write({'payment_ids': [(6, 0, payment_id.ids)], })

    def action_view_caja_chica(self):
        ''' Redirect the user to the bill(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        # action = self.env.ref('stock.action_picking_tree_ready')

        action = {
            'name': _("Caja Chica Relacionada"),
            'type': 'ir.actions.act_window',
            'res_model': 'petty.cash.expense',
            'context': {'create': False},
        }

        for rec in self:
            stock_by_moves = self.env['petty.cash.expense'].search([('id', '=', rec.caja_chica_id.id)])

        if len(stock_by_moves) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': stock_by_moves.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', stock_by_moves.ids)],
            })
        return action

    @api.constrains(
        "l10n_do_fiscal_number", "partner_id", "company_id", "posted_before"
    )
    def _l10n_do_check_unique_vendor_number(self):
        for rec in self.filtered(
                lambda inv: inv.l10n_do_fiscal_number
                            and inv.country_code == "DO"
                            and inv.l10n_latam_use_documents
                            and inv.is_purchase_document()
                            and inv.commercial_partner_id
        ):
            domain = [
                ("move_type", "=", rec.move_type),
                ("l10n_do_fiscal_number", "=", rec.l10n_do_fiscal_number),
                ("company_id", "=", rec.company_id.id),
                ("id", "!=", rec.id),
                ("commercial_partner_id", "=", rec.commercial_partner_id.id),
                ("state", "!=", "cancel"),
            ]
            if rec.search_count(domain):
                values = rec.search(domain)
                raise ValidationError(
                    _(
                        "El Número de comprobante fiscal de la factura del proveedor debe ser único por proveedor y compañía. Se encontró una factura duplicada: Número de factura %(inv_name)s, Número Fiscal %(fiscal_number)s."
                    ) % {
                        "inv_name": values.name,
                        "fiscal_number": values.l10n_do_fiscal_number,
                    }
                )
