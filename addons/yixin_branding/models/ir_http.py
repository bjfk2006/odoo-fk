# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        show = self.env["ir.config_parameter"].sudo().get_param(
            "yixin_branding.show_notification")
        result["yx_show_notification"] = show in ("True", "true", "1")
        return result
