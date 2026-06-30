# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    transit_auto_generate_on_confirm = fields.Boolean(
        string='Auto-create transit tracking on PO confirmation',
        config_parameter='purchase_transit.auto_generate_on_confirm')
