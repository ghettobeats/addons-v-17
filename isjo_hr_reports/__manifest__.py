# -*- coding: utf-8 -*-
#################################################################################
# Author      : Daniel Diaz ISJO Technology. (<https://isjo-technology.com/>)
# All Rights Reserved.
#################################################################################
{
    'name': 'Reportes de Recursos Humanos',
    'version': '17.0.1.0',
    'category': 'Human Resources',
    'summary': 'Reportes operativos de RR.HH.: oficiales activos, rotación, desvinculados y vacantes',
    'author': 'ISJO TECHNOLOGY, SRL',
    'website': 'https://isjo-technology.com',
    'license': 'AGPL-3',
    'copyright': '2026 Daniel Diaz <daniel.diaz@isjo-technology.com>',
    'depends': [
        'base',
        'hr',
        'hr_contract',
        'hr_recruitment',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_reports_menu.xml',
        'views/active_officers_report_view.xml',
        'views/staff_rotation_report_view.xml',
        'views/terminated_officers_report_view.xml',
        # 'views/vacancies_report_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
