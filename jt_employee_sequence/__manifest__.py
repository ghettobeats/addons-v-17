# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Employee Sequence Id For Odoo 17',
    'summary': 'Generate employee sequence id',
    'version': '17.0.0.1.0',
    'author': 'ISJO TECHNOLOGY, SRL',
    'maintainer': 'ISJO TECHNOLOGY, SRL By DANIEL EDUARDO DIAZ MATEO',
    'contributors':['Daniel Eduardo Diaz Mateo <daniel.diaz@isjo-technology.com>'],
    'website': 'https://www.isjo-technology.com',
    'depends': [
        'hr',
        'base',
        'hr_payroll'
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/emp_view.xml',
        'views/emp_sequence_view.xml'
    ],
    'application': False,
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'images': ['static/description/poster_image.png'],
}
