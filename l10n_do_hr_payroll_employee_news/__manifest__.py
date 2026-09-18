# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Dominican Republic - Payroll",

    'summary': """
        Creación de novedades de empleados. 
    """,

    'description': """
Este módulo tiene como objetivo crear el modulo de novedades para ejecutar la nómina en la República Dominicana.

    Crea un modelo de novedades y cargarlas de forma masiva.
    Developers:
         * Daniel Eduardo Diaz Mateo
    """,

    'author': "ISJO Technology, SRL",
    'website': "http://www.isjo-technology.com",
    'category': 'Human Resources/Payroll',
    'version': '17.0.1.0',
    'license': 'AGPL-3',
    'depends': [
        'base_setup',
        'hr_payroll',
        'isjo_hr_payroll',
        'employee_additional_fields_customized_to_segasa'
    ],
    'external_dependencies': {'python': ['pandas']},
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        # 'data/l10n_do_hr_payroll_data.xml',
        # 'data/nomina_regular.xml',
        # 'data/nomina_prestaciones.xml',
        # 'data/nomina_regalia.xml',
        # 'data/nomina_vacaciones.xml',
        # 'data/email_template.xml',
        # 'data/contact_action.xml',
        'data/emp_news_sequence_view.xml',
        'views/payslip_input_import_views.xml',
        'views/inherit_hr_payslip.xml',
        'views/inherit_hr_payslip_run.xml',
        'wizard/wizard_view.xml',
        # 'wizard/wizard_report_views.xml',
    ],
    'demo': [
        # Si tienes datos de demostración, descomenta la siguiente línea:
        # 'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': False,
}

