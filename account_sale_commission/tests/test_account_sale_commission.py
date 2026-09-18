#  Copyright (c) 2018 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.

from datetime import datetime, timedelta
from odoo import fields
from odoo.tests.common import TransactionCase


class TestAccountSaleCommission(TransactionCase):

    def setUp(self):
        super(TestAccountSaleCommission, self).setUp()

        self.acct_inv_obj = self.env['account.invoice']
        self.prd_tmpl_obj = self.env['product.template']
        self.prd_cteg_obj = self.env['product.category']
        self.acct_jnl_obj = self.env['account.journal']
        self.regr_pay_obj = self.env['account.register.payments']
        self.acct_mov_obj = self.env['account.move']
        self.acct_acc_obj = self.env['account.account']
        self.res_user_obj = self.env['res.users'].with_context({'no_reset_password': True})

        # Commission Settings default Params
        self.ICPSudo = self.env['ir.config_parameter'].sudo()
        self.ICPSudo.set_param('account_sale_commission.commission_schema', 'liquidate')
        self.ICPSudo.set_param('account_sale_commission.commission_base', 'gross')
        self.ICPSudo.set_param('account_sale_commission.commission_beneficiary', 'invoice')
        self.ICPSudo.set_param('account_sale_commission.commission_currency_rate', 'invoice')

        # Contacts
        self.invoice_salesperson = self.res_user_obj.create({
            'name': 'Test Salesperson',
            'login': 'test_salesperson',
            'email': 'test1@test.com',
        })
        self.customer_salesperson = self.res_user_obj.create({
            'name': 'Test Customer Salesperson',
            'login': 'test_customer_salesperson',
            'email': 'test2@test.com'
        })
        self.invoice_payment_collector = self.res_user_obj.create({
            'name': 'Test Payment collector',
            'login': 'test_payment',
            'email': 'test3@test.com',
            'groups_id': [(6, 0, [self.env.ref('account.group_account_invoice').id])]
        })
        self.customer = self.env['res.partner'].create({'name': 'Test Customer', 'customer': True,
                                                        'user_id': self.customer_salesperson.id})

        # ----------------
        # Account settings

        # General stuff
        self.account_goods_sale = self.acct_acc_obj.create(
            {'code': 'Y1010', 'name': 'Goods Sale',
             'user_type_id': self.env.ref('account.data_account_type_revenue').id})
        self.account_receivable = self.acct_acc_obj.create(
            {'code': 'Z1010', 'name': 'Account Receivable', 'reconcile': True,
             'user_type_id': self.env.ref('account.data_account_type_receivable').id})
        self.account_exchange_income = self.acct_acc_obj.create(
            {'code': 'I1010', 'name': 'Exchange Income', 'reconcile': True,
             'user_type_id': self.env.ref('account.data_account_type_other_income').id})
        self.account_exchange_expense = self.acct_acc_obj.create(
            {'code': 'T1010', 'name': 'Exchange Expense', 'reconcile': True,
             'user_type_id': self.env.ref('account.data_account_type_expenses').id})
        self.account_payable = self.acct_acc_obj.create(
            {'code': 'Q1010', 'name': 'Account Payable', 'reconcile': True,
             'user_type_id': self.env.ref('account.data_account_type_payable').id})
        self.payment_term_immediate = self.env['account.payment.term'].create(
            {'name': 'Immediate Payment', 'note': 'Payment terms: Inmediate Payment'})
        self.tax_group = self.env['account.tax.group'].create({'name': 'ITBIS'})
        self.tax_18_sale = self.env['account.tax'].create(
            {'name': '18% ITBIS', 'type_tax_use': 'sale', 'amount_type': 'percent', 'amount': 18,
             'tax_group_id': self.tax_group.id})
        self.usd_currency = self.env.ref('base.USD')
        self.date_15_ago = datetime.now().date() - timedelta(days=15)
        self.env['res.currency.rate'].create({
            'name': self.date_15_ago, 'currency_id': self.usd_currency.id, 'rate': 0.01996007984})
        self.env['res.currency.rate'].create({
            'name': datetime.now().date(), 'currency_id': self.usd_currency.id, 'rate': 0.01984126984})

        # Payment method
        self.payment_method_manual_in = self.env.ref("account.account_payment_method_manual_in")

        # Sale Journal
        self.sale_journal_id = self.acct_jnl_obj.create({
            'name': 'Test Sale Journal',
            'type': 'sale',
            'code': 'TSJ'
        })
        # Exchange Rate Journal
        self.exchange_rate_journal_id = self.acct_jnl_obj.create({
            'name': 'Test Exchange Rate Journal',
            'type': 'general',
            'code': 'TEXRJ'
        })

        # Commission entries Journal
        self.commission_journal_id = self.env.ref('account_sale_commission.demo_commission_journal')

        # Payment Journals
        self.bank_journal_id = self.env.ref('account_sale_commission.demo_bank_journal')
        self.cash_journal_id = self.env.ref('account_sale_commission.demo_cash_journal')
        self.check_journal_id = self.env.ref('account_sale_commission.demo_check_journal')

        # Company level Commission Setup
        self.company_id = self.env.ref('base.main_company')
        self.company_id.currency_exchange_journal_id = self.exchange_rate_journal_id.id
        self.company_id.income_currency_exchange_account_id = self.account_exchange_income.id
        self.company_id.expense_currency_exchange_account_id = self.account_exchange_expense.id
        self.company_id.currency_id = self.env.ref('base.DOP').id
        self.company_id.commission_journal_id = self.env.ref('account_sale_commission.demo_commission_journal').id
        self.company_id.commission_debit_account = self.env.ref('account_sale_commission.demo_expenses').id
        self.company_id.commission_credit_account = self.env.ref(
            'account_sale_commission.demo_non_current_liabilities').id

        # Property fields Setup
        self.customer.property_account_receivable_id = self.account_receivable.id
        self.customer.property_account_payable_id = self.account_payable.id

        # ----------------
        # Product settings

        # Product Categories
        self.c_both_category_id = self.prd_cteg_obj.create(
            {'name': 'Commission Category',
             'commission': True,
             'percentage': 10,
             'fixed_amount': 5})
        self.c_percentage_category_id = self.prd_cteg_obj.create(
            {'name': 'Commission Category',
             'commission': True,
             'percentage': 10})
        self.c_fixed_amount_category_id = self.prd_cteg_obj.create(
            {'name': 'Commission Category',
             'commission': True,
             'fixed_amount': 5})
        self.no_comm_category_id = self.prd_cteg_obj.create(
            {'name': 'Commission Category'})

        # Products
        self.product_tmpl_1_id = self.prd_tmpl_obj.create({  # This product get commission params from its category
            'name': 'Test Product 1',
            'sale_ok': True,
            'commission_ok': True,
            'categ_id': self.c_both_category_id.id
        })
        self.product_tmpl_2_id = self.prd_tmpl_obj.create({  # This product get commission params from its category
            'name': 'Test Product 2',
            'sale_ok': True,
            'commission_ok': True,
            'categ_id': self.c_percentage_category_id.id
        })
        self.product_tmpl_3_id = self.prd_tmpl_obj.create({  # This product get commission params from its category
            'name': 'Test Product 3',
            'sale_ok': True,
            'commission_ok': True,
            'categ_id': self.c_fixed_amount_category_id.id
        })
        self.product_tmpl_4_id = self.prd_tmpl_obj.create({  # This product sets its own commission params
            'name': 'Test Product 4',
            'sale_ok': True,
            'commission_ok': True,
            'categ_id': self.c_both_category_id.id,
            'percentage': 13,
            'fixed_amount': 4
        })
        self.product_tmpl_5_id = self.prd_tmpl_obj.create({  # This product should not generate commission entries
            'name': 'Test Product 5',  # because of its category and because has not commission
            'sale_ok': True,  # params itself
            'commission_ok': True,
            'categ_id': self.no_comm_category_id.id
        })

        # Creates an invoice which will be used for all commission use case

        self.invoice_id = self.acct_inv_obj.create({
            'type': 'out_invoice',
            'partner_id': self.customer.id,
            'date_invoice': self.date_15_ago,
            'user_id': self.invoice_salesperson.id,
            'account_id': self.account_receivable.id,
            'payment_term_id': self.payment_term_immediate.id,
            'journal_id': self.sale_journal_id.id,
            'invoice_line_ids': [
                (0, 0,
                 {'product_id': p.id, 'quantity': 1,
                  'account_id': self.account_goods_sale.id,
                  'name': p.name,
                  'price_unit': 100.00,
                  'invoice_line_tax_ids': [(4, self.tax_18_sale.id)]})
                for p in self.env['product.product'].search(
                    [('product_tmpl_id', 'in', [self.product_tmpl_1_id.id, self.product_tmpl_2_id.id,
                                                self.product_tmpl_3_id.id, self.product_tmpl_4_id.id,
                                                self.product_tmpl_5_id.id])])]
        })
        self.invoice_id.action_invoice_open()

        # USD invoice
        self.usd_invoice_id = self.invoice_id.copy({'currency_id': self.usd_currency.id})
        self.usd_invoice_id.action_invoice_open()

    def test_commission_setting_default_params(self):
        """ Test all commission default params are set """

        self.assertEquals(self.ICPSudo.get_param('account_sale_commission.commission_schema'), 'liquidate')
        self.assertEquals(self.ICPSudo.get_param('account_sale_commission.commission_base'), 'gross')
        self.assertEquals(self.ICPSudo.get_param('account_sale_commission.commission_beneficiary'), 'invoice')
        self.assertEquals(self.ICPSudo.get_param('account_sale_commission.commission_currency_rate'), 'invoice')

    def test_use_case_001(self):
        """ Commission Test Use Case #1 (Default behavior)
            commission_schema: liquidate
            commission_base: gross
            commission_beneficiary: invoice
            commission_currency_rate: invoice
            move_date: create_date
        """
        ctx = {'active_model': 'account.invoice', 'active_ids': [self.invoice_id.id]}
        register_payments = self.regr_pay_obj.with_context(ctx).create({
            'payment_date': self.invoice_id.date_invoice,
            'journal_id': self.bank_journal_id.id,
            'payment_method_id': self.payment_method_manual_in.id,
            'amount': self.invoice_id.amount_total  # Full invoice payment
        })
        register_payments.create_payments()

        account_move_id = self.acct_mov_obj.search(
            [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

        # Use Case 1 Commission Formula: ((price * qty) * percentage) + fixed_amount
        # product_1_commission = ((100 * 1) * 0.10) + 5 = 15
        # product_2_commission = ((100 * 1) * 0.10) + 0 = 10
        # product_3_commission = ((100 * 1) * 0) + 5    =  5
        # product_4_commission = ((100 * 1) * 0.13) + 4 = 17
        # product_5_commission = 0                      =  0
        # ---------------------------------------------------
        #                             Commission Total =  47

        move_total = []
        partner_set = set()
        for aml in account_move_id.line_ids:
            move_total.append(aml.debit + aml.credit)
            partner_set.add(aml.partner_id.id)
        commission = sum(move_total) / 2

        # Check there is only one partner for this commission journal entry
        self.assertEquals(len(partner_set), 1)

        # Check commission beneficiary is invoice salesperson
        self.assertEquals(partner_set.pop(), self.invoice_salesperson.partner_id.id)

        # Check commission amount
        self.assertEquals(commission, 47)

    def test_use_case_002(self):
        """ Commission Test Use Case #2
            commission_schema: liquidate
            commission_base: net
            commission_beneficiary: invoice
            commission_currency_rate: invoice
            move_date: create_date
        """
        self.ICPSudo.set_param('account_sale_commission.commission_base', 'net')
        ctx = {'active_model': 'account.invoice', 'active_ids': [self.invoice_id.id]}
        register_payments = self.regr_pay_obj.with_context(ctx).create({
            'payment_date': self.invoice_id.date_invoice,
            'journal_id': self.bank_journal_id.id,
            'payment_method_id': self.payment_method_manual_in.id,
            'amount': self.invoice_id.amount_total  # Full invoice payment
        })
        register_payments.create_payments()

        account_move_id = self.acct_mov_obj.search(
            [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

        # Use Case 2 Commission Formula: ((price * qty * tax) * percentage) + fixed_amount
        # product_1_commission = ((100 * 1 * 1.18) * 0.10) + 5 = 16.8
        # product_2_commission = ((100 * 1 * 1.18) * 0.10) + 0 = 11.8
        # product_3_commission = ((100 * 1 * 1.18) * 0) + 5    =  5
        # product_4_commission = ((100 * 1 * 1.18) * 0.13) + 4 = 19.34
        # product_5_commission = 0                             =  0
        # ------------------------------------------------------------
        #                                    Commission Total =  52.94

        move_total = []
        for aml in account_move_id.line_ids:
            move_total.append(aml.debit + aml.credit)
        commission = sum(move_total) / 2

        # Check commission amount
        self.assertEquals(commission, 52.94)

    def test_use_case_003(self):
        """ Commission Test Use Case #3
            commission_schema: pays
            commission_base: gross
            commission_beneficiary: invoice
            commission_currency_rate: invoice
            move_date: create_date
        """
        self.ICPSudo.set_param('account_sale_commission.commission_schema', 'pays')
        ctx = {'active_model': 'account.invoice', 'active_ids': [self.invoice_id.id]}

        while self.invoice_id.residual > 0:

            register_payments = self.regr_pay_obj.with_context(ctx).create({
                'payment_date': self.invoice_id.date_invoice,
                'journal_id': self.bank_journal_id.id,
                'payment_method_id': self.payment_method_manual_in.id,
                'amount': self.invoice_id.amount_total / 5  # 1/5 of invoice total
            })
            register_payments.create_payments()

            account_move_id = self.acct_mov_obj.search(
                [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

            # Use Case 3 Commission Formula: (((price * qty) * amount_paid / (price * qty)) * percentage) + fixed_amount
            # product_1_commission = (((100 * 1) * 23.6 / (100 * 1)) * 0.10) + 5 = 7.36
            # product_2_commission = (((100 * 1) * 23.6 / (100 * 1)) * 0.10) + 0 = 2.36
            # product_3_commission = (((100 * 1) * 23.6 / (100 * 1)) * 0) + 5    = 5
            # product_4_commission = (((100 * 1) * 23.6 / (100 * 1)) * 0.13) + 4 = 7.068
            # product_5_commission = 0                                           = 0
            # -----------------------------------------------------------------------
            #                                                   Commission Total = 21.788

            move_total = []
            for aml in account_move_id.line_ids:
                move_total.append(aml.debit + aml.credit)
            commission = sum(move_total) / 2

            x = 21.788 if self.invoice_id.residual >= self.invoice_id.amount_total / 5 else 15.848

            # Check commission amount
            self.assertEquals(round(commission, 3), x)

    def test_use_case_004(self):
        """ Commission Test Use Case #4
            commission_schema: pays
            commission_base: net
            commission_beneficiary: invoice
            commission_currency_rate: invoice
            move_date: create_date
        """
        self.ICPSudo.set_param('account_sale_commission.commission_schema', 'pays')
        self.ICPSudo.set_param('account_sale_commission.commission_base', 'net')
        ctx = {'active_model': 'account.invoice', 'active_ids': [self.invoice_id.id]}

        while self.invoice_id.residual > 0:

            register_payments = self.regr_pay_obj.with_context(ctx).create({
                'payment_date': self.invoice_id.date_invoice,
                'journal_id': self.bank_journal_id.id,
                'payment_method_id': self.payment_method_manual_in.id,
                'amount': self.invoice_id.amount_total / 5  # 1/5 of invoice total
            })
            register_payments.create_payments()

            account_move_id = self.acct_mov_obj.search(
                [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

            # Use Case 1 Commission Formula: (((price * qty) * amount_paid / (price * qty)) * percentage) + fixed_amount
            # product_1_commission = (((100 * 1) * 23.6 / (100 * 1)) * 0.10) + 5 = 7.36
            # product_2_commission = (((100 * 1) * 23.6 / (100 * 1)) * 0.10) + 0 = 2.36
            # product_3_commission = (((100 * 1) * 23.6 / (100 * 1)) * 0) + 5    = 5
            # product_4_commission = (((100 * 1) * 23.6 / (100 * 1)) * 0.13) + 4 = 7.068
            # product_5_commission = 0                                           = 0
            # -----------------------------------------------------------------------
            #                                                   Commission Total = 21.788

            move_total = []
            for aml in account_move_id.line_ids:
                move_total.append(aml.debit + aml.credit)
            commission = sum(move_total) / 2

            # Check commission amount
            self.assertEquals(round(commission, 3), 21.788)

    def test_use_case_005(self):
        """ Commission Test Use Case #5
            commission_schema: liquidate
            commission_base: gross
            commission_beneficiary: partner
            commission_currency_rate: invoice
            move_date: create_date
        """
        self.ICPSudo.set_param('account_sale_commission.commission_beneficiary', 'partner')
        ctx = {'active_model': 'account.invoice', 'active_ids': [self.invoice_id.id]}
        register_payments = self.regr_pay_obj.with_context(ctx).create({
            'payment_date': self.invoice_id.date_invoice,
            'journal_id': self.bank_journal_id.id,
            'payment_method_id': self.payment_method_manual_in.id,
            'amount': self.invoice_id.amount_total  # Full invoice payment
        })
        register_payments.create_payments()

        account_move_id = self.acct_mov_obj.search(
            [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

        partner_set = set()
        for aml in account_move_id.line_ids:
            partner_set.add(aml.partner_id.id)

        # Check there is only one partner for this commission journal entry
        self.assertEquals(len(partner_set), 1)

        # Check commission beneficiary is customer salesperson
        self.assertEquals(partner_set.pop(), self.customer_salesperson.partner_id.id)

    def test_use_case_006(self):
        """ Commission Test Use Case #6
            commission_schema: liquidate
            commission_base: gross
            commission_beneficiary: payment
            commission_currency_rate: invoice
            move_date: create_date
        """
        self.ICPSudo.set_param('account_sale_commission.commission_beneficiary', 'payment')
        ctx = {'active_model': 'account.invoice', 'active_ids': [self.invoice_id.id]}
        register_payments = self.regr_pay_obj.with_context(ctx).sudo(user=self.invoice_payment_collector.id).create({
            'payment_date': self.invoice_id.date_invoice,
            'journal_id': self.bank_journal_id.id,
            'payment_method_id': self.payment_method_manual_in.id,
            'amount': self.invoice_id.amount_total  # Full invoice payment
        })
        register_payments.create_payments()

        account_move_id = self.acct_mov_obj.search(
            [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

        partner_set = set()
        for aml in account_move_id.line_ids:
            partner_set.add(aml.partner_id.id)

        # Check there is only one partner for this commission journal entry
        self.assertEquals(len(partner_set), 1)

        # Check commission beneficiary is invoice payment collector
        self.assertEquals(partner_set.pop(), self.invoice_payment_collector.partner_id.id)

    def test_use_case_007(self):
        """ Commission Test Use Case #7 (USD invoice)
            commission_schema: liquidate
            commission_base: gross
            commission_beneficiary: invoice
            commission_currency_rate: invoice
            move_date: create_date
        """
        ctx = {'active_model': 'account.invoice', 'active_ids': [self.usd_invoice_id.id]}
        register_payments = self.regr_pay_obj.with_context(ctx).create({
            'payment_date': datetime.today().date(),
            'journal_id': self.bank_journal_id.id,
            'currency_id': self.usd_currency.id,
            'payment_method_id': self.payment_method_manual_in.id,
            'amount': self.invoice_id.amount_total  # Full invoice payment
        })
        register_payments.create_payments()

        account_move_id = self.acct_mov_obj.search(
            [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

        # Use Case 1 Commission Formula: ((price * qty) * percentage) + fixed_amount
        # product_1_commission = ((100 * 1) * 0.10) + 5 = 15
        # product_2_commission = ((100 * 1) * 0.10) + 0 = 10
        # product_3_commission = ((100 * 1) * 0) + 5    =  5
        # product_4_commission = ((100 * 1) * 0.13) + 4 = 17
        # product_5_commission = 0                      =  0
        # ---------------------------------------------------
        #                             Commission Total =  47

        move_total = []
        partner_set = set()
        for aml in account_move_id.line_ids:
            move_total.append(aml.debit + aml.credit)
            partner_set.add(aml.partner_id.id)
        commission = sum(move_total) / 2

        # Check there is only one partner for this commission journal entry
        self.assertEquals(len(partner_set), 1)

        rate = self.env['res.currency.rate'].search([('currency_id', '=', self.usd_currency.id),
                                                     ('name', '=', self.usd_invoice_id.date_invoice)], limit=1)

        # Check commission amount
        self.assertAlmostEqual(round(commission, 3), round(47 / rate.rate, 3))

    def test_use_case_008(self):
        """ Commission Test Use Case #8 (USD invoice)
            commission_schema: liquidate
            commission_base: gross
            commission_beneficiary: invoice
            commission_currency_rate: current
            move_date: create_date
        """
        ctx = {'active_model': 'account.invoice', 'active_ids': [self.usd_invoice_id.id]}
        register_payments = self.regr_pay_obj.with_context(ctx).create({
            'payment_date': datetime.today().date(),
            'journal_id': self.bank_journal_id.id,
            'currency_id': self.usd_currency.id,
            'payment_method_id': self.payment_method_manual_in.id,
            'amount': self.invoice_id.amount_total  # Full invoice payment
        })
        register_payments.create_payments()

        account_move_id = self.acct_mov_obj.search(
            [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

        # Use Case 1 Commission Formula: ((price * qty) * percentage) + fixed_amount
        # product_1_commission = ((100 * 1) * 0.10) + 5 = 15
        # product_2_commission = ((100 * 1) * 0.10) + 0 = 10
        # product_3_commission = ((100 * 1) * 0) + 5    =  5
        # product_4_commission = ((100 * 1) * 0.13) + 4 = 17
        # product_5_commission = 0                      =  0
        # ---------------------------------------------------
        #                             Commission Total =  47

        move_total = []
        partner_set = set()
        for aml in account_move_id.line_ids:
            move_total.append(aml.debit + aml.credit)
            partner_set.add(aml.partner_id.id)
        commission = sum(move_total) / 2

        # Check there is only one partner for this commission journal entry
        self.assertEquals(len(partner_set), 1)

        rate = self.env['res.currency.rate'].search([('currency_id', '=', self.usd_currency.id),
                                                     ('name', '=', datetime.today().date())], limit=1)

        # Check commission amount
        self.assertAlmostEqual(round(commission, 3), round(47 / rate.rate, 3))

    def test_use_case_009(self):
        """ Commission Test Use Case #9
            commission_schema: liquidate
            commission_base: gross
            commission_beneficiary: invoice
            commission_currency_rate: invoice
            move_date: create_date
        """
        ctx = {'active_model': 'account.invoice', 'active_ids': [self.invoice_id.id]}
        register_payments = self.regr_pay_obj.with_context(ctx).create({
            'payment_date': self.date_15_ago,
            'journal_id': self.bank_journal_id.id,
            'payment_method_id': self.payment_method_manual_in.id,
            'amount': self.invoice_id.amount_total  # Full invoice payment
        })
        register_payments.create_payments()

        account_move_id = self.acct_mov_obj.search(
            [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

        # Check move date is equal to payment date
        self.assertEquals(account_move_id.date, self.date_15_ago)

    def test_use_case_010(self):
        """ Commission Test Use Case #10
            commission_schema: liquidate
            commission_base: gross
            commission_beneficiary: invoice
            commission_currency_rate: invoice
            move_date: assignment_date
        """
        self.ICPSudo.set_param('account_sale_commission.move_date', 'assignment_date')
        ctx = {'active_model': 'account.invoice', 'active_ids': [self.invoice_id.id]}
        register_payments = self.regr_pay_obj.with_context(ctx).create({
            'payment_date': self.date_15_ago,
            'journal_id': self.bank_journal_id.id,
            'payment_method_id': self.payment_method_manual_in.id,
            'amount': self.invoice_id.amount_total  # Full invoice payment
        })
        register_payments.create_payments()

        account_move_id = self.acct_mov_obj.search(
            [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

        # Check move date is equal to payment date
        self.assertEquals(account_move_id.date, datetime.today().date())

    def test_use_case_011(self):
        """ Commission Test Use Case #11 (Outstanding credits)

            commission_schema: liquidate
            commission_base: gross
            commission_beneficiary: invoice
            commission_currency_rate: invoice
            move_date: create_date
        """

        payment_a = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_id': self.payment_method_manual_in.id,
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'amount': self.invoice_id.amount_total / 2,
            'currency_id': self.company_id.currency_id.id,
            'journal_id': self.bank_journal_id.id,
            'payment_date': self.date_15_ago,
        })

        payment_a.post()
        credit_aml_a = payment_a.move_line_ids.filtered('credit')
        self.invoice_id.assign_outstanding_credit(credit_aml_a.id)

        # account_move_id = self.acct_mov_obj.search([('journal_id', '=', self.commission_journal_id.id)])
        account_move_id = self.acct_mov_obj.search([('ref', '=', '%s Sales Commission' % self.invoice_id.name)])

        # Check that no commission entry has been created
        # because commission_schema = liquidate and invoice
        # is still open
        self.assertFalse(account_move_id)

        payment_b = self.env['account.payment'].create({
            'payment_type': 'inbound',
            'payment_method_id': self.payment_method_manual_in.id,
            'partner_type': 'customer',
            'partner_id': self.customer.id,
            'amount': self.invoice_id.residual,
            'currency_id': self.company_id.currency_id.id,
            'journal_id': self.bank_journal_id.id,
            'payment_date': self.date_15_ago,
        })

        payment_b.post()
        credit_aml_b = payment_b.move_line_ids.filtered('credit')
        self.invoice_id.assign_outstanding_credit(credit_aml_b.id)

        account_move_id = self.acct_mov_obj.search(
            [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

        # Check if commission entry has been created
        self.assertTrue(account_move_id)

        # Check move date is equal to payment date
        self.assertEquals(account_move_id.date, self.date_15_ago)

        move_total = []
        partner_set = set()
        for aml in account_move_id.line_ids:
            move_total.append(aml.debit + aml.credit)
            partner_set.add(aml.partner_id.id)
        commission = sum(move_total) / 2

        # Check there is only one partner for this commission journal entry
        self.assertEquals(len(partner_set), 1)

        # Check commission beneficiary is invoice salesperson
        self.assertEquals(partner_set.pop(), self.invoice_salesperson.partner_id.id)

        # Check commission amount
        self.assertEquals(commission, 47)

    def test_use_case_012(self):
        """ Commission Test Use Case #12 (Outstanding credits)

            commission_schema: pays
            commission_base: gross
            commission_beneficiary: invoice
            commission_currency_rate: invoice
            move_date: assignment_date
        """
        self.ICPSudo.set_param('account_sale_commission.commission_schema', 'pays')
        self.ICPSudo.set_param('account_sale_commission.move_date', 'assignment_date')

        while self.invoice_id.residual > 0:

            payment = self.env['account.payment'].create({
                'payment_type': 'inbound',
                'payment_method_id': self.payment_method_manual_in.id,
                'partner_type': 'customer',
                'partner_id': self.customer.id,
                'amount': self.invoice_id.amount_total / 5,
                'currency_id': self.company_id.currency_id.id,
                'journal_id': self.bank_journal_id.id,
                'payment_date': self.date_15_ago,
            })

            payment.post()
            credit_aml = payment.move_line_ids.filtered('credit')
            self.invoice_id.assign_outstanding_credit(credit_aml.id)

            account_move_id = self.acct_mov_obj.search(
                [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

            # Check that a commission entry has been created
            # because commission_schema = pays
            self.assertTrue(account_move_id)

            # Check move date is equal to current date
            # because move_date: assignment_date
            self.assertEquals(account_move_id.date, fields.Date.from_string(datetime.today().date()))

            move_total = []
            partner_set = set()
            for aml in account_move_id.line_ids:
                move_total.append(aml.debit + aml.credit)
                partner_set.add(aml.partner_id.id)
            commission = sum(move_total) / 2

            x = 21.788 if self.invoice_id.residual >= self.invoice_id.amount_total / 5 else 15.848

            # Check commission amount
            self.assertEquals(round(commission, 3), x)

            # Check there is only one partner for this commission journal entry
            self.assertEquals(len(partner_set), 1)

            # Check commission beneficiary is invoice salesperson
            self.assertEquals(partner_set.pop(), self.invoice_salesperson.partner_id.id)

    def test_use_case_013(self):
        """ Commission Test Use Case #13 (Default behavior with line discount)
            commission_schema: liquidate
            commission_base: gross
            commission_beneficiary: invoice
            commission_currency_rate: invoice
            move_date: create_date
        """

        discount_invoice_id = self.invoice_id.copy()

        # Set line level discounts
        for line in discount_invoice_id.invoice_line_ids:
            line.discount = 5

        discount_invoice_id.action_invoice_open()

        ctx = {'active_model': 'account.invoice', 'active_ids': [discount_invoice_id.id]}
        register_payments = self.regr_pay_obj.with_context(ctx).create({
            'payment_date': discount_invoice_id.date_invoice,
            'journal_id': self.bank_journal_id.id,
            'payment_method_id': self.payment_method_manual_in.id,
            'amount': discount_invoice_id.amount_total  # Full invoice payment
        })
        register_payments.create_payments()

        account_move_id = self.acct_mov_obj.search(
            [('journal_id', '=', self.commission_journal_id.id)], limit=1, order="id desc")

        # Use Case 1 Commission Formula: (((price * qty) - discount) * percentage) + fixed_amount
        # product_1_commission = (((100 * 1) - ((100 * 1) * 5 / 100)) * 0.10) + 5 = 14.5
        # product_2_commission = (((100 * 1) - ((100 * 1) * 5 / 100)) * 0.10) + 0 =  9.5
        # product_3_commission = (((100 * 1) - ((100 * 1) * 5 / 100)) * 0) + 5    =  5
        # product_4_commission = (((100 * 1) - ((100 * 1) * 5 / 100)) * 0.13) + 4 = 16.35
        # product_5_commission = 0                                                =  0
        # ---------------------------------------------------------------------------------
        #                                                        Commission Total = 45.35

        move_total = []
        partner_set = set()
        for aml in account_move_id.line_ids:
            move_total.append(aml.debit + aml.credit)
            partner_set.add(aml.partner_id.id)
        commission = sum(move_total) / 2

        # Check there is only one partner for this commission journal entry
        self.assertEquals(len(partner_set), 1)

        # Check commission beneficiary is invoice salesperson
        self.assertEquals(partner_set.pop(), discount_invoice_id.user_id.partner_id.id)

        # Check commission amount
        self.assertEquals(commission, 45.35)
