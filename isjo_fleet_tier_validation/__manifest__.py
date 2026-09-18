# -*- coding: utf-8 -*-
# © 2026 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Fleet Tier Validation",
    'summary': "Validacion por niveles para asignacion y descarga de vehiculos.",
    'description': """
        Extiende fleet.vehicle con un flujo de aprobacion por niveles (tier validation)
        para los movimientos de asignacion y descarga de vehiculos institucionales.

        Desarrolladores:
         * Daniel Eduardo Diaz Mateo
    """,
    'version': '17.0.1.1.0',
    'maintainers': ['Daniel Diaz'],
    'category': 'Fleet',
    'website': 'https://www.isjo-technology.com/',
    'author': 'ISJO Technology SRL',
    'license': 'AGPL-3',
    'application': False,
    'installable': True,
    'post_init_hook': 'post_init_hook',
    'depends': [
        'base_tier_validation',
        'fleet',
        'mitur_fleet_extension',
    ],
    'data': [
        'security/groups.xml',
        'wizard/fleet_approval_wizard_view.xml',
        'views/fleet_movement_history_view.xml',
        'views/fleet_vehicle_view_inherit.xml',
        'security/ir.model.access.csv',
    ],
}
