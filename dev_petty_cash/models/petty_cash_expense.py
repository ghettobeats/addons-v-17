# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################
import logging
from odoo.exceptions import ValidationError, UserError
from odoo import _, api, models, fields, SUPERUSER_ID
from random import randint

_logger = logging.getLogger(__name__)

try:
    from stdnum.do.ncf import is_valid
except (ImportError, IOError) as err:
    _logger.debug(err)

class CajaChicaEstados(models.Model):
    _name = "caja.chica.estados"
    _description = "Estados de Caja Chica"
    _rec_name = 'name'
    _order = 'sequence'

    def _default_team_ids(self):
        team_id = self.env.context.get('default_caja_id')
        if team_id:
            return [(4, team_id, 0)]

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    name = fields.Char(string='Nombre de Estado')
    sequence = fields.Integer('Sequence', help="Determine the display order",
                              index=True)

    nombre_boton = fields.Char(string="Nombre en Boton para Aprobacion")

    boton_final = fields.Boolean("Estado Final", default=False)

    categoria = fields.Selection([
        ('approval', 'Aprobaciones'),
        ('invoice', 'Emision de Facturas'),
        ('payment', 'Emision de Pago'),
        ('cancel', 'Cancelado')
    ], 'Categorias')

    condition = fields.Text(string='Conditions')

    next_stage_id = fields.Many2one(
        'caja.chica.estados', string='Estado Siguiente',)


    cajas_ids = fields.Many2many(
        'tipo.caja.chica', relation='caja_chica_stage_rel', string='Tipos de Cajas Permitidos',
        default=_default_team_ids,
        help='Specific team that uses this stage. Other teams will not be able to see or use this stage.')

    active = fields.Boolean(default=True)

    usuarios_permitidos_ids = fields.Many2many('res.users', string="Usuarios Permitidos", )

    # @api.constrains('cajas_ids')
    # def block_more_than_one_caja(self):
    #     for rec in self:
    #         if len(rec.cajas_ids) > 1:
    #             raise UserError(_("No puede asignar mas de un tipo de caja al grupo, "
    #                               "favor crear otro estado nuevo y asignarle el grupo."))


class TipoCajaChica(models.Model):
    _name = 'tipo.caja.chica'
    _description = 'Tipo Caja Chica'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Cuenta Analitica Por Defecto')
    def action_view_cajas(self):
        action = self.env["ir.actions.actions"]._for_xml_id("dev_petty_cash.action_petty_cash_expense")
        action['context'] = {'default_tipo_caja_id':self.id}
        action['domain'] = [('tipo_caja_id', 'in', self.ids)]
        return action

    def _default_stage_ids(self):
        default_stage = self.env['caja.chica.estados'].search([('name', '=', _('Borrador'))], limit=1)
        return [(4, default_stage.id)]

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', help="Determine the display order",
                              index=True)
    team_head = fields.Many2one('res.users', 'Cabecera de Equipo', )
    team_members = fields.Many2many('res.users', string="Usuarios Permitidos",)

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    balance_caja_chica = fields.Monetary("Balance en Caja", compute="_get_balance")

    currency_id = fields.Many2one(related="petty_journal_id.currency_id")

    def _get_balance(self):
        for expense in self:
            balance = 0.0
            for line in self.env['account.move.line'].search(
                    [('account_id', '=', expense.petty_journal_id.default_account_id.id),
                     ('move_id.state', '=', 'posted')]):
                balance += line.amount_currency
            expense.balance_caja_chica = abs(balance)

    def _get_default_color(self):
        return randint(1, 11)

    color = fields.Integer(string='Color Index', default=_get_default_color)

    stage_ids = fields.Many2many(
        'caja.chica.estados', relation='caja_chica_stage_rel', string='Estados',
        default=_default_stage_ids,
        help="Stages the team will use. This team's tickets will only be able to be in these stages.")

    petty_journal_id = fields.Many2one('account.journal', string='Diario De Caja Chica', tracking=True)
    invoice_journal_id = fields.Many2one('account.journal', string='Diario De Facturas Por Defecto', tracking=True)
    payment_journal_id = fields.Many2one('account.journal', string='Diario de Pagos')


    # def action_view_cajas_chicas(self):
    #     self.ensure_one()
    #     slas = self.env['petty.cash.expense'].sudo().search(
    #         [('tipo_caja_id', '=', self.id)])
    #     action = self.env["ir.actions.actions"]._for_xml_id(
    #         "sh_helpdesk.helpdesk_ticket_action")
    #     if len(slas) > 1:
    #         action['domain'] = [('id', 'in', slas.ids)]
    #     elif len(slas) == 1:
    #         form_view = [
    #             (self.env.ref('sh_helpdesk.helpdesk_ticket_form_view').id, 'form')]
    #         if 'views' in action:
    #             action['views'] = form_view + \
    #                               [(state, view)
    #                                for state, view in action['views'] if view != 'form']
    #         else:
    #             action['views'] = form_view
    #         action['res_id'] = slas.id
    #     else:
    #         action = {'type': 'ir.actions.act_window_close'}
    #     return action

    def _determine_stage(self):
        """ Get a dict with the stage (per team) that should be set as first to a created ticket
            :returns a mapping of team identifier with the stage (maybe an empty record).
            :rtype : dict (key=team_id, value=record of helpdesk.stage)
        """
        result = dict.fromkeys(self.ids, self.env['caja.chica.estados'])
        for team in self:
            result[team.id] = self.env['caja.chica.estados'].search([('cajas_ids', 'in', team.id)], order='sequence',
                                                                limit=1)
        return result


