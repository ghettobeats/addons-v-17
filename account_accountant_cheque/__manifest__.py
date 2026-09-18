{
    "name": "Accountant Cheque Management",
    "summary": """
        Integrates Cheque Management into Accounting
    """,
    "description": """
        Updates Odoo Cheque Management functinalities to properly work
        with Account Accountant module.
    """,
    "author": "Indexa",
    "website": "https://indexa.do/",
    "category": "Accounting/Accounting",
    "version": "15.0.0.0.0",
    "depends": ["account_accountant", "odoo_cheque_management"],
    "data": ["data/account_accountant_data.xml"],
    "installable": True,
    "auto_install": True,
    "uninstall_hook": "uninstall_hook",
}
