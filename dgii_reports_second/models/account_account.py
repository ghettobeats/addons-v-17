# Part of Domincana Premium. See LICENSE file for full copyright and
# licensing details.
# © 2018 José López <jlopez@indexa.do>

from odoo import models, fields


class AccountAccount(models.Model):
    _inherit = 'account.account'

    account_fiscal_type = fields.Selection([
        ('A08', 'A08 - Otras Operaciones (Positivas)'),
        ('A09', 'A09 - Otras Operaciones (Negativas)'),
        ('A19', 'A19 - Ingresos por Operaciones (No Financieros)'),
        ('A20', 'A20 - Ingresos Financieros'),
        ('A21', 'A21 - Ingresos Extraordinarios'),
        ('A22', 'A22 - Ingresos por Arrendamientos'),
        ('A23', 'A23 - Ingresos por Ventas de Activos Depreciables'),
        ('A24', 'A24 - Otros Ingresos'),
        ('A26', 'A26 - ITBIS Pagado en Importaciones'),
        ('A27', 'A27 - '
         'ITBIS Pagado en Importaciones para la Producción de Bienes Exentos'),
        ('A29', 'A29 - '
         'ITBIS en Bienes o Servicios sujetos a Proporcionalidad'),
        ('A30', 'A30 - ITBIS en Importaciones sujetos a Proporcionalidad'),
        ('A34', 'A34 - Pagos Computables por Retenciones (N08-04)'),
        ('A35', 'A35 - '
         'Pagos Computables por Boletos Aéreos (N02-05) (BSP-IATA)'),
        ('A36', 'A36 - Pagos Computables por otras Retenciones (N02-05)'),
        ('A37', 'A37 - '
         'Pagos Computables por Paquetes de Alojamiento y Ocupación'),
        ('A38', 'A38 - '
         'Crédito por retención realizada por Entidades del Estado'),
        ('A41', 'A41 - Dirección Técnica (N07-07)'),
        ('A42', 'A42 - Contrato de Administración (N07-07)'),
        ('A43', 'A43 - Asesorías / Honorarios'),
        ('A46', 'A46 - Ventas de Bienes en Concesión'),
        ('A47', 'A47 - Ventas de Servicios en Nombre de Terceros'),
        ('A50', 'A50 - Total Notas de Crédito emitidas con más de 30 días'),
        ('A51', 'A51 - ITBIS llevado al Costo'),
        ('I02', 'I02 - Ingresos por Exportaciones de Bienes o Servicios'),
        ('I03', 'I03 - '
         'Ingresos por ventas locales de bienes o servicios exentos'),
        ('I04', 'I04 - '
         'Ingresos por ventas de bienes o servicios exentos por destino'),
        ('I13', 'I13 - '
         'Operaciones gravadas por ventas de Activos Depreciables'
         '(categoría 2 y 3)'),
        ('I28', 'I28 - '
         'Saldos Compensables Autorizados (Otros Impuestos) y/o Reembolsos'),
        ('I35', 'I35 - Recargos'), ('I36', 'I36 - Interés Indemnizatorio'),
        ('I39', 'I39 - Servicios sujetos a Retención Personas Físicas'),
        ('ISR', 'Retención de Renta por Terceros')
    ], string='Account Fiscal Type', copy=False)

    account_retribution_type = fields.Selection([
        ('R10', 'Asignacion de vehiculo: 27% del 10%'),
        ('R20', 'Asignacion de vehiculo: 27% del 20%'),
        ('R30', 'Asignacion de vehiculo: 27% del 30%'),
        ('R40', 'Asignacion de vehiculo: 27% del 40%'),
        ('RA', 'Otras retribuciones complementarias: 27% sobre el total'),
    ], string='Account Retribution Type', copy=False)

    calcular_ingresos_financieros_anexoa = fields.Boolean(string='Calcular ingresos financieros en Anexo A?',
                                                          help="Calcular como ingreso financiero las cuentas del catalogo que tengan este "
                                                               "concepto asignado?", default=False)
    es_caja_chica = fields.Boolean('Es caja chica?')


    user_type_name = fields.Char(related='user_type_id.name')
    old_account = fields.Char('Cuenta vieja', store=True)
    es_cuenta_empresarial = fields.Boolean('Cuenta empresarial?', store=True)
    es_cuenta_turistica = fields.Boolean('Cuenta turistica?', store=True)

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"


    def button_undo_reconciliation(self):
        ''' Undo the reconciliation mades on the statement line and reset their journal items
        to their original states.
        '''
        self.line_ids.remove_move_reconcile()
        self.payment_ids.unlink()

        for st_line in self:

            st_line.with_context(force_delete=True).write({
                'to_check': False,
                'line_ids': [(5, 0)] + [(0, 0, line_vals) for line_vals in st_line._prepare_move_line_default_vals()],
                'partner_id': False,
            })