class petty_cash_expense(models.Model):
    _name = 'petty.cash.expense'
    _description = 'Cuadres de Caja Chica'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    attachment_number = fields.Integer('Number of Attachments', compute='_compute_attachment_number')


    def _compute_attachment_number(self):
        for sheet in self:
            sheet.attachment_number = sum(sheet.expense_lines.mapped('attachment_number'))


    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', 'petty.expense.lines'), ('res_id', 'in', self.expense_lines.ids)]
        res['context'] = {
            'default_res_model': 'petty.cash.expense',
            'default_res_id': self.id,
            'create': False,
            'edit': False,
        }
        return res
    
    @api.model
    def _get_request_by(self):
        employee_id =self.env['hr.employee'].search([('user_id','=',self.env.user.id)])
        return employee_id.id or False

    def _default_stage_id(self):
        rec = self.env['caja.chica.estados'].search([], limit=1,
                                                         order='sequence ASC')
        return rec.id if rec else None

    @api.model
    def _read_group_stage_ids(self, categories, domain, order):
        category_ids = categories._search([], order=order,
                                          access_rights_uid=SUPERUSER_ID)
        return categories.browse(category_ids)

    @api.depends('tipo_caja_id')
    def _compute_user_and_stage_ids(self):
        for ticket in self.filtered(lambda ticket: ticket.tipo_caja_id):
            if not ticket.stage_id or ticket.stage_id not in ticket.tipo_caja_id.stage_ids:
                ticket.stage_id = ticket.tipo_caja_id._determine_stage()[ticket.tipo_caja_id.id]

    def _default_team_id(self):
        team_id = self.env['tipo.caja.chica'].search([('team_members', 'in', self.env.uid)], limit=1).id
        if not team_id:
            team_id = self.env['tipo.caja.chica'].search([], limit=1).id
        return team_id
    
    name = fields.Char('Name', default='/', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Responsable', default=_get_request_by, tracking=True)

    petty_journal_id = fields.Many2one(related="tipo_caja_id.petty_journal_id")
    invoice_journal_id = fields.Many2one(related="tipo_caja_id.invoice_journal_id")
    payment_journal_id = fields.Many2one(related="tipo_caja_id.payment_journal_id")

    date = fields.Date('Fecha', copy=False, default=fields.Datetime.now)
    currency_id = fields.Many2one('res.currency', string='Moneda', default=lambda self:self.env.company.currency_id)
    user_id = fields.Many2one('res.users', string='Usuario', default=lambda self:self.env.user)
    company_id = fields.Many2one('res.company', default=lambda self:self.env.company)

    nombre_boton = fields.Char(related="stage_id.nombre_boton")

    boton_final = fields.Boolean(related="stage_id.boton_final")

    categoria = fields.Selection(related="stage_id.categoria")

    next_stage_id = fields.Many2one(related="stage_id.next_stage_id" )

    analytic_account_id = fields.Many2one(related="tipo_caja_id.analytic_account_id")

    tipo_caja_id = fields.Many2one('tipo.caja.chica', string='Tipo de Caja', default=_default_team_id, index=True)

    stage_id = fields.Many2one(
        'caja.chica.estados', string='Estado', compute='_compute_user_and_stage_ids', store=True,
        readonly=False, ondelete='restrict', tracking=True, group_expand='_read_group_stage_ids',
        copy=False, index=True, domain="[('cajas_ids', '=', tipo_caja_id)]")


    expense_lines = fields.One2many('petty.expense.lines','expense_id', string='Expense Lines',copy=True)
    payment_ids = fields.Many2many('account.payment', string='Payments', copy=False)
    balance = fields.Monetary('Balance', compute='set_balance', store=True)
    expense_amount = fields.Monetary('Monto de Gastos', compute='_get_expense_amount', tracking=True)
    request_ids = fields.Many2many('petty.cash.request', string='Solicitudes de Reposicion')
    remaining_balace = fields.Monetary('Monto Restante', compute='_get_expense_amount')
    note = fields.Text('Notas')
    payment_count = fields.Integer('Cuenta de Pagos', compute='_count_payment')
    invoice_count = fields.Integer('Cuenta de Facturas', compute='_count_invoice')
    
    @api.depends('payment_ids')
    def action_view_payment(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_account_payments")
        action['context']={}
        action['domain'] = [('id','in',self.payment_ids.ids)]
        return action

    @api.depends('expense_lines')
    def action_view_invoices(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
        action['context']={}
        action['domain'] = [('id','in',self.expense_lines.account_move_id.ids)]
        return action
    
    @api.depends('payment_ids')
    def _count_payment(self):
        for expense in self:
            expense.payment_count = len(expense.payment_ids)

    @api.depends('expense_lines')
    def _count_invoice(self):
        for expense in self:
            expense.invoice_count = len(expense.expense_lines.account_move_id.ids)
            
    @api.depends('expense_lines')
    def _get_expense_amount(self):
        for expense in self:
            amount = 0
            for line in expense.expense_lines:
                amount += line.total_amount
            expense.expense_amount = amount
            expense.remaining_balace = expense.balance - expense.expense_amount

    @api.onchange('x_balance_manual')
    def set_balance(self):
        for expense in self:
            expense.balance = expense.x_balance_manual
        self._get_expense_amount()
            

    # @api.depends('employee_id','petty_journal_id','currency_id','expense_lines')
    # def _get_balance(self):
    #     for expense in self:
    #         balance = 0.0
    #         _logger.warning(f"--------------BALANCE INTERNO SIN PROCESAR: {abs(expense.balance)}--------------")
    #         for line in self.env['account.move.line'].search(
    #                 [('account_id', '=', expense.petty_journal_id.default_account_id.id),
    #                  ('move_id.state', '=', 'posted')]):
    #             balance += line.amount_currency
    #         _logger.warning(f"--------------BALANCE INTERNO: {abs(expense.balance)}--------------")
    #         expense.balance = abs(balance)
        
    
    def create_payment(self):
        account_ids = []
        for line in self.expense_lines:
            if line.account_id.id not in account_ids:
                account_ids.append(line.account_id.id)
                
        payment_ids= []
        for account in self.expense_lines.account_move_id.filtered(lambda x: x.payment_state == 'not_paid'):
            amount = abs(account.amount_total)
            vals={
                'date': account.invoice_date,
                'amount': amount or 0.0,
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'ref': account.ref,
                'journal_id': self.payment_journal_id and self.payment_journal_id.id or False,
                'currency_id': account.currency_id.id,
                'partner_id': account.partner_id.id,
            }
            payment_id = self.env['account.payment'].sudo().create(vals)
            if payment_id:
                payment_id.action_post()
                payment_ids.append(payment_id.id)
        self.payment_ids = [(6,0, payment_ids)]

        self.reconcile_payment()
            
            
    def reconcile_payment(self):

        for payment in self.payment_ids:
            credit_move_lines = self.env['account.move.line']
            debit_move_lines = self.env['account.move.line']
            account_id = self.petty_journal_id.default_account_id
            if payment.move_id:
                d_line = payment.move_id.line_ids.filtered(lambda x: x.debit > 0 and x.account_id.reconcile == True)
                res_amount = abs(d_line.amount_residual_currency)
                if res_amount:
                    debit_move_lines += d_line
            for mov in self.expense_lines.account_move_id.\
                    line_ids.filtered(lambda x: x.credit > 0 and x.account_id.reconcile == True):
                if mov.move_id.partner_id.id == payment.partner_id.id:
                    credit_move_lines += mov
        
            if debit_move_lines and credit_move_lines:
                (credit_move_lines + debit_move_lines).reconcile()
        return True
    
    @api.onchange("stage_id","expense_amount","balance")
    def action_cofirm(self):
        if self.balance <= self.expense_amount and self.stage_id.categoria == 'invoice':
            raise ValidationError(_("La Caja chica solo tiene un balance de %s. Favor realizar una solicitud adicional.")%(self.balance))

        
    def action_cancel(self):
        for rec in self:
            stage = self.env['caja.chica.estados'].search([('categoria','=','cancel'),('cajas_ids', 'in', rec.tipo_caja_id.ids)],limit=1)
            if stage:
                rec.stage_id = stage.id
            else:
                raise UserError(_("No puede cancelar el documento pues este tipo de caja no tiene un estado de cancelado, favor crear uno."))


    def action_next_step(self):
        for rec in self:
            if self.env.user.id in rec.next_stage_id.usuarios_permitidos_ids.ids:
                if rec.categoria == 'invoice' and rec.invoice_count == 0:
                    raise UserError(_("No puede avanzar hasta que se creen los documentos relacionados."))
                else:
                    rec.write({'stage_id':rec.next_stage_id.id})
            else:
                raise UserError(_("No esta autorizado para cambiar de estados la hoja de caja chica."
                                  "Favor consultar las siguientes personas que estan autorizadas: %s",
                                  (','.join(
                                      val.name
                                      for val in rec.next_stage_id.usuarios_permitidos_ids
                                  ))
                                  ))

    faltan_facturas = fields.Boolean("Faltan Facturas?", default=False, compute="faltan_facturas_a_emitir")

    @api.depends('expense_lines')
    def faltan_facturas_a_emitir(self):
        for rec in self:
            fac = len(rec.expense_lines.filtered(lambda x: not x.account_move_id))
            rec.faltan_facturas = True if fac > 0 else False

    faltan_pagos = fields.Boolean("Faltan Pagos?", default=False, compute="faltan_pagos_a_emitir")
    @api.depends('expense_lines')
    def faltan_pagos_a_emitir(self):
        for rec in self:
            fac = len(rec.expense_lines.filtered(lambda x: x.account_move_id.payment_state == 'not_paid'))
            rec.faltan_pagos = True if fac > 0 else False


    def crear_facturas_relacionadas(self):
        for rec in self:
            

            gasto_menor = self.env['account.journal'].search([('name','=','Gasto Menor'),('type','=','purchase')],limit=1)

            factura_gasto_menor = {}
            lista_factura_gasto_menor = []
            factura_proveedor_informal = []
            factura_fiscal = []

            if not rec.invoice_journal_id:
                raise UserError(_("No existe diario de facturas preestablecido en el tipo de caja. Favor asignarlo."))

            employees_div = []

            for exp1 in rec.expense_lines.filtered(lambda x: x.tipo_de_factura_do == 'gasto_menor' and not x.account_move_id):
                if exp1.employee_id:
                    if not exp1.employee_id.id in employees_div:
                        employees_div.append(exp1.employee_id.id)

            for emp in employees_div:
                
                lineas_gasto_menor = []

                if gasto_menor:
                    journal_dev = gasto_menor.id
                else:
                    journal_dev = rec.invoice_journal_id.id if rec.invoice_journal_id else False

                factura_gasto_menor = {
                            'journal_id': journal_dev,
                            'partner_id':exp1.partner_id.id if exp1.partner_id else False,
                            'move_type':'in_invoice',
                            'invoice_date': exp1.date,
                            'l10n_latam_document_number': exp1.ncf if exp1.ncf else False,
                            'ref':exp1.ncf if exp1.ncf else False,
                            'invoice_origin':rec.name,
                            'currency_id':rec.currency_id.id,
                            'caja_chica_id':rec.id,
                            'company_id':rec.company_id.id,
                        }
                for exp1 in rec.expense_lines.filtered(lambda x: x.tipo_de_factura_do == 'gasto_menor' and not x.account_move_id and x.employee_id.id == emp):
                    if exp1.ncf:
                        document_type = self.env['l10n_latam.document.type'].search([('doc_code_prefix','=',exp1.ncf[0:3])],limit=1)
                    else:
                        document_type = self.env['l10n_latam.document.type'].search([('doc_code_prefix','=','B13')],limit=1)

                    factura_gasto_menor['l10n_latam_document_type_id'] = document_type
                    factura_gasto_menor['payment_reference'] = exp1.payment_reference if exp1.payment_reference else False

                    lineas_gasto_menor.append((0,0,{
                        'product_id':exp1.product_id.id if exp1.product_id else False,
                        'quantity': 1,
                        'name':str(exp1.payment_reference) + ', ' + exp1.product_id.name,
                        'product_uom_id': exp1.product_id.uom_id.id if exp1.product_id else False,
                        'account_id': exp1.account_id.id if exp1.account_id else False,
                        'analytic_account_id': exp1.analytic_account_id.id if exp1.analytic_account_id else False,
                        'analytic_tag_ids': [(6,0,exp1.analytic_tag_ids.ids)] if exp1.analytic_tag_ids else False,
                        'price_unit': exp1.unit_amount,
                        'tax_ids': [(6,0,exp1.tax_ids.ids)],
                        'line_caja_chica_id':exp1.id,

                    }))
                
                factura_gasto_menor['invoice_line_ids'] = lineas_gasto_menor

                lista_factura_gasto_menor.append(factura_gasto_menor)
                

            for exp1 in rec.expense_lines.filtered(lambda x: x.tipo_de_factura_do == 'gasto_menor' and not x.account_move_id and x.employee_id.id == False):
                lineas_gasto_menor = []
                if exp1.ncf:
                    document_type = self.env['l10n_latam.document.type'].search([('doc_code_prefix','=',exp1.ncf[0:3])],limit=1)
                else:
                    document_type = self.env['l10n_latam.document.type'].search([('doc_code_prefix','=','B13')],limit=1)

                if gasto_menor:
                    journal_dev = gasto_menor.id
                else:
                    journal_dev = rec.invoice_journal_id.id if rec.invoice_journal_id else False

                if factura_gasto_menor == {}:
                    factura_gasto_menor = {
                        'journal_id':journal_dev,
                        'partner_id':exp1.partner_id.id if exp1.partner_id else False,
                        'move_type':'in_invoice',
                        'invoice_date': exp1.date,
                        'l10n_latam_document_number': exp1.ncf if exp1.ncf else False,
                        'ref':exp1.ncf if exp1.ncf else False,
                        'payment_reference':exp1.payment_reference if exp1.payment_reference else False,
                        'invoice_origin':rec.name,
                        'currency_id':rec.currency_id.id,
                        'caja_chica_id':rec.id,
                        'company_id':rec.company_id.id,
                        'l10n_latam_document_type_id':document_type,
                    }

                lineas_gasto_menor.append((0,0,{
                    'product_id':exp1.product_id.id if exp1.product_id else False,
                    'quantity': 1,
                    'name':str(exp1.payment_reference) + ', ' + exp1.product_id.name,
                    'product_uom_id': exp1.product_id.uom_id.id if exp1.product_id else False,
                    'account_id': exp1.account_id.id if exp1.account_id else False,
                    'analytic_account_id': exp1.analytic_account_id.id if exp1.analytic_account_id else False,
                    'analytic_tag_ids': [(6,0,exp1.analytic_tag_ids.ids)] if exp1.analytic_tag_ids else False,
                    'price_unit': exp1.unit_amount,
                    'tax_ids': [(6,0,exp1.tax_ids.ids)],
                    'line_caja_chica_id':exp1.id,

                }))

                factura_gasto_menor['invoice_line_ids'] = lineas_gasto_menor

                lista_factura_gasto_menor.append(factura_gasto_menor)


            for exp2 in rec.expense_lines.filtered(lambda x: x.tipo_de_factura_do == 'informal' and not x.account_move_id):

                if exp2.ncf:
                    document_type = self.env['l10n_latam.document.type'].search([('doc_code_prefix','=',exp2.ncf[0:3])],limit=1)
                else:
                    document_type = self.env['l10n_latam.document.type'].search([('doc_code_prefix','=','B11')],limit=1)

                factura_proveedor_informal.append({
                    'journal_id':rec.invoice_journal_id.id if rec.invoice_journal_id else False,
                    'partner_id':exp2.partner_id.id if exp2.partner_id else False,
                    'invoice_date': exp2.date,
                    'move_type':'in_invoice',
                    'l10n_latam_document_number': exp2.ncf if exp2.ncf else False,
                    'ref':exp2.ncf if exp2.ncf else False,
                    'payment_reference':exp2.payment_reference if exp2.payment_reference else False,
                    'invoice_origin':rec.name,
                    'currency_id':rec.currency_id.id,
                    'caja_chica_id': rec.id,
                    'company_id':rec.company_id.id,
                    'l10n_latam_document_type_id':document_type,
                    'invoice_line_ids':[(0,0,{
                                        'product_id':exp2.product_id.id if exp2.product_id else False,
                                        'quantity': 1,
                                        'name':str(exp2.payment_reference) + ', ' + exp2.product_id.name,
                                        'product_uom_id': exp2.product_id.uom_id.id if exp2.product_id else False,
                                        'account_id': exp2.account_id.id if exp2.account_id else False,
                                        'analytic_account_id': exp2.analytic_account_id.id if exp2.analytic_account_id else False,
                                        'analytic_tag_ids': [(6,0,exp2.analytic_tag_ids.ids)] if exp2.analytic_tag_ids else False,
                                        'price_unit': exp2.unit_amount,
                                        'tax_ids': [(6,0,exp2.tax_ids.ids)],
                                        'line_caja_chica_id':exp2.id,

                                    })],
                })

            for exp3 in rec.expense_lines.filtered(lambda x: x.tipo_de_factura_do == 'fiscal' and not x.account_move_id):

                if exp3.ncf:
                    document_type = self.env['l10n_latam.document.type'].search([('doc_code_prefix','=',exp3.ncf[0:3])],limit=1)
                else:
                    document_type = False

                factura_fiscal.append({
                    'journal_id': rec.invoice_journal_id.id if rec.invoice_journal_id else False,
                    'partner_id': exp3.partner_id.id if exp3.partner_id else False,
                    'invoice_date': exp3.date,
                    'move_type':'in_invoice',
                    'l10n_latam_document_number': exp3.ncf if exp3.ncf else False,
                    'ref': exp3.ncf if exp3.ncf else False,
                    'payment_reference': exp3.payment_reference if exp3.payment_reference else False,
                    'invoice_origin': rec.name,
                    'currency_id': rec.currency_id.id,
                    'caja_chica_id': rec.id,
                    'company_id':rec.company_id.id,
                    'l10n_latam_document_type_id':document_type,
                    'invoice_line_ids': [(0, 0, {
                        'product_id': exp3.product_id.id if exp3.product_id else False,
                        'quantity':1,
                        'name':str(exp3.payment_reference) + ', ' + exp3.product_id.name,
                        'product_uom_id': exp3.product_id.uom_id.id if exp3.product_id else False,
                        'account_id': exp3.account_id.id if exp3.account_id else False,
                        'analytic_account_id': exp3.analytic_account_id.id if exp3.analytic_account_id else False,
                        'analytic_tag_ids': [(6, 0, exp3.analytic_tag_ids.ids)] if exp3.analytic_tag_ids else False,
                        'price_unit': exp3.unit_amount,
                        'tax_ids': [(6, 0, exp3.tax_ids.ids)],
                        'line_caja_chica_id':exp3.id,

                    })],
                })


            factura_menor_creada = self.env['account.move']

            factura_fiscal_creada = self.env['account.move']
            factura_informal_creada = self.env['account.move']

            for fact in factura_proveedor_informal:
                factura_fiscal_creada += self.env['account.move'].create(fact)

            for fact in factura_fiscal:
                factura_informal_creada += self.env['account.move'].create(fact)

            for fact in lista_factura_gasto_menor:
                factura_menor_creada += self.env['account.move'].create(fact)

            todas_las_facturas = factura_menor_creada + factura_fiscal_creada + factura_informal_creada

            for rec in todas_las_facturas.invoice_line_ids:
                rec.line_caja_chica_id.write({'account_move_id':rec.move_id.id})





        

        
    def unlink(self):
        for request in self:
            if request.stage_id.categoria != 'approval':
                raise ValidationError(_("Solo puede borrar hoja de caja chica en borrador."))
        return super(petty_cash_expense, self).unlink()
        
    @api.model
    def create(self, vals):
        vals.update({
            'name': self.env['ir.sequence'].next_by_code('petty.cash.expense') or '/',
			
        })
        return super(petty_cash_expense, self).create(vals)
        

class petty_expense_lines(models.Model):
    _name = "petty.expense.lines"
    _description = 'Lineas de Caja Chica'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    attachment_ids = fields.Many2many('ir.attachment', 'caja_chica_ir_attachments_rel',
                                      'rental_id', 'attachment_id', string="Adjuntos",
                                      help="Imágenes del vehículo antes del contrato / cualquier archivo adjunto")

    attachment_number = fields.Integer('Number of Attachments', compute='_compute_attachment_number',store=True)


    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group([('res_model', '=', 'petty.expense.lines'), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)


    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', 'petty.expense.lines'), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': 'petty.expense.lines', 'default_res_id': self.id}
        return res

    partner_id = fields.Many2one('res.partner', string='Proveedor', tracking=True,required=True,)

    @api.onchange("partner_id","tipo_de_factura_do")
    def get_partner_domain(self):
        for rec in self:
            if rec.tipo_de_factura_do == 'gasto_menor':
                return {'domain': {'partner_id': [('vat', '=', rec.company_id.partner_id.vat)]}}
            else:
                return {'domain': {'partner_id': [('vat', '!=', rec.company_id.partner_id.vat)]}}

    product_id = fields.Many2one('product.product', string='Producto')
    account_id = fields.Many2one('account.account', string='Cuenta',required=True)
    ncf = fields.Char("NCF", store=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado Relacionado', tracking=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Cuenta Analitica')
    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag", string="Etiquetas Analiticas",
    )
    tax_ids = fields.Many2many('account.tax', 'linea_caja_chica_tax_rel', 'expense_id', 'tax_id',
                               compute='_compute_from_product_id_company_id', store=True, readonly=False,
                               domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase')]",
                               string='Impuestos')
    unit_amount = fields.Float("Monto", compute='_compute_from_product_id_company_id', store=True, required=True,
                               copy=True,digits='Product Price', readonly=False)

    date = fields.Date('Fecha', copy=True, default=lambda self: self.expense_id.date)
    total_amount = fields.Monetary('Total', compute='_compute_amount', store=True, currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    expense_id = fields.Many2one('petty.cash.expense', string='Expense', ondelete='cascade')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    account_move_id = fields.Many2one("account.move","Factura Relacionada", store=True,copy=False)

    tipo_de_factura_do = fields.Selection([
        ('gasto_menor', 'Gasto Menor'),
        ('informal', 'Proveedor Informal'),
        ('fiscal', 'Factura Fiscal')], string='Tipo de Documento',
        track_visibility='onchange', default='gasto_menor', copy=False)

    payment_reference = fields.Char(string="Referencia de Pago", store=True)


    @api.depends('product_id', 'company_id')
    def _compute_from_product_id_company_id(self):
        for expense in self.filtered('product_id'):
            expense = expense.with_company(expense.company_id)
            if not expense.unit_amount:
                expense.unit_amount = expense.product_id.price_compute('standard_price')[expense.product_id.id]
            expense.tax_ids = expense.product_id.supplier_taxes_id.filtered(
                lambda tax: tax.company_id == expense.company_id)

    @api.depends('unit_amount', 'tax_ids', 'currency_id')
    def _compute_amount(self):
        for expense in self:
            taxes = expense.tax_ids.compute_all(expense.unit_amount, expense.currency_id, 1,
                                                expense.product_id, expense.employee_id.user_id.partner_id)
            expense.total_amount = taxes.get('total_included')

    @api.onchange("ncf")
    def _format_document_number(self):
        """ Make validation of Import Dispatch Number
          * making validations on the document_number.
          * format the document_number against a pattern and return it
        """
        document_number = self.ncf
        self.ensure_one()

        if not document_number:
            return False

        msg = "'%s' " + _(" no es un valor valido para el tipo de comprobante. %s")

        # Import NCF Number Validator
        if not is_valid(document_number):
            raise UserError(
                msg
                % (
                    document_number,
                    _("Por favor chequee el numero y registrelo de nuevo."),
                )
            )
        # return document_number


    
    @api.onchange('product_id')
    def onchange_product(self):
        self.ensure_one()
        self = self.with_company(self.expense_id.company_id)
        if self.product_id:
            accounts = self.product_id.product_tmpl_id.get_product_accounts(fiscal_pos=False)
            analytic_account_id = self.product_id.expense_analytic_account_id if hasattr(self.product_id, 'expense_analytic_account_id') else False
            account_id = accounts['expense'] or False
            self.account_id = account_id and account_id.id or False
            self.analytic_account_id = analytic_account_id if analytic_account_id else False
            self.unit_amount = self.product_id.standard_price or 0.0
    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
