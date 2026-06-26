# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        # Close the transit loop, but never let tracking break the receipt.
        try:
            moves._sync_purchase_transit_received()
        except Exception:  # noqa: BLE001 - tracking must not block receipt
            _logger.exception(
                "purchase_transit: failed to sync actual_received for moves %s",
                moves.ids)
        return moves

    def _sync_purchase_transit_received(self):
        """Fill the 'received' milestone from the real incoming move date."""
        Transit = self.env['purchase.transit'].sudo()
        for move in self:
            line = move.purchase_line_id
            if not line or move.state != 'done':
                continue
            if move.location_dest_id.usage != 'internal':
                continue
            transit = Transit.search(
                [('purchase_line_id', '=', line.id)], limit=1)
            if not transit:
                continue
            done_date = fields.Date.to_date(move.date) or fields.Date.context_today(move)
            if not transit.actual_received or transit.actual_received < done_date:
                transit.actual_received = done_date
