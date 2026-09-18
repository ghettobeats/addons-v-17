# Copyright 2018,2021 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# Copyright 2024 Daniel Eduardo Diaz Mateo <https://isjo-technology.com/>
# License MIT (https://opensource.org/licenses/MIT).
{
    "name": "Control access to Apps",
    "summary": "Configure administrators who don't have access to Apps",
    "category": "Extra Tools",
    "version": "17.0.1.0.0",
    "application": False,
    "author": "ISJO TECHNOLOGY, SRL. Daniel Eduardo Diaz Mateo",
    "support": "daniel.diaz@isjo-technology.com",
    "website": "https://isjo-technology.com/",
    "license": "Other OSI approved licence",  # MIT
    "depends": ["ir_rule_protected"],
    "external_dependencies": {"python": [], "bin": []},
    "data": [
        "security/access_apps_security.xml",
        "security/ir.model.access.csv"
    ],
    "demo": [],
    "qweb": [],
    "post_load": None,
    "pre_init_hook": None,
    "post_init_hook": None,
    "uninstall_hook": "uninstall_hook",
    "assets": {},  # Odoo 17 introduces a new way to handle assets
    "auto_install": False,
    "installable": True,
}
