# © 2026 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Employee Additional Fields Customized to SEGASA',
    'version': '17.0.1.0.0',
    'summary': """
        Additional fields for hr.employee model. This is only customized to SEGASA.
    """,
    'description': """
        Additional fields for hr.employee model. This is only customized to SEGASA.
        
        Developers:
         * Daniel Eduardo Diaz Mateo
    """,
    'author': 'ISJO TECHNOLOGY, SRL',
    'license': 'LGPL-3',
    'website': 'https://www.isjo-technology.com',
    'category': 'Human Resources',
    'depends': [
        'base',
        'hr',
        'hr_contract',
        'hr_payroll',
        # 'payroll_batch_report',
        # 'payroll_report',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_region_data.xml',
        'data/hr_structure_class_data.xml',
        # 'templates/payroll_batch_report.xml',
        # 'templates/payroll_report.xml',
        'views/contract_views.xml',
        'views/employee_views.xml',
        'wizard/hr_payroll_payslips_by_employees_extend_views.xml',
        'views/view_hr_structure_class_form.xml',
        'views/view_hr_zone_form.xml',
        'views/view_hr_region_form.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}

