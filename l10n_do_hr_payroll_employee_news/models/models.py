# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import datetime
from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class PayslipInputImport(models.Model):
    _name = 'payslip.input.import'
    _description = 'Import Payslip Input'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            values['name'] = self.env[
                'ir.sequence'].next_by_code('seqemp_news.seqemp_news')
        return super(PayslipInputImport, self).create(vals_list)

    name = fields.Char(string='Employee News Id')

    input_id = fields.Many2one(comodel_name='hr.payslip.input.type', store=True, string='Novedad')
    code = fields.Char(related='input_id.code', string='Codigo')
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Empleado', store=True, required=True)
    emp_id = fields.Char(related='employee_id.emp_id', string='Codigo Empleado')
    structure_class_id = fields.Many2one(related='employee_id.structure_class_id', store=True, string='Clase')
    amount = fields.Float(string='Importe', digits=(16, 4))  # digits=dp.get_precision('Monto Novedad'))
    frecuency_type = fields.Selection(
        selection=[
            ('fixed', 'Fijo'),
            ('variable', 'Variable'),
            ('slip', 'Recibo')
        ],
        string='Tipo de frecuencia',
        default='fixed')

    apply_in = fields.Many2one(
        comodel_name='hr.payslip.run',
        string='Aplicar en',
        domain="[('state', '=', 'verify')]"
    )

    splid_id = fields.Many2one(
        comodel_name='hr.payslip',
        string='Recibo',
        domain="[('state', '=', 'verify')]"
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Borrador'),
            ('confirm', 'Confirmado'),
            ('assign','Asignado'),
            ('closed','Cerrada'),
            ('detained', 'Retenido'),
            ('cancel', 'Cancelado')
        ], string='Estado',
        default='draft'
    )

    # frecuency_number = fields.Integer(string='Numero de Quincenas', default=1)
    start_date = fields.Date(string='Fecha inicial', )
    end_date = fields.Date(string='Fecha final')  # , compute='_calc_date_end', store=True)
    company_id = fields.Many2one(comodel_name='res.company', default=lambda self: self.env.company)

    notes = fields.Text('Descripcion/Notas')

    @api.depends('input_id', 'code')
    def name_get(self):
        result = []
        for r in self:
            name = '[%s] %s' % (r.code, r.input_id.name)
            result.append((r.id, name))
        return result

    @api.onchange('frecuency_type')
    def onchange_frecuency_type(self):
        if self.frecuency_type == 'variable':
            self.start_date = False
            self.end_date = False

    # def assign_rule_in_lote(self):
    #     """Asigna la novedad a un lote una vez confirmado."""
    #     for record in self:
    #         # Verificar que la novedad esté confirmada
    #         if record.state != 'confirm':
    #             continue
    # 
    #         # Validación de fechas para frecuencia fija
    #         if record.frecuency_type == 'fixed':
    #             if not record.start_date:
    #                 raise UserError("Debe especificar una fecha de inicio para el tipo de frecuencia 'fixed'.")
    # 
    #             # Validar que la fecha de inicio no sea mayor a la de finalización
    #             if record.end_date and record.start_date > record.end_date:
    #                 raise UserError("La fecha de inicio no puede ser mayor a la fecha de finalización.")
    # 
    #         # Buscar las nóminas relacionadas según la configuración del registro
    #         domain = [
    #             ('state', '=', 'verify'),
    #             ('employee_id', '=', record.employee_id.id)
    #         ]
    #         if record.frecuency_type == 'fixed':
    #             domain += [
    #                 '|',  # Verificar periodo de validez de la novedad
    #                 ('date_from', '<=', record.end_date or record.start_date),
    #                 ('date_to', '>=', record.start_date)
    #             ]
    # 
    #         if record.apply_in:
    #             domain.append(('payslip_run_id', '=', record.apply_in.id))
    #         elif record.splid_id:
    #             domain.append(('id', '=', record.splid_id.id))
    # 
    #         payslips = self.env['hr.payslip'].search(domain)
    # 
    #         if not payslips:
    #             # Manejar casos donde no se encuentran nóminas
    #             record.notes = (
    #                                        record.notes or '') + "\nDeclinado: No se encontró ningún lote confirmado para payslip_run_name: %s" % (
    #                                record.apply_in.name if record.apply_in else 'N/A')
    #             record.state = 'detained'
    #             continue
    # 
    #         # Crear entradas de nómina y asignar
    #         for payslip in payslips:
    #             # Validar si la estructura del slip incluye la novedad
    #             if record.frecuency_type == 'fixed' and payslip.struct_id.id not in record.input_id.struct_ids.ids:
    #                 continue
    # 
    #             self.env['hr.payslip.input'].create({
    #                 'name': record.input_id.name or 'Novedad',  # Nombre o descripción
    #                 'payslip_id': payslip.id,  # Nómina asociada
    #                 'input_type_id': record.input_id.id,  # Tipo de entrada (novedad)
    #                 'amount': record.amount,  # Monto de la novedad
    #                 'sequence': 10,  # Secuencia predeterminada
    #             })
    #             payslip.compute_sheet()  # Recalcular la nómina
    # 
    #             # Actualizar las notas del registro
    #             record.notes = (record.notes or '') + "\nSe ha asignado al %s: %s" % (
    #                 'Batch/Lote' if record.apply_in else 'slip',
    #                 record.apply_in.name if record.apply_in else payslip.name
    #             )
    # 
    #         # Cambiar el estado del registro a 'assign'
    #         record.state = 'assign'

    def assign_rule_in_lote(self):
        """Asigna la novedad a un lote una vez confirmado."""
        for record in self:
            # Verificamos si la novedad está en estado confirmado
            if record.state == 'confirm':
                # Cambiar el tipo de frecuencia cuando sea fijo
                if record.frecuency_type == 'fixed':
                    # Validar start_date y end_date
                    if record.start_date:
                        start_date = record.start_date if isinstance(record.start_date, str) else record.start_date.strftime('%Y-%m-%d')
                        end_date = record.end_date if record.end_date and isinstance(record.end_date, str) else (record.end_date.strftime('%Y-%m-%d') if record.end_date else None)
                        start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
                        end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d') if end_date else None
                        if end_date and start_date > end_date:
                            raise UserError("La fecha de inicio no puede ser mayor a la fecha de finalización.")
                    else:
                        raise UserError("Debe especificar una fecha de inicio para el tipo de frecuencia 'fixed'.")

                    # Obtener las nóminas del lote en estado verify
                    payslips = self.env['hr.payslip'].search(
                        [('state', '=', 'verify'), ('employee_id', '=', record.employee_id.id)])
                    for payslip in payslips:
                        date_from = payslip.date_from if isinstance(payslip.date_from,
                                                                    str) else payslip.date_from.strftime('%Y-%m-%d')
                        date_to = payslip.date_to if isinstance(payslip.date_to, str) else payslip.date_to.strftime(
                            '%Y-%m-%d')
                        date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d')
                        date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d')

                        # Verificar si la entrada pertenece a la estructura
                        if payslip.struct_id.id in record.input_id.struct_ids.ids\
                                and (start_date <= date_to and (not end_date or end_date >= date_from)):
                            self.env['hr.payslip.input'].create({
                            'name': record.input_id.name or 'Novedad',  # Nombre o descripción de la entrada
                            'payslip_id': payslip.id,  # Nómina a la que se asignará
                            'input_type_id': record.input_id.id,  # Tipo de entrada (novedad)
                            'amount': record.amount,  # Importe de la novedad
                            'sequence': 10,  # Secuencia por defecto
                            })
                            payslip.compute_sheet()  # Recalcular la nómina
                            record.notes = (record.notes or '') + "\nSe ha asignado al slip: %s" % payslip.name

                        # Actualizar el estado del registro a 'assign'
                    record.state = 'assign'
                    return
                if record.apply_in:
                    # Obtener las nóminas del lote
                    payslips = self.env['hr.payslip'].search([
                        ('payslip_run_id', '=', record.apply_in.id),
                        ('state', '=', 'verify'),
                        ('employee_id', '=', record.employee_id.id)
                    ])
                else:
                    # Obtener recibo
                    payslips = self.env['hr.payslip'].search([
                        ('id', '=', record.splid_id.id),
                        ('state', '=', 'verify'),
                        ('employee_id', '=', record.employee_id.id)
                    ])


                if not payslips:
                    # Actualizar la descripción indicando que no se encontró ningún lote confirmado
                    record.notes = (record.notes or '') + "\nDeclinado: No se encontró ningún lote confirmado para payslip_run_name: %s" % record.apply_in.name
                    # Cambiar el estado del registro a 'detained'
                    record.state = 'detained'
                else:
                    # Crear entradas de nómina (hr.payslip.input) para cada nómina
                    for payslip in payslips:
                        self.env['hr.payslip.input'].create({
                            'name': record.input_id.name or 'Novedad',  # Nombre o descripción de la entrada
                            'payslip_id': payslip.id,  # Nómina a la que se asignará
                            'input_type_id': record.input_id.id,  # Tipo de entrada (novedad)
                            'amount': record.amount,  # Importe de la novedad
                            'sequence': 10,  # Secuencia por defecto
                        })
                        payslip.compute_sheet()  # Recalcular la nómina
                        # Actualizar la descripción indicando que no se encontró ningún lote confirmado
                        if record.apply_in:
                            record.notes = (record.notes or '') + "\nSe ha asignado al Batch/Lote: %s" % record.apply_in.name
                        else:
                            record.notes = (record.notes or '') + "\nSe ha asignado al slip: %s" % payslip.name
                    # Cambiar el estado del registro a 'assign'
                    record.state = 'assign'

    def action_confirm(self):
        """Confirma solo las novedades en estado borrador. Si encuentra alguna en otro estado, muestra un mensaje de advertencia."""
        non_draft_records = self.filtered(lambda r: r.state != 'draft')
        if non_draft_records:
            # Crear un mensaje de error mostrando los registros que no están en estado borrador
            error_message = _("Las siguientes novedades no están en estado 'Borrador' y no pueden ser confirmadas:\n")
            error_message += "\n".join(
                [f"- {record.display_name} (Estado: {record.state})" for record in non_draft_records])
            raise UserError(error_message)

        # Confirmar las novedades que están en estado borrador
        for record in self.filtered(lambda r: r.state == 'draft'):
            record.state = 'confirm'
            
    def action_closed(self):
        for rec in self:
            rec.state = 'closed'


    def button_cancel(self):
        """Cancelar la novedad y eliminar la entrada del slip."""
        for record in self:
            if record.apply_in:
                # Buscar las nóminas del lote
                payslips = self.env['hr.payslip'].search([
                    ('payslip_run_id', '=', int(record.apply_in.id)),
                    ('state', '=', 'verify'),
                    ('employee_id', '=', int(record.employee_id.id))

                ])
            else:
                # Buscar recibo
                payslips = self.env['hr.payslip'].search([
                    ('id', '=', int(record.splid_id.id)),
                    ('state', '=', 'verify'),
                    ('employee_id', '=', int(record.employee_id.id))
                ])
            # if not payslips:
            #     record.state = 'cancel'
            #     raise UserError(
            #         "No se puede cancelar esta novedad porque no está aplicada a ningún recibo o lote.")
            # Buscar las nóminas del lote en estado 'verify'
            # payslips_verify = self.env['hr.payslip'].search(
            #     [('payslip_run_id', '=', record.apply_in.id), ('state', '=', 'verify')])
            if payslips:
                # Buscar y eliminar las entradas de nómina asociadas a la novedad
                payslip_inputs = self.env['hr.payslip.input'].search(
                    [('payslip_id', 'in', payslips.ids), ('input_type_id', '=', record.input_id.id)])
                if payslip_inputs:
                    payslip_inputs.unlink()  # Eliminar las entradas de nómina
                # Recalcular las nóminas afectadas
                for payslip in payslips:
                    payslip.compute_sheet()  # Recalcular la nómina

            # Actualizar el estado de la novedad a 'cancel'
            record.state = 'cancel'
            # Opcionalmente, puedes agregar una nota en la descripción
            record.notes = (record.notes or '') + "\nCancelado: La entrada fue eliminada del slip."

    def button_draft(self):
        """Restablece la novedad a estado borrador."""
        for record in self:
            # Cambiar el estado a 'draft'
            record.state = 'draft'
            # Opcionalmente, puedes limpiar otras variables o campos si es necesario
            record.notes = (record.notes or '') + "\nLa novedad ha sido restablecida a borrador."

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("Solo se pueden eliminar las novedades en estado borrador.")
        return super(PayslipInputImport, self).unlink()


class ResCompany(models.Model):
    _inherit = 'res.company'

    hr_payroll_account_pay = fields.Many2one(
        comodel_name='account.account',
        string='Cuenta de Nomina por Pagar por Defecto',
        domain="[('account_type', 'in', ('liability_payable', 'liability_credit_card','liability_current','liability_no_current'))]"
    )

    hr_payroll_account_charge = fields.Many2one(
        comodel_name='account.account',
        string='Cuenta de Nomina por Cobrar por Defecto',
        domain="[('account_type', '=', 'asset_receivable')]"
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    hr_payroll_account_pay = fields.Many2one(
        related='company_id.hr_payroll_account_pay',
        readonly=False
    )

    hr_payroll_account_charge = fields.Many2one(
        related='company_id.hr_payroll_account_charge',
        readonly=False
    )
