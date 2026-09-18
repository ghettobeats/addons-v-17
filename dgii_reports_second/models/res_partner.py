# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.
# © 2018 José López <jlopez@indexa.do>

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"




    is_company_related = fields.Boolean("Esta relacionado a compania?", compute="compute_is_company_related")

    def compute_is_company_related(self):
        company = self.env['res.company'].search([('partner_id','=',self.id)])
        for rec in self:
            if rec.id == company.partner_id.id:
                rec.is_company_related = True
            else:
                rec.is_company_related = False

    related = fields.Selection(
        [('0', 'Not Related'),
         ('1', 'Related')],
        default='0',
    )



    property_account_payable_advance_id = fields.Many2one(
        'account.account', "Cuenta de avances a proveedores por default", company_dependent=True,
        domain=[
            ('internal_type', '=', 'receivable'),
            ('deprecated', '=', False),
        ], default=lambda self: self.env.company.property_account_payable_advance_id.id or False)
    property_account_receivable_advance_id = fields.Many2one(
        'account.account', "Cuenta de avances a clientes por default", company_dependent=True,
        domain=[
            ('internal_type', '=', 'payable'),
            ('deprecated', '=', False),
        ], default=lambda self: self.env.company.property_account_receivable_advance_id.id or False)

    @api.model
    def _commercial_fields(self):
        return super(ResPartner, self)._commercial_fields() + \
               ['property_account_payable_advance_id', 'property_account_receivable_advance_id']
