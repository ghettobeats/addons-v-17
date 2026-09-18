# -*- coding: utf-8 -*-
#################################################################################
# Author      : Daniel Diaz ISJO Technology. (<https://isjo-technology.com/>)
# All Rights Reserved.
#################################################################################
{
    'name': "ISJO HR Payroll for Odoo 17",
    'summary': "This module extends the Human Resources Payroll module",
    'description': """
        This module extends the Human Resources Payroll module.

        Developers:
         * Daniel Eduardo Diaz Mateo
    """,
    'author': "ISJO Technology, SRL",
    'website': "http://www.isjo-technology.com",
    'category': 'Human Resources/Payroll',
    'version': '17.0.1.0',
    'license': 'AGPL-3',
    'depends': [
        'base',
        # 'mail',
        'hr_payroll',
        'hr_payroll_account',
        'jt_employee_sequence',
        'utils',
    ],
    'data': [
        # Descomenta los archivos que realmente necesitas:
        'security/groups_special_rule.xml',
        'security/ir.model.access.csv',
        'data/default_settings.xml',
        # 'data/ir_cron.xml',
        'report/reports.xml',
        'data/email_template.xml',
        'wizard/hr_payroll_payslips_by_employees_views.xml',
        'wizard/clone_salary_rule_wizard.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_contract_views.xml',
        'report/payslip_report.xml',
        'report/payslip_run_detailed_report.xml',
    ],
    'demo': [
        # Si tienes datos de demostración, descomenta la siguiente línea:
        # 'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': False,
}
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
