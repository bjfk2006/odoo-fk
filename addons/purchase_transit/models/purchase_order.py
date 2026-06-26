# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    transit_ids = fields.One2many(
        'purchase.transit', 'order_id', string='Transit Tracking')
    transit_count = fields.Integer(
        string='Transit Count', compute='_compute_transit_count')

    @api.depends('transit_ids')
    def _compute_transit_count(self):
        for order in self:
            order.transit_count = len(order.transit_ids)

    def button_confirm(self):
        res = super().button_confirm()
        auto = self.env['ir.config_parameter'].sudo().get_param(
            'purchase_transit.auto_generate_on_confirm')
        if auto in ('True', 'true', '1'):
            self.action_generate_transit()
        return res

    def action_generate_transit(self):
        """Create one transit record per order line that lacks one (idempotent)."""
        Transit = self.env['purchase.transit']
        lines = self.order_line.filtered(
            lambda l: not l.display_type and l.product_id)
        existing = Transit.search([
            ('purchase_line_id', 'in', lines.ids)]).purchase_line_id
        to_create = lines - existing
        if to_create:
            Transit.create([
                {'purchase_line_id': line.id} for line in to_create])
        return self.action_view_transit()

    def action_view_transit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transit Tracking'),
            'res_model': 'purchase.transit',
            'view_mode': 'list,kanban,form',
            'domain': [('order_id', '=', self.id)],
            'context': {'default_purchase_line_id': False},
        }
