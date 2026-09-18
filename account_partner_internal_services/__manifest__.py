# Copyright 2020-Present Indexa - Manuel Marquez <mmarquez@indexacorp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Partner Internal Services",
    "summary": "Automate assignation of accounts for contacts of internal services.",
    "category": "Accounting/Accounting",
    "author": "Indexa Inc.",
    "website": "https://indexa.do/",
    "maintainers": ["mamcode"],
    "development_status": "Beta",
    "license": "AGPL-3",
    "version": "13.0.1.0.0",
    "depends": ["account_accountant", "sale", "stock_account"],
    "data": ["views/res_partner_views.xml", "views/product_category_views.xml"],
    "installable": False,
}
