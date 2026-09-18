from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RentalToInvoice(models.TransientModel):
    _name = 'get.advaces.wizard'
    _description = 'Generate invoice for all selected rentals'

    advance_ids = fields.Many2many('account.payment', 'account_payment_advance_group_rel', 'invoice_id', 'payment_id',
                                  'Avances')
    wizard_customer_id = fields.Many2one('res.partner', required=True, string='Cliente', help="Cliente", store=True)
    wizard_move_type = fields.Char('Move type')

    @api.model
    def default_get(self, fields):
        res = super(RentalToInvoice, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        move = self.env['account.move'].browse(active_id)
        res['wizard_customer_id'] = move.partner_id
        if move.move_type in ('in_invoice','in_receipt'):
            res['wizard_move_type'] = 'outbound'
        if move.move_type in ('out_invoice','out_receipt'):
            res['wizard_move_type'] = 'inbound'
        return res

    def compute_advance(self):
        [data] = self.read()
        if not data['advance_ids']:
            raise UserError(_("Tiene que selecionar avances(s) para generar la compensacion(s)."))
        active_id = self.env.context.get('active_id')
        move = self.env['account.move'].browse(active_id)
        for rent in self.env['account.payment'].browse(data['advance_ids']):
            if rent.advance_residual == 0.0:
                raise UserError(_("No puede seleccionar un pago que ya esta aplicado o no tiene avances."))
            else:
                for advance in data['advance_ids']:
                    move._recover_advance_payments(advance)

        return {'type': 'ir.actions.act_window_close'}