from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    cr.execute(
        "UPDATE fleet_vehicle SET movement_state = 'draft' WHERE movement_state IS NULL"
    )
