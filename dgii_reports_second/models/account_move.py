# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.

import json

from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from datetime import date, datetime

from stdnum.exceptions import *
from stdnum.util import clean, isdigits
import lxml.html
import requests
from stdnum.do.rnc import compact as rnc_compact
from odoo.tools.misc import formatLang, format_date as odoo_format_date, get_lang
import ast


class InvoiceServiceTypeDetail(models.Model):
    _name = 'invoice.service.type.detail'
    _description = "Invoice Service Type Detail"

    name = fields.Char()
    code = fields.Char(size=2)
    parent_code = fields.Char()

    _sql_constraints = [
        ('code_unique', 'unique(code)', _('Code must be unique')),
    ]


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    country_code = fields.Char('Country code')

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    payment_debit_account_id = fields.Many2one('account.account', store=True)
    payment_credit_account_id = fields.Many2one('account.account', store=True)

    view_in_kanban = fields.Boolean("Ver en kanban por default account", store=True, default=True)

    

    def _select_action_to_open(self):
        self.ensure_one()
        if self._context.get('action_name'):
            return self._context.get('action_name')
        elif self.type == 'bank':
            return 'action_bank_statement_tree'
        elif self.type == 'cash':
            return 'action_view_bank_statement_tree'
        elif self.type == 'sale':
            return 'action_move_out_invoice_type'
        elif self.type == 'purchase':
            return 'action_move_in_invoice_type'
        elif self.view_in_kanban:
            return 'action_account_moves_all'
        else:
            return 'action_move_journal_line'

    def open_action(self):
        """return action based on type for related journals"""
        self.ensure_one()
        action_name = self._select_action_to_open()

        # Set 'account.' prefix if missing.
        if '.' not in action_name:
            action_name = 'account.%s' % action_name

        action = self.env["ir.actions.act_window"]._for_xml_id(action_name)

        context = self._context.copy()
        if 'context' in action and type(action['context']) == str and self.type == 'general':
            context.update(ast.literal_eval(action['context'].replace("active_id","")))
        elif 'context' in action and type(action['context']) == str and self.type != 'general':
            context.update(ast.literal_eval(action['context']))
        else:
            context.update(action.get('context', {}))
        action['context'] = context
        if self.type == 'general' and self.view_in_kanban:
            action['context'].update({
                'search_default_account_id': self.default_account_id.id,
            })
        elif self.type == 'general' and not self.view_in_kanban:
            action['context'].update({
                'default_journal_id': self.id,
                'search_default_journal_id': self.id,
            })
        elif self.type != 'general':
            action['context'].update({
                'default_journal_id': self.id,
                'search_default_journal_id': self.id,
            })

        domain_type_field = action['res_model'] == 'account.move.line' and 'move_id.move_type' or 'move_type' # The model can be either account.move or account.move.line

        # Override the domain only if the action was not explicitly specified in order to keep the
        # original action domain.
        if not self._context.get('action_name'):
            if self.type == 'sale':
                action['domain'] = [(domain_type_field, 'in', ('out_invoice', 'out_refund', 'out_receipt'))]
            elif self.type == 'purchase':
                action['domain'] = [(domain_type_field, 'in', ('in_invoice', 'in_refund', 'in_receipt'))]

        return action


