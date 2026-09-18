# -*- coding: utf-8 -*-
# (C) 2018 Smile (<http://www.smile.fr>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError




class AccountInvoice(models.Model):
    _inherit = 'account.move'

    @api.constrains("name", "partner_id", "company_id")
    def _check_unique_vendor_number(self):
        for rec in self.filtered(
            lambda x: x.is_purchase_document()
            and x.company_id.country_id == self.env.ref("base.do")
            and x.l10n_latam_use_documents
            and x.l10n_latam_document_number
        ):
            pass
        

    def button_cancel(self):
        recovery = self.env['account.payment.recovery'].search([])

        for rec in recovery:
            for move in self:
                if move.id == rec.move_id.id:
                    rec.payment_id.stored_advance_residual += rec.amount
                    rec.unlink()
                    move.is_advanced_move_cancelled = True
        return super(AccountInvoice, self).button_cancel()

    def button_draft(self):

        for move in self:
            if move.is_advanced_move_cancelled == True:
                raise UserError(_("No puede volver draft un movimiento cancelado relacionado a un avance. "
                                  "Favor ir a la factura y reasignar el avance."))
        return super(AccountInvoice, self).button_draft()

    is_advanced_move_cancelled = fields.Boolean('is advanced move cancelled?', store=True, default=False)
    is_sn_advanced = fields.Boolean('is SN advanced?', compute="boolean_advance",store=False, default=False)

    @api.depends('state')
    def boolean_advance(self):
        for inv in self:
            inv.is_sn_advanced = False
            if inv.state == 'posted' and inv.move_type != 'entry':
                payments = self.env['account.payment'].search([('partner_id','=',inv.partner_id.id),('is_advance_payment','=',True)
                                                   ,('state','=','posted'), ('currency_id','=',inv.currency_id.id)])


                for pay in payments:

                    if (pay.stored_advance_residual > 0.0) and pay.is_advance_payment == True:
                        # raise UserError(_("%s,%s", payments.recovery_ids.payment_id.ids, payments.ids))
                        inv.is_sn_advanced = True


    recovery_ids = fields.One2many(
        'account.payment.recovery', 'invoice_id',
        'Advance payments', readonly=True,
        states={'draft': [('readonly', False)]})

    # def action_post(self):
    #     """ Create recevories at invoice validation.
    #     """
    #     res = super(AccountInvoice, self).action_post()
    #     self._recover_advance_payments()
    #
    #     return res_recover_advance_payments

    def do_recover_advance_payments(self):
        return {
            'name': _('Seleccion de avances'),
            'res_model': 'get.advaces.wizard',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def _recover_advance_payments(self,payment):
        for inv in self:
            if inv.move_type != 'entry':
                residual = inv.amount_residual
                for advance_payment in inv._get_advance_payments(payment):

                    if residual > 0 and advance_payment.stored_advance_residual > 0:
                        if (advance_payment.id not in advance_payment.recovery_ids.payment_id.ids or advance_payment.stored_advance_residual > 0.0):
                            advance_residual = advance_payment.stored_advance_residual
                            if advance_payment.currency_id != inv.currency_id:
                                advance_residual = advance_payment.currency_id. \
                                    with_context(date=inv.invoice_id.invoice_date). \
                                    compute(advance_residual, inv.currency_id)
                            amount = min(residual, advance_residual)

                            recovery = self.env['account.payment.recovery'].create({
                                'invoice_id': self.id,
                                'payment_id': advance_payment.id,
                                'amount': amount,
                                })

                            recovery.post()
                            residual -= amount

    def _get_advance_payments(self,payment):
        # Override in smile_advance_payment_purchase
        advance_payments = None
        advance_payments = self.env['account.payment'].search([('partner_id','=',self.partner_id.id),('is_advance_payment','=',True)
                                                   ,('state','=','posted'), ('currency_id','=',self.currency_id.id), ('id','=',payment)])

        # raise UserError(_("%s", advance_payments))
        return advance_payments

    def action_cancel(self):
        """ Reverse recoveries when invoice is cancelled.
        """
        res = super(AccountInvoice, self).action_cancel()
        self.recovery_ids.mapped('move_id').action_cancel()
        return res
