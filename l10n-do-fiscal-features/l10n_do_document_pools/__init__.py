from . import models
from . import wizard

import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """
    Fill l10n_do_journal_document_type_id field on all existing fiscal invoices
    """

    env = api.Environment(cr, SUPERUSER_ID, {})
    env.cr.execute(
        """
        SELECT id, journal_id, l10n_latam_document_type_id
        FROM account_move move
        JOIN res_company company
        ON (move.company_id = company.id)
        JOIN res_partner partner
        ON (company.partner_id = partner.id)
        JOIN res_country country
        ON (partner.country_id = country.id)
        WHERE move.move_type != 'entry'
        AND country.code = 'DO'
        AND move.l10n_latam_document_type_id IS NOT NULL
        AND move.l10n_do_journal_document_type_id IS NULL;
        """
    )

    _logger.info(
        "Starting account_move l10n_do_journal_document_type_id field migration"
    )
    for move, journal, doc_type_id in env.cr.fetchall():
        env.cr.execute(
            """
            UPDATE account_move
            SET l10n_do_journal_document_type_id = doc_type.id
            FROM (
                SELECT id
                FROM l10n_do_account_journal_document_type doc_type
                WHERE journal_id = %s
                AND l10n_latam_document_type_id = %s
            ) AS doc_type
            WHERE account_move.id = move;
            """
            % (journal, doc_type_id)
        )
    _logger.info("Finish account_move l10n_do_journal_document_type_id field migration")
