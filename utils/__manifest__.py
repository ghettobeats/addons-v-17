# -*- coding: utf-8 -*-
# © 2024 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': "Utils for Odoo 17",
    'summary': "Utility module for common functionalities.",
    'description': """
            This module provides utility functions for reports, paper formatting, and JavaScript utilities.
    """,
    'version': '17.0.0.1.0',
    'author': 'ISJO TECHNOLOGY, SRL',
    'maintainer': 'ISJO TECHNOLOGY, SRL By DANIEL EDUARDO DIAZ MATEO',
    'contributors':['Daniel Eduardo Diaz Mateo <daniel.diaz@isjo-technology.com>'],
    'website': 'https://www.isjo-technology.com',
    'category': 'Tools',
    'depends': ['base'],
    'data': [
        # Comment out these lines if the files don't exist
        'views/report_paperformat.xml',
        'views/report_templates.xml',
    ],
    'application': False,
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'images': ['static/description/poster_image.png'],
    ########################################################################################

}

