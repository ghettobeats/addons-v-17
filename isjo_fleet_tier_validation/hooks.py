# -*- coding: utf-8 -*-
# © 2026 ISJO TECHNOLOGY, SRL (Daniel Diaz <daniel.diaz@isjo-technology.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


def post_init_hook(env):
    env.cr.execute(
        "UPDATE fleet_vehicle SET movement_state = 'draft' WHERE movement_state IS NULL"
    )