class AccountInvoice(models.Model):
    _inherit = 'account.move.line'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')

    def reconcile(self):
        ''' Reconcile the current move lines all together.
        :return: A dictionary representing a summary of what has been done during the reconciliation:
                * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
                * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                        in the involved lines.
                * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
        '''
        results = {}

        if not self:
            return results

        # List unpaid invoices
        not_paid_invoices = self.move_id.filtered(
            lambda move: move.is_invoice(include_receipts=True) and move.payment_state not in ('paid', 'in_payment')
        )

        # ==== Check the lines can be reconciled together ====
        company = None
        account = None
        print("===self==", self)
        for line in self:
            if line.reconciled:
                raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
            if not line.account_id.reconcile and line.account_id.internal_type != 'liquidity':
                raise UserError(_("Account %s does not allow reconciliation. First change the configuration of this account to allow it.")
                                % line.account_id.display_name)
            if line.move_id.state != 'posted':
                raise UserError(_('You can only reconcile posted entries.'))
            if company is None:
                company = line.company_id
            elif line.company_id != company:
                raise UserError(_("Entries doesn't belong to the same company: %s != %s")
                                % (company.display_name, line.company_id.display_name))
            if account is None:
                account = line.account_id
            elif line.account_id != account:
                raise UserError(_("Entries are not from the same account: %s != %s")
                                % (account.display_name, line.account_id.display_name))

        sorted_lines = self.sorted(key=lambda line: (line.date_maturity or line.date, line.currency_id))

        # ==== Collect all involved lines through the existing reconciliation ====

        involved_lines = sorted_lines
        involved_partials = self.env['account.partial.reconcile']
        current_lines = involved_lines
        current_partials = involved_partials
        while current_lines:
            current_partials = (current_lines.matched_debit_ids + current_lines.matched_credit_ids) - current_partials
            involved_partials += current_partials
            current_lines = (current_partials.debit_move_id + current_partials.credit_move_id) - current_lines
            involved_lines += current_lines

        # ==== Create partials ====

        partial_amount = self.env.context.get('amount', False)
        if partial_amount:
            reconcile = sorted_lines._prepare_reconciliation_partials()
            reconcile[0].update({
                'amount': partial_amount,
                'debit_amount_currency': partial_amount,
                'credit_amount_currency': partial_amount,
            })
        else:
            reconcile = sorted_lines._prepare_reconciliation_partials()

        partials = self.env['account.partial.reconcile'].create(reconcile)
        # Track newly created partials.
        results['partials'] = partials
        involved_partials += partials

        # ==== Create entries for cash basis taxes ====

        is_cash_basis_needed = account.user_type_id.type in ('receivable', 'payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel'):
            tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
            results['tax_cash_basis_moves'] = tax_cash_basis_moves

        # ==== Check if a full reconcile is needed ====

        if involved_lines[0].currency_id and all(line.currency_id == involved_lines[0].currency_id for line in involved_lines):
            is_full_needed = all(line.currency_id.is_zero(line.amount_residual_currency) for line in involved_lines)
        else:
            is_full_needed = all(line.company_currency_id.is_zero(line.amount_residual) for line in involved_lines)
        if is_full_needed:

            # ==== Create the exchange difference move ====

            if self._context.get('no_exchange_difference'):
                exchange_move = None
            else:
                exchange_move = involved_lines._create_exchange_difference_move()
                if exchange_move:
                    exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == account)

                    # Track newly created lines.
                    involved_lines += exchange_move_lines

                    # Track newly created partials.
                    exchange_diff_partials = exchange_move_lines.matched_debit_ids \
                                             + exchange_move_lines.matched_credit_ids
                    involved_partials += exchange_diff_partials
                    results['partials'] += exchange_diff_partials

                    exchange_move._post(soft=False)

            # ==== Create the full reconcile ====

            results['full_reconcile'] = self.env['account.full.reconcile'].create({
                'exchange_move_id': exchange_move and exchange_move.id,
                'partial_reconcile_ids': [(6, 0, involved_partials.ids)],
                'reconciled_line_ids': [(6, 0, involved_lines.ids)],
            })

        # Trigger action for paid invoices
        not_paid_invoices\
            .filtered(lambda move: move.payment_state in ('paid', 'in_payment'))\
            .action_invoice_paid()

        return results


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    numero_antiguo = fields.Char('Numero de factura antiguo')
    es_documento_caja_chica = fields.Boolean('Es factura de caja chica')
    is_numero_antiguo = fields.Boolean('Es documento antiguo?', store=False, compute="is_numero_antiguo_compute")

    @api.depends('numero_antiguo')
    def is_numero_antiguo_compute(self):
        for rec in self:
            if not rec.numero_antiguo in ('',False, None):
                rec.is_numero_antiguo = False
            else:
                rec.is_numero_antiguo = True



    def compact(self, number):
        """Convert the number to the minimal representation. This strips the
        number of any valid separators and removes surrounding whitespace."""
        return clean(number, ' ').strip().upper()

    # The following document types are known:
    def ncf_document_types(self):
        return(
        '01',  # invoices for fiscal declaration (or tax reporting)
        '02',  # invoices for final consumer
        '03',  # debit note
        '04',  # credit note (refunds)
        '11',  # informal supplier invoices (purchases)
        '12',  # single income record
        '13',  # minor expenses invoices (purchases)
        '14',  # invoices for special customers (tourists, free zones)
        '15',  # invoices for the government
    )

    def ecf_document_types(self):
        return (
        '31',  # invoices for fiscal declaration (or tax reporting)
        '32',  # invoices for final consumer
        '33',  # debit note
        '34',  # credit note (refunds)
        '41',  # supplier invoices (purchases)
        '43',  # minor expenses invoices (purchases)
        '44',  # invoices for special customers (tourists, free zones)
        '45',  # invoices for the government
    )

    def validate(self,number):
        """Check if the number provided is a valid NCF."""
        number = self.compact(number)
        if len(number) == 13:
            if number[0] != 'E' or not isdigits(number[1:]):
                raise InvalidFormat()
            if number[1:3] not in self.ecf_document_types():
                raise InvalidComponent()
        elif len(number) == 11:
            if number[0] != 'B' or not isdigits(number[1:]):
                raise InvalidFormat()
            if number[1:3] not in self.ncf_document_types():
                raise InvalidComponent()
        elif len(number) == 19:
            if number[0] not in 'AP' or not isdigits(number[1:]):
                raise InvalidFormat()
            if number[9:11] not in self.ncf_document_types():
                raise InvalidComponent()
        else:
            raise InvalidLength()
        return number

    def is_valid(self,number):
        """Check if the number provided is a valid NCF."""
        try:
            return bool(self.validate(number))
        except ValidationError:
            return False

    def _convert_result(self,result,type):  # pragma: no cover
        """Translate SOAP result entries into dictionaries."""
        if type == 'ncf':
            translation = {
                'NOMBRE': 'name',
                'COMPROBANTE': 'proof',
                'ES_VALIDO': 'is_valid',
                'MENSAJE_VALIDACION': 'validation_message',
                'RNC': 'rnc',
                'NCF': 'ncf',
                u'RNC/Cédula': 'rnc',
                u'Nombre/Razón Social': 'name',
                'Estado': 'status',
                'Tipo de comprobante': 'type',
            }
            return dict(
                (translation.get(key, key), value)
                for key, value in result.items())
        if type == 'encf':
            translation = {
                'NOMBRE': 'name',
                'COMPROBANTE': 'proof',
                'ES_VALIDO': 'is_valid',
                'MENSAJE_VALIDACION': 'validation_message',
                'RNC': 'rnc',
                'NCF': 'ncf',
                u'RNC/Cédula': 'rnc',
                u'Nombre/Razón Social': 'name',
                'Código de Seguridad ': 'codigo',
                'Estado': 'status',
                'Monto total': 'monto',
                'ITBIS': 'itbis',
                'Fecha de emision': 'fechae',
                'Tipo de comprobante': 'type',
            }
            return dict(
                (translation.get(key, key), value)
                for key, value in result.items())

    def check_dgii(self,rnc, ncf, timeout=30):  # pragma: no cover
        """Validate the RNC, NCF combination on using the DGII online web service.

        This uses the validation service run by the the Dirección General de
        Impuestos Internos, the Dominican Republic tax department to check
        whether the combination of RNC and NCF is valid. The timeout is in
        seconds.

        Returns a dict with the following structure::

            {
                'name': 'The registered name',
                'status': 'VIGENTE',
                'type': 'FACTURAS DE CREDITO FISCAL',
                'rnc': '123456789',
                'ncf': 'A020010210100000005',
                'validation_message': 'El NCF digitado es válido.',
            }

        Will return None if the number is invalid or unknown."""
        rnc = rnc_compact(rnc)
        ncf = self.compact(ncf)
        url = 'https://dgii.gov.do/app/WebApps/ConsultasWeb2/ConsultasWeb/consultas/ncf.aspx'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
        }
        # Get the page to pick up needed form parameters
        document = lxml.html.fromstring(
            requests.get(url, headers=headers, timeout=30).text)
        validation = document.find('.//input[@name="__VIEWSTATEGENERATOR"]').get('value')
        viewstate = document.find('.//input[@name="__VIEWSTATE"]').get('value')
        eventvalidation = document.find('.//input[@name="__EVENTVALIDATION"]').get('value')
        data = {
            '__VIEWSTATEGENERATOR': validation,
            '__VIEWSTATE': viewstate,
            '__EVENTVALIDATION': eventvalidation,
            'ctl00$cphMain$btnConsultar': 'Buscar',
            'ctl00$cphMain$txtNCF': ncf,
            'ctl00$cphMain$txtRNC': rnc,
        }
        document = lxml.html.fromstring(
            requests.post(url, headers=headers, data=data, timeout=100000).text)
        result = document.find('.//div[@id="cphMain_pResultado"]')
        if result is not None:
            data = {
                'validation_message': document.findtext('.//*[@id="cphMain_lblInformacion"]').strip(),
            }
            data.update(zip(
                [x.text.strip().rstrip(':') for x in result.xpath('.//th')],
                [x.text.strip() for x in result.xpath('.//span[string()]')]))
            return self._convert_result(data,type='ncf')
        else:
            data = {
                'validation_message': document.findtext('.//*[@id="cphMain_lblInformacion"]').strip(),
            }
            return self._convert_result(data,type='ncf')

    def check_edgii(self, rncv,rncc, ncf,codigo, timeout=30):  # pragma: no cover
        """Validate the RNC, NCF combination on using the DGII online web service.

        This uses the validation service run by the the Dirección General de
        Impuestos Internos, the Dominican Republic tax department to check
        whether the combination of RNC and NCF is valid. The timeout is in
        seconds.

        Returns a dict with the following structure::

            {
                'name': 'The registered name',
                'status': 'VIGENTE',
                'type': 'FACTURAS DE CREDITO FISCAL',
                'rnc': '123456789',
                'ncf': 'A020010210100000005',
                'validation_message': 'El NCF digitado es válido.',
            }

        Will return None if the number is invalid or unknown."""
        import lxml.html
        import requests
        from stdnum.do.rnc import compact as rnc_compact
        rncc = rnc_compact(rncc)  # Buyer RNC
        rncv = rnc_compact(rncv)  # Seller RNC
        ncf = self.compact(ncf)
        url = 'https://dgii.gov.do/app/WebApps/ConsultasWeb2/ConsultasWeb/consultas/ncf.aspx'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36',
        }
        # Get the page to pick up needed form parameters
        document = lxml.html.fromstring(
            requests.get(url, headers=headers, timeout=30).text)
        validation = document.find('.//input[@name="__VIEWSTATEGENERATOR"]').get('value')
        viewstate = document.find('.//input[@name="__VIEWSTATE"]').get('value')
        eventvalidation = document.find('.//input[@name="__EVENTVALIDATION"]').get('value')
        data = {
            '__VIEWSTATEGENERATOR': validation,
            '__VIEWSTATE': viewstate,
            '__EVENTVALIDATION': eventvalidation,
            'ctl00$cphMain$btnConsultar': 'Buscar',
            'ctl00$cphMain$txtRNC': rncv,
            'ctl00$cphMain$txtNCF': ncf,
            'ctl00$cphMain$txtRncComprador': rncc,
            'ctl00$cphMain$txtCodigoSeg': codigo,
        }
        document = lxml.html.fromstring(
            requests.post(url, headers=headers, data=data, timeout=100000).text)
        result = document.find('.//div[@id="cphMain_PResultadoFE"]')
        if result is not None:
            data.clear()
            data.update(zip(
                [x.text.strip().rstrip(':') for x in result.xpath('.//th')],
                [x.text.strip() for x in result.xpath('.//span[string()]')]))
            return self._convert_result(data,type='encf')
        else:
            data = {
                'validation_message': document.findtext('.//*[@id="cphMain_lblInformacion"]').strip(),
            }
            return self._convert_result(data,type='encf')

    check_ncf_done = fields.Boolean("Chequeo en DGII", default=False, copy=False)
    check_ncf_message = fields.Char("Mensaje de chequeo en DGII", copy=False)
    check_ecf_code = fields.Char("Codigo de seguridad e-NCF", copy=False)
    is_encf = fields.Boolean("Es e-NCF?", compute="check_encf", copy=False)
    ncf_message_done = fields.Boolean("Esta el comprobante confirmado?", copy=False)
    ncf_message_incorrect = fields.Boolean("Esta el comprobante no valido?", copy=False)
    ncf_message_error = fields.Boolean("La busqueda da error?", copy=False)

    @api.onchange('l10n_latam_document_number')
    def check_encf(self):
        for inv in self:
            if inv.l10n_latam_document_number:
                if inv.l10n_latam_document_type_id and inv.move_type in ('in_invoice', 'in_refund') \
                    and len(inv.l10n_latam_document_number) == 13:
                    inv.is_encf = True
                else:
                    inv.is_encf = False
            else:
                inv.is_encf = False


    def check_ncf_in_dgii(self):
        for inv in self:
            if inv.l10n_latam_document_number:
                if inv.l10n_latam_document_type_id and inv.move_type in ('in_invoice', 'in_refund') \
                    and len(inv.l10n_latam_document_number) == 11:
                    try:
                        validation = self.check_dgii(inv.partner_id.vat, inv.l10n_latam_document_number)
                        inv.check_ncf_message = (_(" NCF Validado. Datos: "
                                                   "Válido hasta: %s. "
                                                   , validation['Válido hasta']))
                        if 'no es correcto' in inv.check_ncf_message:
                            inv.ncf_message_incorrect = True
                        else:
                            inv.ncf_message_incorrect = False
                        inv.ncf_message_done = True
                        inv.ncf_message_error = False
                    except:
                        inv.ncf_message_done = False
                        inv.ncf_message_error = True
                        inv.check_ncf_message = ' Error en la busqueda del comprobante, favor intentar de nuevo en la pagina de la DGII' \
                                                'o presionar el boton de nuevo.'
                if inv.l10n_latam_document_type_id and inv.move_type in ('in_invoice', 'in_refund') \
                    and len(inv.l10n_latam_document_number) == 13:
                    if not inv.check_ecf_code:
                        raise UserError(_('No puede confirmar un e-NCF sin completar primero el codigo de seguridad.'))
                    try:
                        validation = self.check_edgii(rncc=self.env.company.vat,rncv=inv.partner_id.vat, ncf=inv.l10n_latam_document_number
                                                                 , codigo=inv.check_ecf_code)
                        inv.check_ncf_message = (_(" e-NCF Validado. Datos: "
                                                   "Monto total en DGII: %s, "
                                                   "ITBIS total en DGII: %s, "
                                                   "Fecha de emision en DGII: %s.", validation['Monto Total'],validation['Total de ITBIS']
                                                   ,validation['Fecha Emisi&oacuten']))
                        if 'no es correcto' in inv.check_ncf_message:
                            inv.ncf_message_incorrect = True
                        else:
                            inv.ncf_message_incorrect = False
                        inv.ncf_message_done = True
                        inv.ncf_message_error = False
                    except:
                        inv.ncf_message_done = False
                        inv.ncf_message_error = True
                        inv.check_ncf_message = 'Error en la busqueda del comprobante, favor intentar de nuevo en la pagina ' \
                                                'o presionar el boton de nuevo'

    def write(self, vals,exchange=False):
        # OVERRIDE


        res = super().write(vals)
        for inv in self:
            if 'state' in vals:
                if vals['state'] == 'posted':
                    if inv.tipo_itbis_venta == '08' and inv.move_type in ('out_invoice','out_refund') and inv.journal_id.l10n_latam_company_use_documents:
                            for line in inv.invoice_line_ids:
                                if line.tax_ids:
                                    for tax in line.tax_ids:
                                        if tax.amount != 1.8 and tax.amount_type != 'group' and tax.tax_group_id.name == 'ITBIS':
                                            bool = False
                                            # raise UserError(
                                            #     _("No puede utilizar este tipo de ITBIS exento (Constructora 08) si existe alguna linea de la factura "
                                            #       "con un ITBIS que supere el 18 porciento del 10 porciento de la factura o si existe alguna linea con un ITBIS exento. Factura borrador: %s, "
                                            #       "SN: %s",
                                            #       inv.id if inv.posted_before == False else inv.name, inv.partner_id.name))
                                        elif tax.amount_type == 'group':
                                            for taxes in tax.children_tax_ids:
                                                if taxes.amount != 1.8 and taxes.tax_group_id.name == 'ITBIS':
                                                    bool = False
                                                    # raise UserError(
                                                    #     _("No puede utilizar este tipo de ITBIS exento (Constructora 08) si existe alguna linea de la factura "
                                                    #       "con un ITBIS que supere el 18 porciento del 10 porciento de la factura o si existe alguna linea con un ITBIS exento. Factura borrador: %s, "
                                                    #       "SN: %s",
                                                    #       inv.id if inv.posted_before == False else inv.name,
                                                    #       inv.partner_id.name))
                                else:
                                    bool = False
                                    # raise UserError(
                                    #     _("No puede utilizar este tipo de ITBIS exento (Constructora 08) si existe alguna linea de la factura "
                                    #       "con un ITBIS que supere el 18 porciento del 10 porciento de la factura o si existe alguna linea con un ITBIS exento. Factura borrador: %s, "
                                    #       "SN: %s",
                                    #       inv.id if inv.posted_before == False else inv.name, inv.partner_id.name))
                    if inv.tipo_itbis_venta == '09' and inv.move_type in ('out_invoice','out_refund') and inv.journal_id.l10n_latam_company_use_documents:
                        for line in inv.invoice_line_ids:
                            if line.tax_ids:
                                for tax in line.tax_ids:
                                    if tax.amount != 1.8 and tax.amount_type != 'group' and tax.tax_group_id.name == 'ITBIS':
                                        bool = False
                                        # raise UserError(
                                        #     _("No puede utilizar este tipo de ITBIS exento (Constructora 09) si existe alguna linea de la factura "
                                        #       "con un ITBIS que supere el 18 porciento del 10 porciento de la factura o si existe alguna linea con un ITBIS exento. Factura borrador: %s, "
                                        #       "SN: %s",
                                        #       inv.id if inv.posted_before == False else inv.name, inv.partner_id.name))
                                    elif tax.amount_type == 'group':
                                        for taxes in tax.children_tax_ids:
                                            if taxes.amount != 1.8 and taxes.tax_group_id.name == 'ITBIS':
                                                bool = False
                                                # raise UserError(
                                                #     _("No puede utilizar este tipo de ITBIS exento (Constructora 09) si existe alguna linea de la factura "
                                                #       "con un ITBIS que supere el 18 porciento del 10 porciento de la factura o si existe alguna linea con un ITBIS exento. Factura borrador: %s, "
                                                #       "SN: %s",
                                                #       inv.id if inv.posted_before == False else inv.name,
                                                #       inv.partner_id.name))
                            else:
                                bool = False
                                # raise UserError(
                                #     _("No puede utilizar este tipo de ITBIS exento (Constructora 09) si existe alguna linea de la factura "
                                #       "con un ITBIS que supere el 18 porciento del 10% de la factura o si existe alguna linea con un ITBIS exento. Factura borrador: %s,"
                                #               " SN: %s", inv.name, inv.partner_id.name))

                    if inv.tipo_itbis_venta == '05' and inv.move_type in ('out_invoice','out_refund') and inv.journal_id.l10n_latam_company_use_documents:
                        for line in inv.invoice_line_ids:
                            if line.tax_ids:
                                for tax in line.tax_ids:
                                    if tax.amount != 18.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                        bool = False
                                        # raise UserError(
                                        #     _("No puede utilizar este tipo de ITBIS exento o gravado (Venta de activo depreciable) si existe alguna linea de la factura "
                                        #       "con un ITBIS que no sea igual al 18 porciento o alguna linea exenta de ITBIS. Factura borrador: %s,"
                                        #       " SN: %s", inv.name, inv.partner_id.name))
                                    elif tax.amount_type == 'group':
                                        for taxes in tax.children_tax_ids:
                                            if taxes.amount != 18.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                bool = False
                                                # raise UserError(
                                                #     _("No puede utilizar este tipo de ITBIS exento o gravado (Venta de activo depreciable) si existe alguna linea de la factura "
                                                #       "con un ITBIS que no sea igual al 18 porciento o alguna linea exenta de ITBIS. Factura borrador: %s,"
                                                #       " SN: %s", inv.name, inv.partner_id.name))

                            else:
                                bool = False
                                # raise UserError(
                                #     _("No puede utilizar este tipo de ITBIS exento (Venta de activo depreciable) si existe alguna linea de la factura "
                                #       "con un ITBIS que no sea igual al 18 porciento o alguna linea exenta de ITBIS. Factura borrador: %s,"
                                #               " SN: %s", inv.name, inv.partner_id.name))
                    if inv.journal_id.l10n_latam_company_use_documents and inv.move_type in ('out_refund'):
                        if inv.l10n_do_origin_ncf:
                            modified = False
                            modified = self.env['account.move'].search(
                                ['&', '&', ('l10n_latam_document_number', '=', inv.l10n_do_origin_ncf)
                                    , ('partner_id', '=', inv.partner_id.id), ('state', '=', 'posted')
                                    , ('move_type', '=', 'out_invoice'), ('company_id', '=', inv.company_id.id)])

                            for modifieds in modified:
                                if inv.l10n_do_origin_ncf == modifieds.l10n_latam_document_number and \
                                    inv.tipo_itbis_venta != modifieds.tipo_itbis_venta:
                                    boole = True
                                    # raise UserError(_("La nota de credito %s no posee la misma asignacion de tipo "
                                    #                   "de itbis de venta que la factura %s. Esto podria traer inconsistencias "
                                    #                   "en la elaboracion del IT1. Favor corregir.", inv.id if inv.posted_before == False else inv.name, modifieds.name))

                                if inv.l10n_do_origin_ncf == modifieds.l10n_latam_document_number:
                                    origin_exento = 0.0
                                    nc_exento = 0.0
                                    for line in modifieds.invoice_line_ids:
                                        if line.tax_ids:
                                            for tax in line.tax_ids:
                                                if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                    origin_exento += line.price_subtotal
                                                if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                    for taxes in tax.children_tax_ids:
                                                        if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                            origin_exento += line.price_subtotal
                                        if not line.tax_ids:
                                            origin_exento += line.price_subtotal
                                    for line in inv.invoice_line_ids:
                                        if line.tax_ids:
                                            for tax in line.tax_ids:
                                                if tax.amount == 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                    nc_exento += line.price_subtotal
                                                if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                    for taxes in tax.children_tax_ids:
                                                        if taxes.amount == 0.0 and taxes.tax_group_id.name == 'ITBIS' and taxes.amount_type != 'group':
                                                            nc_exento += line.price_subtotal
                                        if not line.tax_ids:
                                            nc_exento += line.price_subtotal
                                    if nc_exento > origin_exento and (inv.invoice_date - modifieds.invoice_date).days <= 30:
                                        boole = True
                                        # raise UserError(_("La nota de credito %s tiene un valor exento mayor que la factura "
                                        #                   " %s afectada. Esto podria traer inconsistencias "
                                        #                   "en la elaboracion del IT1, pues la nota de credito si esta dentro "
                                        #                   "de los 30 dias deberia afectar el valor exento en la misma proporcion "
                                        #                   "o menor que lo facturado. Favor corregir.", inv.id if inv.posted_before == False else inv.name,
                                        #                   modifieds.name))
                                    origin_gravado = 0.0
                                    nc_gravado = 0.0
                                    for line in modifieds.invoice_line_ids:
                                        if line.tax_ids:
                                            for tax in line.tax_ids:
                                                if tax.amount > 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                    origin_gravado += line.price_subtotal * (tax.amount / 100)
                                                if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                    for taxes in tax.children_tax_ids:
                                                        origin_gravado += line.price_subtotal * (taxes.amount / 100)
                                    for line in inv.invoice_line_ids:
                                        if line.tax_ids:
                                            for tax in line.tax_ids:
                                                if tax.amount > 0.0 and tax.tax_group_id.name == 'ITBIS' and tax.amount_type != 'group':
                                                    nc_gravado += line.price_subtotal * (tax.amount / 100)
                                                if tax.tax_group_id.name == 'ITBIS' and tax.amount_type == 'group':
                                                    for taxes in tax.children_tax_ids:
                                                        nc_gravado += line.price_subtotal * (taxes.amount / 100)
                                    if nc_gravado > origin_gravado and (inv.invoice_date - modifieds.invoice_date).days <= 30:
                                        boole = True
                                        # raise UserError(_("La nota de credito %s tiene un valor gravado mayor que la factura "
                                        #                   " %s afectada. Esto podria traer inconsistencias "
                                        #                   "en la elaboracion del IT1, pues la nota de credito si esta dentro "
                                        #                   "de los 30 dias deberia afectar el valor gravado en la misma proporcion "
                                        #                   "o menor que lo facturado. Favor corregir.", inv.id if inv.posted_before == False else inv.name,
                                        #                   modifieds.name))
                        else:
                            if inv.journal_id.l10n_latam_use_documents == True:
                                raise UserError(_("La nota de credito borrador %s, SN: %s no posee un NCF afectado. "
                                                  "Favor corregir.", inv.id if inv.posted_before == False else inv.name, inv.partner_id.name))

        return res

    import_itbis_amount = fields.Monetary(string="ITBIS en importacion", compute="_calc_import_itbis")

    @api.depends('state')
    def _calc_import_itbis(self):
        for rec in self:
            if rec.state == 'posted':
                import_tax = 0.0
                for lines in rec.invoice_line_ids:
                    for tax in lines.tax_ids:
                        if tax.is_import and (rec.amount_total - rec.amount_untaxed) > 0:
                            import_tax += 1
                if import_tax > 0:
                    rec.import_itbis_amount = rec.amount_total - rec.amount_untaxed
                else:
                    rec.import_itbis_amount = 0.0
            else:
                rec.import_itbis_amount = 0.0



    def _post(self, soft = True):
        for rec in self:
            import_tax = 0.0
            normal_tax = 0.0
            for lines in rec.invoice_line_ids:
                for tax in lines.tax_ids:
                    if tax.is_import and (rec.amount_total - rec.amount_untaxed) <= 0 and tax.amount_type != 'group':
                        raise UserError(_("Como el codigo de impuesto de ITBIS de importacion esta asignado, "
                                          "favor de modificar el ITBIS en importacion, pues el mismo no puede ser menor ni igual a 0."))
                    elif tax.amount_type == 'group':
                        for taxes in tax.children_tax_ids:
                            if taxes.is_import and (rec.amount_total - rec.amount_untaxed) <= 0 and taxes.amount_type != 'group':
                                raise UserError(_("Como el codigo de impuesto de ITBIS de importacion esta asignado, "
                                                  "favor de modificar el ITBIS en importacion, pues el mismo no puede ser menor ni igual a 0."))
                            if taxes.is_import:
                                import_tax += 1
                            if not taxes.is_import:
                                normal_tax += 1
                    if tax.is_import:
                        import_tax += 1
                    if not tax.is_import:
                        normal_tax += 1
            if import_tax > 0.0 and normal_tax > 0.0:
                raise UserError(_("No puede registrar una factura con un ITBIS de importacion y un ITBIS normal al mismo tiempo. "
                                  "Si es una importacion, registre la liquidacion como un documento unico utilizando el codigo "
                                  "de impuestos de ITBIS - Importacion y los demas documentos relacionados registrelos a parte. Esto "
                                  "es necesario para realizar un calculo correcto del IT1."))

            # if rec.state != 'posted':
            #     to_write = {'state': 'posted'}
            to_write = {}

            sequence = False
            # if rec.payment_id.payment_type == 'outbound' and (rec.name == '/' or rec.name == '/0' or rec.name == False
            #                                                   or rec.name == rec.partner_id.name):
            #     sequence = rec._get_sequence(outbound=True)
            # elif rec.payment_id.payment_type == 'inbound' and (rec.name == '/' or rec.name == '/0' or rec.name == False
            #                                                   or rec.name == rec.partner_id.name):
            #     sequence = rec._get_sequence(inbound=True)
            # elif rec.name == '/' or rec.name == '/0' or rec.name == False or rec.name == rec.partner_id.name:
            #     sequence = rec._get_sequence()
                
            # if not sequence and rec.name == '/' or rec.name == '/0' or rec.name == False:
            #     raise UserError(_('Please define a sequence on your journal.'))


            # if rec.journal_id.active == False and rec.name == '/':
            #     raise UserError(_('This Journal is not active, please change it to one which is active.'))


                # raise UserError(_("%s", to_write))

            # to_write['l10n_ncf_type_name'] = rec.l10n_ncf_type_name

            to_write['currency_id']: rec.currency_id

            # raise UserError(_("%s", to_write))
            rec.write(to_write)


        return super(AccountInvoice, self)._post(soft)

    sale_itbis_retention_type = fields.Selection(
        [('01', 'RETENCIONES (Norma No. 08-04)'),
         ('02', 'VENTAS DE PASAJES DE TRANSPORTE AÉREO (Norma No. 02-05) (BSP-IATA)'),
         ('03', 'OTRAS RETENCIONES (Norma No. 02-05)'),
         ('04', 'VENTAS DE PAQUETES DE ALOJAMIENTO Y OCUPACIÓN'),
         ('05', 'ENTIDADES DEL ESTADO'),
         ('06', 'PAGOS COMPUTABLES POR ITBIS PERCIBIDO'), ],
        string="Tipo de Retención en ITBIS", store=False, compute="_compute_withheld_taxes")


    clasificacion_itbis_compra = fields.Selection(
        [('01', 'ND: EN OPERACIONES DE PRODUCTORES DE BIENES O SERVICIOS EXENTOS'),
         ('02', 'ND: A INCLUIR EN ACTIVOS (CATEGORÍA I)'),
         ('03', 'ND: OTROS ITBIS PAGADOS NO DEDUCIBLES'),
         ('04', 'D: EN LA PRODUCCIÓN Y/O VENTA DE BIENES EXPORTADOS'),
         ('05', 'D: EN LA PRODUCCIÓN Y/O VENTA DE BIENES GRAVADOS'),
         ('06', 'D: EN LA PRESTACIÓN DE SERVICIOS GRAVADOS'),
         ('07', 'P:ITBIS SUJETO A PROPORCIONALIDAD'),],
        string="Clasificacion de ITBIS en compra (Anexo A)",
        help="Con esta asignacion se realiza la correcta distribucion en el Anexo A"
        , store=True,
        default=lambda self: self.env.user.company_id.clasificacion_itbis_compra)

    calculate_clasificacion_compra = fields.Boolean(compute='_compute_clasificacion_compra', store=False)

    @api.depends('l10n_latam_document_type_id', 'partner_id')
    def _compute_clasificacion_compra(self):
        for inv in self:
            if self.env.user.company_id.clasificacion_itbis_compra and inv.calculate_clasificacion_compra == False and not inv.clasificacion_itbis_compra:
                inv.clasificacion_itbis_compra = self.env.user.company_id.tipo_itbis_venta
                inv.calculate_clasificacion_compra = True
            else:
                inv.calculate_clasificacion_compra = False

    tipo_compra_cabecera = fields.Selection(
        [('product', 'Bienes'),
         ('service', 'Servicios'), ],
        string="Tipo de compra",
        help="Con esta asignacion se realiza la correcta distribucion en el Anexo A si "
             "a nivel de linea no es seleccionado un producto."
        , store=True)

    no_product = fields.Boolean(string="No hay producto seleccionado?",compute="_compute_no_product")

    @api.depends('invoice_line_ids')
    def _compute_no_product(self):

        for inv in self:
            inv.no_product = False
            if inv.move_type in ('in_invoice','in_refund'):
                for line in inv.invoice_line_ids:
                    if not line.product_id:
                        inv.no_product = False
                    else:
                        inv.no_product = True
            else:
                inv.no_product = False




    tipo_itbis_venta = fields.Selection(
        [('01', 'Exportacion de vienes y servicios Art. 342 CT'),
         ('02', 'Exportacion de vienes y servicios Art. 344 CT y Art. 14 Literal j, Reglamento 293-11'),
         ('03', 'Venta bienes y servicios locales exentos Art. 343 CT y Art. 344 CT'),
         ('04', 'Venta bienes o servicios exentos por destino (Regimen especial)'),
         ('05', 'Venta de activo depreciable (cat. II y III)'),
         ('08', 'Construccion: DIRECCIÓN TÉCNICA (Art. 4 Norma 07-07)'),
         ('09', 'Construccion: CONTRATO DE ADMINISTRACIÓN (Art. 4 Párrafo I, Norma 07-07)'),
         ('10', 'Construccion: ASESORIAS / HONORARIOS'),
         ('11', 'Comisionista: VENTAS DE BIENES EN CONCESIÓN'),
         ('12', 'Comisionista: VENTAS DE SERVICIOS EN NOMBRE DE TERCEROS'),
         ('13', 'Venta local de vienes exentos Párrafos III y IV, Art. 343 CT'),],
        string="Tipo de ITBIS exento (y gravados) en venta", help="Con esta asignacion se realiza la correcta distribucion en el Anexo A"
        , store=True,
        default=lambda self: self.env.user.company_id.tipo_itbis_venta)

    calculate_tipo_venta = fields.Boolean(compute='_compute_tipo_venta', store=False)

    @api.depends('l10n_latam_document_type_id','partner_id')
    def _compute_tipo_venta(self):
        for inv in self:
            if self.env.user.company_id.tipo_itbis_venta and inv.calculate_tipo_venta == False and not inv.tipo_itbis_venta:
                # if inv.l10n_latam_document_type_id.l10n_do_ncf_type in ('special', 'e-special'):
                #     inv.tipo_itbis_venta = '04'
                #     inv.calculate_tipo_venta = True
                # else:
                inv.tipo_itbis_venta = self.env.user.company_id.tipo_itbis_venta
                inv.calculate_tipo_venta = True
            else:
                inv.calculate_tipo_venta = False


    @api.onchange('l10n_latam_document_type_id','partner_id')
    def get_tipo_itbis_venta(self):
        for inv in self:
            if inv.l10n_latam_document_type_id.l10n_do_ncf_type in ('special', 'e-special'):
                inv.tipo_itbis_venta = '04'
            else:
                inv.tipo_itbis_venta = self.env.user.company_id.tipo_itbis_venta

    def _check_balanced(self):
        ''' Assert the move is fully balanced debit = credit.
        An error is raised if it's not the case.
        '''
        moves = self.filtered(lambda move: move.line_ids)
        # raise UserError(_("%s.", moves.line_ids))
        if not moves:
            return


        # /!\ As this method is called in create / write, we can't make the assumption the computed stored fields
        # are already done. Then, this query MUST NOT depend of computed stored fields (e.g. balance).
        # It happens as the ORM makes the create with the 'no_recompute' statement.
        self.env['account.move.line'].flush(self.env['account.move.line']._fields)
        self.env['account.move'].flush(['journal_id'])
        self._cr.execute('''
            SELECT line.move_id, ROUND(SUM(line.debit - line.credit), currency.decimal_places)
            FROM account_move_line line
            JOIN account_move move ON move.id = line.move_id
            JOIN account_journal journal ON journal.id = move.journal_id
            JOIN res_company company ON company.id = journal.company_id
            JOIN res_currency currency ON currency.id = company.currency_id
            WHERE line.move_id IN %s
            GROUP BY line.move_id, currency.decimal_places
            HAVING ROUND(SUM(line.debit - line.credit), currency.decimal_places) != 0.0;
        ''', [tuple(self.ids)])

        query_res = self._cr.fetchall()
        if query_res:

            ids = [res[0] for res in query_res]

            sums = [res[1] for res in query_res]
            raise UserError(_("Cannot create unbalanced journal entry. Ids: %s\nDifferences debit - credit: %s") % (ids, sums))

    def _convert_to_DOP_currency(self, base_currency, date1, amount):
        user_company_id = self.env.user.company_id
        user_currency_id = self.env['res.currency'].browse(74)
        base_currency_id = base_currency
        if not date1:
            date1 = date.today()

        return base_currency_id._convert(
            amount, user_currency_id, user_company_id, date1)

    @api.constrains('state','partner_id','l10n_latam_document_type_id','amount_untaxed','fiscal_position_id' )
    def _check_consumer_type_ncf(self):
        """ Validates that an invoices with a partner from country != DO
            and products type != service must have Exportaciones NCF.
            See DGII Norma 05-19, Art 10 for further information.
        """
        for rec in self.filtered(
            lambda r: r.company_id.country_id == self.env.ref("base.do")
            and r.l10n_latam_document_type_id
            and r.move_type in ("out_invoice","out_refund")
            and r.state in ('draft','posted')
        ):
            return False

            # if rec.partner_id.country_id.code == 'DO':
            #     if rec.l10n_latam_document_type_id.l10n_do_ncf_type == 'consumer' and \
            #             self._convert_to_DOP_currency(rec.currency_id, rec.invoice_date,
            #                                           rec.amount_untaxed) >= 250000 and not rec.partner_id.vat \
            #                                         and rec.fiscal_position_id.name != 'In process':
            #         raise ValidationError(
            #                     "Sales above DOP 250,000.00 to dominican final consumers must have "
            #                     "a vat number (RNC or Cedula). "
            #                     "If the sale must be procceded anyways, please fill select in fiscal position -In process-. "
            #                     "With this, it will be reported as a passport without numbers until the vat can be retrieved"
            #                 )

    #        if rec.partner_id.country_id.code != 'DO':
    #            if rec.l10n_latam_document_type_id.l10n_do_ncf_type == 'consumer' and \
    #                    self._convert_to_DOP_currency(rec.currency_id, rec.invoice_date,
    #                                                  rec.amount_untaxed) >= 250000 and not rec.partner_id.vat \
    #                                                and rec.fiscal_position_id.name != 'In process':
    #                raise ValidationError(
    #                            "Sales above DOP 250,000.00 to foreign final consumers must have "
    #                            "a vat number (Passport or fiscal ID). "
    #                            "If the sale must be procceded anyways, please in fiscal position -In process-. "
    #                            "With this, it will be reported as a passport without numbers until the vat can be retrieved"
    #                        )



    def _get_invoice_payment_widget(self):
        if self.invoice_payments_widget:
            j = json.loads(self.invoice_payments_widget)
            return j['content'] if j else []
        else:
            return []


    @api.depends('payment_state')
    def _compute_invoice_payment_date(self):
        for inv in self:
            inv.payment_date = False
            if inv.move_type in ('in_invoice', 'in_refund'):
                if inv.payment_state in ('paid','in_payment'):
                    dates = [
                        payment['date'] if payment['date'] != False else date(2000, 1, 1) for payment in inv._get_reconciled_info_JSON_values()
                    ]
                    if dates:
                        max_date = max(dates)
                        date_invoice = inv.invoice_date
                        if date_invoice:
                            inv.payment_date = max_date if max_date >= date_invoice \
                                else date_invoice
                        else:
                            inv.payment_date = max_date
                elif inv.payment_state == 'not_paid':
                    inv.payment_date = False
            if inv.move_type in ('out_invoice', 'out_refund'):

                payments = self.env['account.payment']
                for payment in inv._get_reconciled_info_JSON_values():
                    if 'account_payment_id' in payment:
                        # raise UserError(_("%s", payment))
                        payments += self.env['account.payment'].search([('id', '=', payment['account_payment_id'])])


                # raise UserError(_("%s",payments))
                for paym in payments:
                    if paym.withold_method != 'default':
                        if inv.payment_state in ('paid','in_payment'):
                            dates = [
                                payment['date'] if payment['account_payment_id'] == paym.id and payment['date'] != False else date(2000, 1, 1) for payment in inv._get_reconciled_info_JSON_values()
                            ]
                            if dates:
                                max_date = max(dates)
                                date_invoice = inv.invoice_date
                                if date_invoice:
                                    inv.payment_date = max_date if max_date >= date_invoice \
                                        else date_invoice
                                else:
                                    inv.payment_date = max_date
                        elif inv.payment_state == 'not_paid':
                            inv.payment_date = False

                for line in inv.line_ids:
                    for tax in line.tax_ids:
                        if tax.amount < 0:
                            if inv.payment_state in ('paid','in_payment'):
                                dates = [
                                    payment['date'] for payment in inv._get_reconciled_info_JSON_values()
                                ]
                                if dates:
                                    max_date = max(dates)
                                    date_invoice = inv.invoice_date
                                    if date_invoice:
                                        inv.payment_date = max_date if max_date >= date_invoice \
                                            else date_invoice
                                    else:
                                        inv.payment_date = max_date

            if inv.payment_state == 'not_paid' and inv.move_type not in ('entry'):
                inv.payment_date = False

    @api.constrains('line_ids.tax_line_id')
    def _check_isr_tax(self):
        """Restrict one ISR and ITBIS tax per invoice"""
        for inv in self:
            line = [
                tax_line.tax_line_id.tax_group_id.name
                for tax_line in inv.line_ids.filtered(lambda line: line.tax_line_id)
                if tax_line.tax_line_id.tax_group_id.name in ['ISR', 'ITBIS'] and tax_line.tax_line_id.amount < 0
            ]
            if len(line) != len(set(line)):
                raise ValidationError(_('An invoice cannot have multiple'
                                        'withholding taxes.'))

    def _convert_to_local_currency(self, amount):
        sign = -1 if self.move_type in ['in_refund', 'out_refund'] else 1
        amount = self.company_currency_id._convert(
            amount, self.currency_id, self.company_id, self.date
        )
        return amount * sign

    def _get_tax_line_ids(self):
        return self.line_ids

    @api.depends('line_ids.tax_line_id', 'line_ids.tax_base_amount', 'state', 'payment_state')
    def _compute_taxes_fields(self):
        """Compute invoice common taxes fields"""
        for inv in self:

            if inv.payment_state == 'not_paid':
                inv._compute_invoice_payment_date()

            tax_line_ids = inv._get_tax_line_ids()

            inv.selective_tax = 0.0
            inv.other_taxes = 0.0
            inv.legal_tip = 0.0
            inv.proportionality_tax = 0.0
            inv.cost_itbis = 0.0

            if inv.state != 'draft' or inv.payment_state in ('paid','in_payment'):
                # Monto Impuesto Selectivo al Consumo

                amount_ISC = 0
                for tax_line in tax_line_ids:
                    ISC_taxes = ['ISC']
                    for tax in tax_line.tax_line_id:
                        if tax.tax_group_id.name in ISC_taxes and \
                                tax_line.tax_base_amount > 0:
                            amount_ISC += tax_line.price_subtotal
                inv.selective_tax = amount_ISC


                # Monto Otros Impuestos/Tasas
                amount_other = 0
                for tax_line in tax_line_ids:
                    Other_taxes = ['Otros Impuestos']
                    for tax in tax_line.tax_line_id:
                        if tax.tax_group_id.name in Other_taxes and \
                                tax_line.tax_base_amount > 0:
                            amount_other += tax_line.price_subtotal
                inv.other_taxes = amount_other


                # Monto Propina Legal
                amount_tip = 0
                for tax_line in tax_line_ids:
                    Tips = ['Propina']
                    for tax in tax_line.tax_line_id:
                        if tax.tax_group_id.name in Tips and \
                                tax_line.tax_base_amount > 0:
                            amount_tip += tax_line.price_subtotal
                inv.legal_tip = amount_tip

                # ITBIS sujeto a proporcionalidad
                amount_prop = 0
                ITBIS_taxes = ['ITBIS']
                for tax_line in tax_line_ids:
                    for tax in tax_line.tax_line_id:
                        if tax.tax_group_id.name.find('ITBIS') != -1 and tax.amount > 0 and inv.clasificacion_itbis_compra == '07':
                            amount_prop += tax_line.price_subtotal
                inv.proportionality_tax = amount_prop



                # ITBIS llevado al Costo

                cost_itbis = 0
                for tax_line in tax_line_ids:

                    for tax in tax_line.tax_line_id:
                        # raise UserError(_("%s", tax.amount))
                        if tax.tax_group_id.name.find('ITBIS') != -1 and tax.amount > 0 and \
                                inv.clasificacion_itbis_compra in ('01','02','03'):
                            cost_itbis += tax_line.price_subtotal
                inv.cost_itbis = cost_itbis


                if inv.move_type == 'out_invoice' and any([
                    inv.third_withheld_itbis,
                    inv.third_income_withholding
                        ]):
                    # Fecha Pago
                    inv._compute_invoice_payment_date()

                if inv.move_type == 'in_invoice' and any([
                    inv.withholded_itbis,
                    inv.income_withholding
                        ]):
                    # Fecha Pago
                    inv._compute_invoice_payment_date()



    @api.depends('invoice_line_ids', 'invoice_line_ids.product_id', 'state')
    def _compute_amount_fields(self):
        """Compute Purchase amount by product type"""
        for inv in self:

            inv.service_total_amount = 0.0
            inv.good_total_amount = 0.0

            if inv.move_type in [
                'in_invoice', 'in_refund'
                    ] and inv.state != 'draft' and inv.journal_id.l10n_latam_use_documents:
                service_amount = 0
                good_amount = 0

                products = 0

                for line in inv.invoice_line_ids:

                    if line.product_id:
                        # Monto calculado en bienes
                        if line.product_id.type in ['product', 'consu']:
                            good_amount += line.price_subtotal

                        # Si la linea no tiene un producto
                        elif not line.product_id:
                            service_amount += line.price_subtotal
                            continue

                        # Monto calculado en servicio
                        else:
                            service_amount += line.price_subtotal
                        products += 1
                    else:
                        # if products >= 1:
                        #     raise UserError(_("No puede crear una factura con lineas que tenga articulos y otras que no las tengan, "
                        #                       "favor utilizar items en todas las lineas o en ninguna para poder continuar"))
                        if inv.tipo_compra_cabecera == 'service':
                            service_amount += line.price_subtotal
                        if inv.tipo_compra_cabecera == 'product':
                            good_amount += line.price_subtotal


                inv.service_total_amount = service_amount
                inv.good_total_amount = good_amount

    @api.depends('invoice_line_ids', 'invoice_line_ids.product_id', 'payment_state')
    def _compute_isr_withholding_type(self):
        """Compute ISR Withholding Type

        Keyword / Values:
        01 -- Alquileres
        02 -- Honorarios por Servicios
        03 -- Otras Rentas
        04 -- Rentas Presuntas
        05 -- Intereses Pagados a Personas Jurídicas
        06 -- Intereses Pagados a Personas Físicas
        07 -- Retención por Proveedores del Estado
        08 -- Juegos Telefónicos
        """
        for inv in self:
            inv.isr_withholding_type = None
            if inv.move_type == 'in_invoice' and inv.payment_state in ('paid','in_payment'):
                isr = [
                    tax_line.tax_line_id
                    for tax_line in inv.line_ids.filtered(lambda line: line.tax_line_id)
                    if tax_line.tax_line_id.tax_group_id.name in ['ISR -2%', 'ISR -10%', 'ISR -27%']
                ]
                if isr:
                    inv.isr_withholding_type = isr.pop(0).isr_retention_type

            elif inv.payment_state not in ('paid','in_payment'):
                inv.isr_withholding_type = None

    def _get_payment_string(self):
        """Compute Vendor Bills payment method string

        Keyword / Values:
        cash        -- Efectivo
        bank        -- Cheques / Transferencias / Depósitos
        card        -- Tarjeta Crédito / Débito
        credit      -- Compra a Crédito
        swap        -- Permuta
        credit_note -- Notas de Crédito
        mixed       -- Mixto
        """
        payments = []
        p_string = ""

        for payment in self._get_invoice_payment_widget():
            payment_id = self.env['account.payment'].browse(
                payment.get('account_payment_id'))
            move_id = False
            if payment_id:
                if payment_id.journal_id.type in ['cash', 'bank', 'general'] and \
                        not payment_id.payment_method_id.l10n_do_payment_form:
                    p_string = payment_id.journal_id.l10n_do_payment_form

                elif payment_id.payment_method_id.l10n_do_payment_form:
                    p_string = payment_id.payment_method_id.l10n_do_payment_form

            if not payment_id:
                move_id = self.env['account.move'].browse(
                    payment.get('move_id'))
                if move_id:
                    p_string = 'credit'

            # If invoice is paid, but the payment doesn't come from
            # a journal, assume it is a credit note
            payment = p_string if payment_id or move_id else 'credit_note'
            payments.append(payment)

        methods = {p for p in payments}
        if len(methods) == 1:
            return list(methods)[0]
        elif len(methods) > 1:
            return 'mixed'

    @api.depends('payment_state')
    def _compute_in_invoice_payment_form(self):
        for inv in self:
            if inv.payment_state in ('paid','in_payment'):
                payment_dict = {'cash': '01', 'bank': '02', 'card': '03',
                                'credit': '04', 'swap': '05',
                                'credit_note': '06', 'mixed': '07'}
                inv.payment_form = payment_dict.get(inv._get_payment_string())
            else:
                inv.payment_form = '04' if inv.move_type != 'in_refund' else '06'

    @api.depends('line_ids.tax_line_id', 'line_ids.tax_base_amount', 'state')
    def _compute_invoiced_itbis(self):
        """Compute invoice invoiced_itbis taking into account the currency"""
        for inv in self:
            inv.invoiced_itbis = 0.0
            if inv.state != 'draft':
                amount = 0
                itbis_taxes = ['ITBIS', 'ITBIS 18%']
                for tax in inv._get_tax_line_ids():
                    if tax.tax_line_id.tax_group_id.name in itbis_taxes and \
                            tax.tax_base_amount > 0 and tax.tax_line_id.amount > 0:
                        amount += tax.price_subtotal
                    inv.invoiced_itbis = amount

    def _get_payment_move_iterator(self, payment, inv_type, witheld_type):
            move_id = self.env['account.move'].browse(payment.get('move_id'))
            if move_id:
                if inv_type == 'out_invoice':
                    return [
                        move_line.debit
                        for move_line in move_id.line_ids
                        if move_line.account_id.account_fiscal_type in
                        witheld_type
                    ]
                else:
                    return [
                        move_line.credit
                        for move_line in move_id.line_ids
                        if move_line.account_id.account_fiscal_type in
                        witheld_type
                    ]

    @api.depends('payment_state')
    def _compute_withheld_taxes(self):
        for inv in self:
            inv.withholded_itbis = 0.0
            inv.income_withholding = 0.0
            inv.sale_itbis_retention_type = False
            inv.isr_withholding_type = False
            inv.third_withheld_itbis = 0
            inv.third_income_withholding = 0
            if inv.payment_state in ('paid','in_payment'):
                inv.third_withheld_itbis = 0
                inv.third_income_withholding = 0
                witheld_itbis_types = ['A34', 'A36']
                witheld_isr_types = ['ISR', 'A38']

                if inv.move_type == 'in_invoice':
                    tax_line_ids = inv._get_tax_line_ids()

                    # Monto Retención Renta por impuesto
                    amount_isr = 0
                    isr_type = ''
                    for tax_line in tax_line_ids:
                        witholded_isr = ['ISR -2%', 'ISR -10%', 'ISR -27%']
                        for tax in tax_line.tax_line_id:
                            if tax.tax_group_id.name in witholded_isr and \
                                    tax_line.tax_base_amount > 0:
                                amount_isr += tax_line.price_subtotal * -1
                                isr_type = tax.isr_retention_type
                            if tax.amount_type == 'group':
                                for taxes in tax.children_tax_ids:
                                    if tax.tax_group_id.name in witholded_isr:
                                        isr_type = taxes.isr_retention_type
                                       
                        
                        
                        inv.income_withholding = amount_isr
                        inv.isr_withholding_type = isr_type
                        


                    # Monto ITBIS Retenido por impuesto
                    amount_itbis = 0
                    for tax_line in tax_line_ids:
                        withholded_itbis = ['ITBIS -30%', 'ITBIS -100%', 'ITBIS -75%']
                        for tax in tax_line.tax_line_id:
                            if tax.tax_group_id.name in withholded_itbis and \
                                    tax_line.tax_base_amount > 0:
                                amount_itbis += tax_line.price_subtotal * -1
                        inv.withholded_itbis = amount_itbis

                    for payment in inv._get_invoice_payment_widget():
                        withholded_itbis = 0.0
                        income_withholding = 0.0
                        payment_id = self.env['account.payment'].browse(
                            payment.get('account_payment_id'))

                        if payment_id and inv.income_withholding == 0.0 and inv.withholded_itbis == 0.0:

                            for invoices in payment_id.payment_invoice_ids:
                                if invoices.invoice_id == inv:
                                    if payment_id.withold_method != 'itbis_tccomision':
                                        withholded_itbis += invoices.itbis_withold
                                    income_withholding += invoices.isr_withold

                            retention_in_invoice = False
                            for invoice in inv.invoice_line_ids:
                                for tax in invoice.tax_ids:
                                    if tax.amount < 0:
                                        retention_in_invoice = True

                            if retention_in_invoice == False and inv.withholded_itbis == 0.0:
                                inv.withholded_itbis = withholded_itbis
                            if retention_in_invoice == False and inv.income_withholding == 0.0:
                                inv.income_withholding = income_withholding
                            if inv.income_withholding > 0.0 and retention_in_invoice == False:
                                inv.isr_withholding_type = payment_id.withold_isr_select.isr_retention_type


                if inv.move_type == 'out_invoice':


                        tax_line_ids = inv._get_tax_line_ids()

                        # ITBIS Retenido por Terceros
                        amount_itbis = 0
                        tipo_retencion = ''
                        for tax_line in tax_line_ids:
                            third_withheld_itbis = ['ITBIS -30%', 'ITBIS -100%', 'ITBIS -75%']
                            for tax in tax_line.tax_line_id:
                                if tax.tax_group_id.name in third_withheld_itbis and \
                                        tax_line.tax_base_amount > 0:
                                    amount_itbis += tax_line.price_subtotal * -1
                                    tipo_retencion = tax_line.sale_itbis_retention_type
                            inv.third_withheld_itbis = amount_itbis
                            if tipo_retencion != '01' and amount_itbis > 0.0:
                                inv.sale_itbis_retention_type = tipo_retencion
                            if amount_itbis == 0.0:
                                inv.payment_date = False
                                inv.sale_itbis_retention_type = False



                        # Retención de Renta pr Terceros
                        amount_isr = 0
                        for tax_line in tax_line_ids:
                            third_withholding = ['ISR -5%']
                            for tax in tax_line.tax_line_id:
                                if tax.tax_group_id.name in third_withholding and \
                                        tax_line.tax_base_amount > 0:
                                    amount_isr += tax_line.price_subtotal * -1
                            inv.third_income_withholding = amount_isr

                        for payment in inv._get_invoice_payment_widget():
                            withholded_itbis = 0.0
                            income_withholding = 0.0
                            payment_id = self.env['account.payment'].browse(
                                payment.get('account_payment_id'))

                            if payment_id and inv.third_income_withholding == 0.0 and inv.third_withheld_itbis == 0.0:

                                for invoices in payment_id.payment_invoice_ids:
                                    if invoices.invoice_id == inv and (not payment_id.withold_itbis_select.sale_itbis_retention_type in ('01', False)):
                                        withholded_itbis += invoices.itbis_withold
                                    income_withholding += invoices.isr_withold
                                if payment_id.withold_itbis_select.sale_itbis_retention_type != '01' and withholded_itbis > 0.0:
                                    inv.sale_itbis_retention_type = payment_id.withold_itbis_select.sale_itbis_retention_type
                                inv.third_withheld_itbis = withholded_itbis
                                inv.third_income_withholding = income_withholding
                                if withholded_itbis == 0.0:
                                    inv.payment_date = False
                                    inv.sale_itbis_retention_type = False



            if inv.move_type == 'in_invoice' and inv.payment_state not in ('paid','in_payment'):
                inv.income_withholding = None
                inv.withholded_itbis = None

            if inv.move_type == 'out_invoice' and inv.payment_state not in ('paid','in_payment'):
                inv.third_withheld_itbis = None
                inv.third_income_withholding = None



    @api.depends('invoiced_itbis', 'cost_itbis', 'state')
    def _compute_advance_itbis(self):
        for inv in self:
            inv.advance_itbis = inv.invoiced_itbis - inv.cost_itbis

    @api.depends('journal_id.type')
    def _compute_is_exterior(self):
        for inv in self:
            inv.is_exterior = True if inv.journal_id.type == \
                'exterior' else False

    @api.onchange('service_type')
    def onchange_service_type(self):
        self.service_type_detail = False
        return {
            'domain': {
                'service_type_detail': [
                    ('parent_code', '=', self.service_type)
                    ]
            }
        }

    @api.onchange('journal_id')
    def ext_onchange_journal_id(self):
        self.service_type = False
        self.service_type_detail = False

    # ISR Percibido       --> Este campo se va con 12 espacios en 0 para el 606
    # ITBIS Percibido     --> Este campo se va con 12 espacios en 0 para el 606
    payment_date = fields.Date(compute='_compute_invoice_payment_date', store=False)
    service_total_amount = fields.Monetary(
        compute='_compute_amount_fields',
        store=False,
        currency_field='currency_id')
    good_total_amount = fields.Monetary(compute='_compute_amount_fields',
                                        store=False,
                                        currency_field='currency_id')
    invoiced_itbis = fields.Monetary(compute='_compute_invoiced_itbis',
                                     store=False,
                                     currency_field='currency_id')
    withholded_itbis = fields.Monetary(compute='_compute_withheld_taxes',
                                       store=False,
                                       currency_field='currency_id')
    proportionality_tax = fields.Monetary(compute='_compute_taxes_fields',
                                          store=False,
                                          currency_field='currency_id')
    cost_itbis = fields.Monetary(compute='_compute_taxes_fields',
                                 store=False,
                                 currency_field='currency_id')
    advance_itbis = fields.Monetary(compute='_compute_advance_itbis',
                                    store=False,
                                    currency_field='currency_id')
    isr_withholding_type = fields.Char(compute='_compute_isr_withholding_type',
                                       store=False,
                                       size=2)
    income_withholding = fields.Monetary(compute='_compute_withheld_taxes',
                                         store=False,
                                         currency_field='currency_id')
    selective_tax = fields.Monetary(compute='_compute_taxes_fields',
                                    store=False,
                                    currency_field='currency_id')
    other_taxes = fields.Monetary(compute='_compute_taxes_fields',
                                  store=False,
                                  currency_field='currency_id')
    legal_tip = fields.Monetary(compute='_compute_taxes_fields',
                                store=False,
                                currency_field='currency_id')
    payment_form = fields.Selection([('01', 'Cash'),
                                     ('02', 'Check / Transfer / Deposit'),
                                     ('03', 'Credit Card / Debit Card'),
                                     ('04', 'Credit'), ('05', 'Swap'),
                                     ('06', 'Credit Note'), ('07', 'Mixed')],
                                    compute='_compute_in_invoice_payment_form',
                                    store=False)
    third_withheld_itbis = fields.Monetary(
        compute='_compute_withheld_taxes',
        store=False,
        currency_field='currency_id')
    third_income_withholding = fields.Monetary(
        compute='_compute_withheld_taxes',
        store=False,
        currency_field='currency_id')
    is_exterior = fields.Boolean(compute='_compute_is_exterior', store=False)
    service_type = fields.Selection([
        ('01', 'Gastos de Personal'),
        ('02', 'Gastos por Trabajos, Suministros y Servicios'),
        ('03', 'Arrendamientos'), ('04', 'Gastos de Activos Fijos'),
        ('05', 'Gastos de Representación'), ('06', 'Gastos Financieros'),
        ('07', 'Gastos de Seguros'),
        ('08', 'Gastos por Regalías y otros Intangibles')
    ])
    service_type_detail = fields.Many2one('invoice.service.type.detail')

    fiscal_status = fields.Selection(
        [('normal', 'Partial'), ('done', 'Reported'), ('blocked', 'Not Sent')],
        copy=False,
        help="* The \'Grey\' status means ...\n"
        "* The \'Green\' status means ...\n"
        "* The \'Red\' status means ...\n"
        "* The blank status means that the invoice have"
        "not been included in a report."
    )

    @api.model
    def norma_recompute(self):
        """
        This method add all compute fields into []env
        add_todo and then recompute
        all compute fields in case dgii config change and need to recompute.
        :return:
        """
        active_ids = self._context.get("active_ids")
        invoice_ids = self.browse(active_ids)
        for k, v in self.fields_get().items():
            if v.get("store") and v.get("depends"):
                self.env.add_to_compute(self._fields[k], invoice_ids)

        self.recompute()
