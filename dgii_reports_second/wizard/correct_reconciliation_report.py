from odoo import _, fields, models
from odoo.exceptions import ValidationError, UserError
import calendar
from datetime import datetime as dt


class CreateWithholdingTaxCert(models.TransientModel):
    _name = "correct.reconciliation.report"
    _description = "Correct reconciliation report"

    report_date = fields.Date(
        string='Fecha de reporte',
        default=lambda self: fields.Datetime.now()
    )

    name = fields.Char(string='Periodo', required=True, size=7)

    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company
    )

    journal_id = fields.Many2one(
        'account.journal', string='Diario (Banco)',
        domain=[('type', '=', 'bank')], required=True
    )

    def validate_data(self):
        if len(self.name) != 7:
            raise ValidationError(_('El periodo esta incompleto o mal escrito, favor arreglar.'))
        return True

    def get_name_date(self):
        month, year = self.name.split('/')
        last_day = calendar.monthrange(int(year), int(month))[1]
        end_date = '{}{}{}'.format(year, month, last_day)
        return end_date

    def get_report_datas(self):

        fecha_conciliacion = str(self.get_name_date())

        balance_banco = 0.0

        WHERE_BALANCE_BANK = (
            _("t2.date <= '%s' and t0.journal_id = %s and t0.state in ('posted','confirm')", fecha_conciliacion,
              str(self.journal_id.id)))
        # raise UserError(_("%s", WHERE_INIT))
        cr = self.env.cr
        sql = ('''select (select t5.balance_start from account_bank_statement t5 
                                                            where t5.state in ('posted','confirm') 
                                                            and t5.journal_id = t0.journal_id order by t5.date asc limit 1 )
								+ sum(t1.amount)							
                                                            as balance
                                from account_bank_statement t0
								left join account_bank_statement_line t1 on t1.statement_id = t0.id
								left join account_move t2 on t1.move_id = t2.id
                                where %s
								group by t0.journal_id 
                        ''') % WHERE_BALANCE_BANK
        cr.execute(sql)
        balance_banco = 0.0
        row = cr.dictfetchone()
        # raise UserError(_('%s', row is not None))
        if row is not None:
            balance_banco = row.get('balance') or 0.0

        WHERE_PP = (
            _("t1.date <= '%s' and t1.state in ('posted') and t0.account_id in "
              "(t8.payment_credit_account_id,t8.payment_debit_account_id) and (t5.max_date > '%s' or t5.max_date is null) and t1.journal_id = '%s'"
              ,
              fecha_conciliacion,
              fecha_conciliacion, str(self.journal_id.id)))

        cr_pp = self.env.cr
        sql_pp = ('''
                                    with journal as(
                                    select t0.default_account_id, t0.payment_credit_account_id, 
                                    t0.payment_debit_account_id,t0.suspense_account_id from account_journal t0
                                    where t0.id = %s limit 1
                                    )   
                                    select distinct t1.date as fecha, t1.name as numero,
                                    case when t3.check_number is null then t1.ref else t3.check_number end as cheque_numero
                                    , t6.name as sn,t0.name as detalle, 
                                    case when t2.currency_id = t0.currency_id then abs(t0.amount_currency) else abs(t0.debit - t0.credit) end as monto,
                                    case when t7.code in ('check_printing', 'pdc') then 'cheque'
                                    when t7.code not in ('check_printing', 'pdc') then 'otro' else 'otro' end as metodo_pago,
                                    case when t3.payment_type <> null then t3.payment_type
									when t0.amount_currency <= 0 then 'outbound'
									when t0.amount_currency >= 0 then 'inbound' end as tipo_pago
                                    from account_move_line t0
                                    left join account_move t1 on t0.move_id = t1.id
                                    left join account_journal t2 on t1.journal_id = t2.id
                                    left join account_payment t3 on t1.payment_id = t3.id
                                    left join account_full_reconcile t4 on t0.full_reconcile_id = t4.id
                                    left join account_partial_reconcile t5 on t4.id = t5.full_reconcile_id
                                    left join res_partner t6 on t0.partner_id = t6.id
                                    left join account_payment_method t7 on t3.payment_method_id = t7.id
                                    left join account_move_line t9 on t9.id = t5.debit_move_id,
                                    journal t8
                                    where %s
                                ''') % (str(self.journal_id.id), WHERE_PP)
        cr_pp.execute(sql_pp)
        trans_transito = cr_pp.dictfetchall()

        WHERE_PP2 = (
            _("t1.date <= '%s' and t1.state in ('posted') and t0.account_id in "
              "(t8.payment_credit_account_id,t8.payment_debit_account_id) and (t5.max_date > '%s' or t5.max_date is null) and t1.journal_id != '%s'"
              ,
              fecha_conciliacion,
              fecha_conciliacion, str(self.journal_id.id)))

        cr_pp2 = self.env.cr
        sql_pp2 = ('''
                                            with journal as(
                                            select t0.default_account_id, t0.payment_credit_account_id, 
                                            t0.payment_debit_account_id,t0.suspense_account_id from account_journal t0
                                            where t0.id = %s limit 1
                                            )   
                                            select distinct t1.date as fecha, t1.name as numero,
                                            case when t3.check_number is null then t1.ref else t3.check_number end as cheque_numero
                                            , t6.name as sn,t0.name as detalle, 
                                            case when t2.currency_id = t0.currency_id then abs(t0.amount_currency) else abs(t0.debit - t0.credit) end as monto,
                                            case when t7.code in ('check_printing', 'pdc') then 'cheque'
                                            when t7.code not in ('check_printing', 'pdc') then 'otro' else 'otro' end as metodo_pago,
                                            case when t3.payment_type <> null then t3.payment_type
        									when t0.amount_currency <= 0 then 'outbound'
        									when t0.amount_currency >= 0 then 'inbound' end as tipo_pago
                                            from account_move_line t0
                                            left join account_move t1 on t0.move_id = t1.id
                                            left join account_journal t2 on t1.journal_id = t2.id
                                            left join account_payment t3 on t1.payment_id = t3.id
                                            left join account_full_reconcile t4 on t0.full_reconcile_id = t4.id
                                            left join account_partial_reconcile t5 on t4.id = t5.full_reconcile_id
                                            left join res_partner t6 on t0.partner_id = t6.id
                                            left join account_payment_method t7 on t3.payment_method_id = t7.id
                                            left join account_move_line t9 on t9.id = t5.debit_move_id,
                                            journal t8
                                            where %s
                                        ''') % (str(self.journal_id.id), WHERE_PP2)
        cr_pp2.execute(sql_pp2)
        trans_transito_nodiario = cr_pp2.dictfetchall()

        # raise UserError(_("%s", trans_transito))

        WHERE_BP = (
            _("t1.date <= '%s' and t1.state in ('posted', 'confirm') and t2.id = %s and "
              "t8.account_id in (t2.suspense_account_id) and (t5.max_date > '%s' or t5.max_date is null) ",
              fecha_conciliacion, str(self.journal_id.id),
              fecha_conciliacion))

        cr_bp = self.env.cr
        sql_bp = ('''
                                    select t1.date as fecha, t1.name as numero
                                    , t6.name as sn,t8.name as detalle, 
                                    abs(t0.amount) as monto,
                                    case when t0.amount > 0 then 'entrante'
                                    when t0.amount < 0 then 'saliente' else 'cero' end as tipo_trans_banco
                                    from account_bank_statement_line t0
                                    left join account_move t1 on t0.move_id = t1.id
                                    left join account_move_line t8 on t1.id = t8.move_id
                                    left join account_journal t2 on t1.journal_id = t2.id
                                    left join account_full_reconcile t4 on t8.full_reconcile_id = t4.id
                                    left join account_partial_reconcile t5 on t4.id = t5.full_reconcile_id
                                    left join res_partner t6 on t0.partner_id = t6.id
                                    where %s
                                        ''') % WHERE_BP
        cr_bp.execute(sql_bp)
        bank_trans_transito = cr_bp.dictfetchall()

        WHERE_BL = (
            _("t1.date <= '%s' and t1.state in ('posted') and "
              "t0.account_id in (t3.default_account_id,t3.payment_debit_account_id,t3.payment_credit_account_id)",
              fecha_conciliacion))

        cr_bl = self.env.cr

        if self.journal_id.currency_id == self.company_id.currency_id:
            sql_bl = ('''
                               with journal as(
                                select t0.default_account_id, t0.payment_credit_account_id, 
                                    t0.payment_debit_account_id,t0.suspense_account_id from account_journal t0
                                    where t0.id = %s limit 1
                                )
                                select
                                sum(t0.debit - t0.credit) as balance
                                from account_move_line t0
                                left join account_move t1 on t0.move_id = t1.id
                                left join account_journal t2 on t1.journal_id = t2.id,
                                journal t3
                                where %s
                                                    ''') % (str(self.journal_id.id), WHERE_BL)
        elif self.journal_id.currency_id != self.company_id.currency_id:
            sql_bl = ('''
                               with journal as(
                                select t0.default_account_id, t0.payment_credit_account_id, 
                                    t0.payment_debit_account_id,t0.suspense_account_id from account_journal t0
                                    where t0.id = %s limit 1
                                )
                                select
                                sum(t0.amount_currency) as balance
                                from account_move_line t0
                                left join account_move t1 on t0.move_id = t1.id
                                left join account_journal t2 on t1.journal_id = t2.id,
                                journal t3
                                where %s
                                                    ''') % (str(self.journal_id.id), WHERE_BL)

        cr_bl.execute(sql_bl)
        row_bl = cr_bl.dictfetchone()
        balance_libro = 0.0
        if row_bl is not None:
            balance_libro = row_bl.get('balance') or 0.0

        return balance_banco, trans_transito, bank_trans_transito, balance_libro,trans_transito_nodiario

    def get_name_date_formated(self):
        month, year = self.name.split('/')
        last_day = calendar.monthrange(int(year), int(month))[1]
        end_datestr = '{}-{}-{}'.format(year, month, last_day)
        end_date = dt.strptime(end_datestr, '%Y-%m-%d')
        return end_date

    def action_pdf(self):
        balance_banco, trans_transito, bank_trans_transito, balance_libro,trans_transito_nodiario = self.get_report_datas()
        ids = self.read()[0]

        data = {
            'model': 'create.withholding.tax.cert',
            'form': self.read()[0],
            'cuenta_mayor': self.journal_id.default_account_id.code + '-' + self.journal_id.default_account_id.name,
            'banco': self.journal_id.bank_id.name,
            'numero_cuenta': self.journal_id.bank_account_id.acc_number,
            'moneda_simbolo': self.journal_id.currency_id.name,
            'fecha': self.get_name_date_formated(),
            'balance_banco': balance_banco,
            'currency_id': self.journal_id.currency_id.id,
            'trans_transito': trans_transito,
            'report_file_name': self.journal_id.default_account_id.code + " - Reporte de conciliacion bancaria - " + self.get_name_date(),
            'balance_libro': balance_libro,
            'bank_trans_transito': bank_trans_transito,
            'trans_transito_nodiario': trans_transito_nodiario,
            'companyid': self.company_id.id,

        }
        id = data['form']['id']

        wizard = self.env['correct.reconciliation.report'].browse(id)
        data['docs'] = wizard

        return self.env.ref(
            'dgii_reports_second'
            '.action_correct_reconciliation_report_receipte').report_action(
            self, data=data)

    def action_view(self):
        res = {
            'type': 'ir.actions.client',
            'name': 'Certificado de retencion: Rango de fecha',
            'tag': 'tax.cert.wizard',
            'context': {'wizard_id': self.id}
        }
        return res