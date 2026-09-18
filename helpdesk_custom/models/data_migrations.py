from odoo import fields, models, api, _


class DataMigration(models.Model):
    _name = 'data.migration'
    _description = 'Data Migration from Studio fields'

    @api.model
    def migrate_studio_data(self):
        # Definición de los modelos y los mapeos de campos
        model_field_mappings = {
            'helpdesk.ticket': {
                'x_studio_fecha_oficio': 'official_document_date',
                'x_studio_many2one_field_l6kci': 'requesting_area',
                'x_studio_beneficiario_2': 'beneficiary',
                'x_falta_firma': 'signature_missing',
                'x_factura_relacionadas': 'related_invoices',
                'x_pagos_relacionados': 'related_payments',
            },
            'helpdesk.stages.log': {
                'x_stage_id': 'stage_id',
                'create_id': 'write_uid',
                'x_user_id': 'assign_user',
                'x_signature': 'signature',
                'x_fecha_hora_inicio': 'stage_start_date',
                'x_fecha_hora_final': 'stage_end_date',
            },
            # Agrega más modelos y mapeos aquí según sea necesario
        }

        # Iterar sobre cada modelo y sus mapeos de campos
        for model_name, field_mapping in model_field_mappings.items():
            source_model = self.env[model_name]
            records = source_model.search([])  # Obtener todos los registros del modelo

            for record in records:
                updates = {}
                for source_field, target_field in field_mapping.items():
                    if hasattr(record, source_field):
                        # Leer el valor del campo fuente
                        value = getattr(record, source_field)
                        updates[target_field] = value
                if updates:
                    # Actualizar los campos destino
                    record.write(updates)

        return _('Data migration completed.')
