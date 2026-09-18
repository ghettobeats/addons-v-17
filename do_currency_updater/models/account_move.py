from odoo import models, api, fields, _
from odoo.exceptions import UserError
from functools import lru_cache


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    recalculate_manual = fields.Boolean(string='Recalcular moneda manualmente', default=False,
        help="You can check this box to use a manual method to calculate the currency amount")

    currency_rate = fields.Float(string='Tasa de cambio', store=False, tracking=False,
        compute='_compute_currency_rate', readonly=False,digits=(16, 5))


    currency_rate_stored = fields.Float(string='Tasa de cambio', store=True, tracking=True, readonly=False,digits=(16, 5)) 


    is_currency_different = fields.Boolean("Currency in invoice different?",compute="compute_rate_do", store=False)

    @api.depends('currency_id','invoice_origin', 'state')
    def compute_rate_do(self):
        for inv in self:
            inv.is_currency_different = False
            sale_order = inv.env['sale.order'].search([('name', '=', inv.invoice_origin)])
            if (not inv.invoice_origin or not sale_order) and inv.currency_id.id != inv.company_id.currency_id.id:
                inv.is_currency_different = True
                if inv.recalculate_manual == False:
                    inv.currency_rate = inv.currency_id._get_conversion_rate(inv.currency_id, inv.company_id.currency_id, inv.company_id,
                                                inv.date or fields.Date.context_today(self))


            if inv.invoice_origin and sale_order  and inv.currency_id.id != inv.company_id.currency_id.id:
                inv.is_currency_different = True
                if sale_order.currency_id.id != inv.currency_id.id and inv.recalculate_manual == False:
                    inv.currency_rate = sale_order.currency_id._get_conversion_rate(sale_order.currency_id, inv.company_id.currency_id, inv.company_id,
                                                inv.date or fields.Date.context_today(self))


    @api.onchange('currency_id','invoice_origin', 'state','recalculate_manual','currency_rate_stored')
    def _compute_currency_rate(self):
        for inv in self:
            inv.currency_rate = 0.0
            sale_order = inv.env['sale.order'].search([('name', '=', inv.invoice_origin)])
            if not (inv.invoice_origin or not sale_order) and inv.currency_id.id != inv.company_id.currency_id.id:
                if inv.recalculate_manual == False:
                    inv.currency_rate = inv.currency_id._get_conversion_rate(inv.currency_id, inv.company_id.currency_id, inv.company_id,
                                                inv.date or fields.Date.context_today(self))

                    if inv.currency_rate_stored == 0.0:
                        inv.currency_rate_stored = inv.currency_rate

            if inv.invoice_origin and sale_order:
                if (sale_order.currency_id != inv.currency_id) and inv.recalculate_manual == False and inv.currency_id.id != inv.company_id.currency_id.id:
                    inv.currency_rate = sale_order.currency_id._get_conversion_rate(sale_order.currency_id, inv.company_id.currency_id, inv.company_id,
                                                inv.date or fields.Date.context_today(self))
                    if inv.currency_rate_stored == 0.0:
                        inv.currency_rate_stored = inv.currency_rate

    @api.onchange('recalculate_manual', 'currency_rate_stored')
    def recalculate_amount_currency(self):
        for inv in self:
            if inv.recalculate_manual == True:
                old_values = []
                for line in inv.line_ids:
                    old_values.append((1,line.id,line.copy_data()[0]))

                difference = 0.0
                for lo in old_values:
                    if lo[2]['debit'] != 0.0 and inv.recalculate_manual == True:
                        monto = round(lo[2]['amount_currency'] * inv.currency_rate_stored, inv.currency_id.decimal_places)
                        lo[2]['debit'] = monto
                        difference += monto
                    if lo[2]['credit'] != 0.0 and inv.recalculate_manual == True:
                        monto = round(abs(lo[2]['amount_currency'] * inv.currency_rate_stored), inv.currency_id.decimal_places)
                        lo[2]['credit'] = monto
                        difference -= monto

                difference = round(difference, inv.currency_id.decimal_places)

                if difference > 0.0:
                    for lo in old_values:
                        if lo[2]['debit'] > 0:
                            lo[2]['debit'] -= difference
                            break

                if difference < 0.0:
                    for lo in old_values:
                        if lo[2]['credit'] > 0:
                            lo[2]['credit'] -= abs(difference)
                            break

                # inv.line_ids.unlink()
                inv.write({"line_ids":old_values})


    @api.onchange('currency_id', 'invoice_date')
    def recalculation_amount_by_currency(self):
        for inv in self:
            if inv.currency_id != inv.company_id.currency_id and inv.recalculate_manual == True:
                amount_currency_orig = []
                amount_inv_price = []
                amount_inv_subtotal = []
                current_date = inv.invoice_date or fields.Date.today()
                currency = inv.currency_id
                from_currency = inv.company_id.currency_id.with_context(date=current_date)
                to_currency = inv.currency_id.with_context(date=current_date)
                if to_currency != inv.company_id.currency_id:
                    amount_currency_orig.clear()
                    for inv_line in inv.line_ids:
                        amount_currency_orig.append(inv_line.amount_currency)

                    if inv.move_type != ('entry'):
                        amount_inv_price.clear()
                        amount_inv_subtotal.clear()
                        for inv_line in inv.invoice_line_ids:
                            amount_inv_price.append(inv_line.price_unit)
                            amount_inv_subtotal.append(inv_line.price_subtotal)

                    # if inv.move_type != ('entry'):
                    #     for inv_line in inv.invoice_line_ids:
                    #         inv_line.price_unit = currency._compute(from_currency, to_currency,
                    #                                                 inv_line.price_unit)
                    #         inv_line.price_subtotal = currency._compute(from_currency, to_currency,
                    #                                                     inv_line.price_subtotal)
                    for inv_line in inv.line_ids:
                        inv_line.amount_currency = currency._compute(from_currency, to_currency,
                                                                     inv_line.amount_currency)
                        inv_line.currency_id = to_currency

                        balance = inv.currency_id._convert(inv_line.amount_currency, inv.company_id.currency_id,
                                                           inv.company_id,
                                                           inv.date or fields.Date.context_today(self))
                        inv_line.debit = balance > 0.0 and balance or 0.0
                        inv_line.credit = balance < 0.0 and -balance or 0.0



