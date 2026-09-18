from odoo import fields, models, api, _
import json

from odoo.exceptions import ValidationError, UserError


# class IrMailServer(models.Model):
#     """Represents an SMTP server, able to send outgoing emails, with SSL and TLS capabilities."""
#     _inherit = "ir.mail_server"
#
#     @api.model
#     def _get_default_bounce_address(self):
#         '''Compute the default bounce address.
#
#         The default bounce address is used to set the envelop address if no
#         envelop address is provided in the message.  It is formed by properly
#         joining the parameters "mail.bounce.alias" and
#         "mail.catchall.domain".
#
#         If "mail.bounce.alias" is not set it defaults to "postmaster-odoo".
#
#         If "mail.catchall.domain" is not set, return None.
#
#         '''
#         get_param = self.env['ir.config_parameter'].sudo().get_param
#         postmaster = get_param('mail.bounce.alias', default='admin')
#         domain = get_param('mail.catchall.domain')
#         if postmaster and domain:
#             return '%s@%s' % (postmaster, domain)



class ResCompany(models.Model):
    _inherit = "res.company"

    # email_secundario = fields.Char(store=True, readonly=False, string="Email secundario")
    email = fields.Char(store=True, readonly=False)
    company_seal = fields.Image("Company Seal", max_width=200, max_height=200)
    company_firm = fields.Image("Company Sign", max_width=150, max_height=150)
    firm_name = fields.Char("Nombre de firma",Store=True)
    firm_position = fields.Char("Cargo de firma", Store=True)




    tipo_itbis_venta = fields.Selection(
        [('01', 'Exportacion de vienes y servicios Art. 342 CT'),
         ('02', 'Exportacion de vienes y servicios Art. 344 CT y Art. 14 Literal j, Reglamento 293-11'),
         ('03', 'Bienes y servicios locales  Art. 343 CT'),
         ('04', 'Bienes o servicios por destino'),
         ('05', 'Venta de activo depreciable'),
         ('08', 'Construccion: DIRECCIÓN TÉCNICA (Art. 4 Norma 07-07)'),
         ('09', 'Construccion: CONTRATO DE ADMINISTRACIÓN (Art. 4 Párrafo I, Norma 07-07)'),
         ('10', 'Construccion: ASESORIAS / HONORARIOS'),
         ('11', 'Comisionista: VENTAS DE BIENES EN CONCESIÓN'),
         ('12', 'Comisionista: VENTAS DE SERVICIOS EN NOMBRE DE TERCEROS'),
         ('13', 'Venta local de vienes exentos Párrafos III y IV, Art. 343 CT'), ],
        string="Tipo de ITBIS exento (y gravados) en venta", store=True)

    clasificacion_itbis_compra = fields.Selection(
        [('01', 'ND: EN OPERACIONES DE PRODUCTORES DE BIENES O SERVICIOS EXENTOS'),
         ('02', 'ND: A INCLUIR EN ACTIVOS (CATEGORÍA I)'),
         ('03', 'ND: OTROS ITBIS PAGADOS NO DEDUCIBLES'),
         ('04', 'D: EN LA PRODUCCIÓN Y/O VENTA DE BIENES EXPORTADOS'),
         ('05', 'D: EN LA PRODUCCIÓN Y/O VENTA DE BIENES GRAVADOS'),
         ('06', 'D: EN LA PRESTACIÓN DE SERVICIOS GRAVADOS'),
         ('07', 'P:ITBIS SUJETO A PROPORCIONALIDAD'), ],
        string="Clasificacion de ITBIS en compra (Anexo A)",
        help="Con esta asignacion se realiza la correcta distribucion en el Anexo A"
        , store=True)

    property_account_payable_advance_id = fields.Many2one(
        'account.account', "Cuenta de avances a proveedores por default",
        domain=[
            ('internal_type', '=', 'receivable'),
            ('deprecated', '=', False),
        ])
    property_account_receivable_advance_id = fields.Many2one(
        'account.account', "Cuenta de avances a clientes por default",
        domain=[
            ('internal_type', '=', 'payable'),
            ('deprecated', '=', False),
        ])

    @api.model
    def create(self, vals):
        if not vals.get('favicon'):
            vals['favicon'] = self._get_default_favicon()
        if not vals.get('name') or vals.get('partner_id'):
            self.clear_caches()
            return super(ResCompany, self).create(vals)
        partner = self.env['res.partner'].create({
            'name': vals['name'],
            'is_company': True,
            'image_1920': vals.get('logo'),
            'email': vals.get('email'),
            'phone': vals.get('phone'),
            'website': vals.get('website'),
            'vat': vals.get('vat'),
            'company_id': False,
        })
        # compute stored fields, for example address dependent fields
        partner.flush()
        vals['partner_id'] = partner.id
        self.clear_caches()
        company = super(ResCompany, self).create(vals)
        # The write is made on the user to set it automatically in the multi company group.
        self.env.user.write({'company_ids': [(4, company.id)]})

        # Make sure that the selected currency is enabled
        if vals.get('currency_id'):
            currency = self.env['res.currency'].browse(vals['currency_id'])
            if not currency.active:
                currency.write({'active': True})
        return company

    def write(self, vals):

        if 'property_account_receivable_advance_id' in vals and 'property_account_payable_advance_id' in vals:
            if vals['property_account_receivable_advance_id'] != False and vals['property_account_payable_advance_id'] != False:
                self.generate_properties(receivable_advance_id=vals['property_account_receivable_advance_id'],
                                         payable_advance_id=vals['property_account_payable_advance_id'])
        elif 'property_account_payable_advance_id' in vals:
            if vals['property_account_payable_advance_id'] != False:
                self.generate_properties(payable_advance_id=vals['property_account_payable_advance_id'], receivable_advance_id=False)
        elif 'property_account_receivable_advance_id' in vals:
            if vals['property_account_receivable_advance_id'] != False:
                self.generate_properties(receivable_advance_id=vals['property_account_receivable_advance_id'], payable_advance_id=False)

        return super(ResCompany, self).write(vals)


    def generate_properties(self, payable_advance_id=False, receivable_advance_id=False):
        """
        This method used for creating properties.

        :param acc_template_ref: Mapping between ids of account templates and real accounts created from them
        :param company_id: company to generate properties for.
        :returns: True
        """
        self.ensure_one()
        PropertyObj = self.env['ir.property']

        todo_list = [
            ('property_account_payable_advance_id', 'res.partner', payable_advance_id),
            ('property_account_receivable_advance_id', 'res.partner', receivable_advance_id),

        ]

        for field, model, account in todo_list:
            if account:
                PropertyObj._set_default(field, model, account, company=self.env.company.id)

        return True