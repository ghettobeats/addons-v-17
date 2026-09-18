from odoo import fields
stmt_lines = [
    {
        "payment_ref": "Interes Credito",
        "date": fields.Date.from_string("2021-12-31"),
        "amount": 11884.34,
    },
    {
        "payment_ref": "Retencion Imp. x Int. Pagados",
        "date": fields.Date.from_string("2021-12-31"),
        "amount": -118.84,
    },
]
