# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.

import json

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError



class AccountTax(models.Model):
    _inherit = 'account.tax'


    isr_retention_type = fields.Selection(
        [('01', 'Alquileres'),
         ('02', 'Honorarios por Servicios'),
         ('03', 'Otras Rentas'),
         ('04', 'Rentas Presuntas'),
         ('05', 'Intereses Pagados a Personas Jurídicas'),
         ('06', 'Intereses Pagados a Personas Físicas'),
         ('07', 'Retención por Proveedores del Estado'),
         ('08', 'Juegos Telefónicos')],
        string="Tipo de Retención en ISR",store=True)

    sale_itbis_retention_type = fields.Selection(
        [('01', 'RETENCIONES (Norma No. 08-04)'),
         ('02', 'VENTAS DE PASAJES DE TRANSPORTE AÉREO (Norma No. 02-05) (BSP-IATA)'),
         ('03', 'OTRAS RETENCIONES (Norma No. 02-05)'),
         ('04', 'VENTAS DE PAQUETES DE ALOJAMIENTO Y OCUPACIÓN'),
         ('05', 'ENTIDADES DEL ESTADO'),
         ('06', 'PAGOS COMPUTABLES POR ITBIS PERCIBIDO'),],
        string="Tipo de Retención en ITBIS en Venta", store=True)

    purchase_itbis_retention_type = fields.Selection(
        [('01', 'SERVICIOS SUJETOS A RETENCION PERSONAS FISICAS'),
         ('02', 'SERVICIOS SUJETOS A RETENCION ENTIDADES NO LUCRATIVAS (Norma No. 01-11)'),
         ('03', 'SERVICIOS SUJETOS A RETENCION SOCIEDADES (Norma No. 07-09)'),
         ('04', 'SERVICIOS SUJETOS A RETENCION SOCIEDADES (Norma No. 02-05 y 07-07)'),
         ('05', 'RETENCION A CONTRIBUYENTES ACOGIDOS AL RST (Operaciones Gravadas al 18%)'),
         ('06', 'RETENCION A CONTRIBUYENTES ACOGIDOS AL RST (Operaciones Gravadas al 16%)'),
         ('07', 'BIENES SUJETOS A RETENCION DE COMPROBANTE DE COMPRAS (Operaciones Gravadas al 18%) (Norma No. 05-19)'),
         ('08', 'BIENES SUJETOS A RETENCION DE COMPROBANTE DE COMPRAS (Operaciones Gravadas al 16%) (Norma No. 05-19)'),],
        string="Tipo de Retención en ITBIS en Compra", store=True)

    is_tc_comision = fields.Boolean(string='Es comision de TC?',
                                                          help="Impuesto o cargo relacionado a la comision de una empresa intermediaria "
                                                               "de transacciones por TC (Azul, Cardnet, Visanet, etc)", default=False)

    is_tc_extra = fields.Boolean(string='Es comision extra de TC?',
                                    help="Impuesto o cargo relacionado a la comision de una empresa intermediaria "
                                         "de transacciones por TC (Azul, Cardnet, Visanet, etc)", default=False)

    is_import = fields.Boolean(string='Es ITBIS en importacion?',
                                    help="Cotejar si el impuesto esta relacionado a un ITBIS en importacion, "
                                         "esto permitira considerarlo para el IT1")

    is_itbis = fields.Boolean(string='Es un ITBIS de retencion?',
                                    compute="is_retention_type")

    is_isr = fields.Boolean(string='Es un ISR de retencion?',
                                  compute="is_retention_type")

    @api.onchange('is_tc_comision', 'is_tc_extra')
    def validation_tc_comision(self):
        for rec in self:
            if rec.is_tc_comision == True and rec.is_tc_extra == True:
                raise UserError(_("No puede asignar una comision y un una comision extra a un mismo impuesto."))


    @api.depends('amount', 'is_tc_comision')
    def is_retention_type(self):
        for rec in self:
            if rec.amount < 0 and rec.is_tc_comision == False and "ITBIS" in rec.tax_group_id.name:
                rec.is_itbis = True
                rec.is_isr = False
            elif rec.amount < 0 and rec.is_tc_comision == False and "ISR" in rec.tax_group_id.name:
                rec.is_itbis = False
                rec.is_isr = True
            else:
                rec.is_itbis = False
                rec.is_isr = False


    calculate_ret_itbis_basesubtotal = fields.Boolean(string='Calcular la retencion del 2% en base al subtotal de la factura?',
                                    help="Como la mayoria de las companias intermediarias cobran la retencion por norma 08-04 "
                                         "en base al subtotal de la factura y no del itbis, esta opcion esta disponible.", default=True)