# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    transit_ids = fields.One2many(
        'purchase.transit', 'purchase_line_id', string='Transit Tracking')
