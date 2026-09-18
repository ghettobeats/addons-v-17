{
    "name": "Dominican Withholding Certification",
    "summary": """
        Generate Withholding Certifications from payments""",
    "author": "Indexa",
    "website": "https://www.indexa.do",
    "category": "Accounting",
    "version": "15.0.1.0.0",
    "depends": ["l10n_do_accounting"],
    "data": [
        "security/ir.model.access.csv",
        "data/res_company_data.xml",
        "views/account_views.xml",
        "views/res_config_setting_views.xml",
        "views/withholding_cert_templates.xml",
        "views/report_withholding_cert.xml",
        "views/withholding_cert_report.xml",
        "wizard/layout_setup_wizard_views.xml",
    ],
    "installable": True,
}
