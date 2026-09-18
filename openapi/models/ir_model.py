# Copyright 2018 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
import itertools
import logging
import re
import psycopg2
from ast import literal_eval
from collections import defaultdict
from collections.abc import Mapping
from operator import itemgetter

from psycopg2 import sql

from odoo import api, fields, models, tools, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression
from odoo.tools import pycompat, unique
from odoo.tools.safe_eval import safe_eval, datetime, dateutil, time

class IrModelFields(models.Model):
    _inherit = "ir.model.fields"

    override_readonly = fields.Boolean('Crear aun con readonly?', store=True)

    def write(self, vals):
        # if set, *one* column can be renamed here
        column_rename = None

        # names of the models to patch
        patched_models = set()


        override = False if 'override_readonly' not in vals else True

        if vals and self:
            for item in self:
                if item.state != 'manual' and override == False:

                    raise UserError(_('Properties of base fields cannot be altered in this manner! '
                                      'Please modify them through Python code, '
                                      'preferably through a custom addon!'))

                if vals.get('model_id', item.model_id.id) != item.model_id.id:
                    raise UserError(_("Changing the model of a field is forbidden!"))

                if vals.get('ttype', item.ttype) != item.ttype:
                    raise UserError(_("Changing the type of a field is not yet supported. "
                                      "Please drop it and create it again!"))

                obj = self.pool.get(item.model)
                field = getattr(obj, '_fields', {}).get(item.name)

                if vals.get('name', item.name) != item.name:
                    # We need to rename the field
                    item._prepare_update()
                    if item.ttype in ('one2many', 'many2many', 'binary'):
                        # those field names are not explicit in the database!
                        pass
                    else:
                        if column_rename:
                            raise UserError(_('Can only rename one field at a time!'))
                        column_rename = (obj._table, item.name, vals['name'], item.index, item.store)

                # We don't check the 'state', because it might come from the context
                # (thus be set for multiple fields) and will be ignored anyway.
                if obj is not None and field is not None:
                    patched_models.add(obj._name)

        # These shall never be written (modified)
        for column_name in ('model_id', 'model', 'state'):
            if column_name in vals:
                del vals[column_name]

        res = super(IrModelFields, self).write(vals)

        self.flush()
        self.clear_caches()                         # for _existing_field_data()

        if column_rename:
            # rename column in database, and its corresponding index if present
            table, oldname, newname, index, stored = column_rename
            if stored:
                self._cr.execute(
                    sql.SQL('ALTER TABLE {} RENAME COLUMN {} TO {}').format(
                        sql.Identifier(table),
                        sql.Identifier(oldname),
                        sql.Identifier(newname)
                    ))
                if index:
                    self._cr.execute(
                        sql.SQL('ALTER INDEX {} RENAME TO {}').format(
                            sql.Identifier(f'{table}_{oldname}_index'),
                            sql.Identifier(f'{table}_{newname}_index'),
                        ))

        if column_rename or patched_models:
            # setup models, this will reload all manual fields in registry
            self.flush()
            self.pool.setup_models(self._cr)

        if patched_models:
            # update the database schema of the models to patch
            models = self.pool.descendants(patched_models, '_inherits')
            self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))

        return res

class IrModel(models.Model):
    _inherit = "ir.model"

    api_access_ids = fields.One2many("openapi.access", "model_id", "Access via API")
    api_accesses_count = fields.Integer(
        compute="_compute_related_accesses_count",
        string="Related openapi accesses count",
        store=False,
    )


    def _compute_related_accesses_count(self):
        for record in self:
            record.api_accesses_count = len(record.api_access_ids)
