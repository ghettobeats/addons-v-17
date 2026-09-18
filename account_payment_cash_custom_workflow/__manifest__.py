# Copyright 2021-Present Indexa - Manuel Marquez <mmarquez@indexacorp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Custom Workflow in Payments of Cash Control",
    "category": "Accounting/Accounting",
    "version": "15.0.0.0.2",
    "depends": ["account"],
    "data": [
        "security/account_payment_cash_custom_workflow_security.xml",
        "views/account_journal_views.xml",
        "views/account_payment_views.xml",
    ],
    "installable": True,
}
