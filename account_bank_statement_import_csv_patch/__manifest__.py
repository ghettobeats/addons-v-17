{
    "name": "Bank Statement Import CSV Patch",
    "summary": """
    Skip account_bank_statement_import_csv csv check
        """,
    "author": "Indexa",
    "website": "https://www.indexa.do",
    "category": "Accounting",
    "license": "LGPL-3",
    "version": "15.0.1.0.0",
    "depends": ["account_bank_statement_import", "account_bank_statement_import_csv"],
    "data": [
            "views/res_company_views.xml",
    ],
    "installable": True,
    "auto_install": True,
}
