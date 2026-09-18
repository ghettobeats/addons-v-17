# -*- coding: utf-8 -*-
#################################################################################
# Author      : Daniel Diaz ISJO Technology. (<https://isjo-technology.com/>)
# All Rights Reserved.
#################################################################################
{
    'name': "ISJO HR Payroll - Multi Currency",
    'summary': "Permite identificar la moneda de pago del empleado en el contrato (USD, EUR, etc.)",
    'description': """
        Agrega el campo 'Moneda de Pago' (currency_id) al contrato del empleado,
        para identificar en qué moneda se le paga (Peso Dominicano, Dólar, Euro, etc.).

        El campo 'Salario' (wage) siempre se expresa en Peso Dominicano (RD$),
        independientemente de la moneda de pago seleccionada en el contrato.

        Developers:
         * Daniel Eduardo Diaz Mateo
    """,
    'author': "ISJO Technology, SRL",
    'website': "http://www.isjo-technology.com",
    'category': 'Human Resources/Payroll',
    'version': '17.0.1.0',
    'license': 'AGPL-3',
    'depends': [
        'isjo_hr_payroll',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_contract_views.xml',
        'views/hr_payroll_currency_rate_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_payslip_run_views.xml',
    ],
    'installable': True,
    'auto_install': False,
}
# © 2026 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
