# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # Default unset = False = hidden; tick to show.
    yx_show_discuss = fields.Boolean(
        string="显示讨论应用",
        config_parameter="yixin_branding.show_discuss")
    yx_show_apps_menu = fields.Boolean(
        string="显示应用(模块管理)菜单",
        config_parameter="yixin_branding.show_apps_menu")
    yx_show_notification = fields.Boolean(
        string="显示顶部通知",
        config_parameter="yixin_branding.show_notification")

    def set_values(self):
        super().set_values()
        get = self.env["ir.config_parameter"].sudo().get_param

        def truthy(key):
            return get(key) in ("True", "true", "1")

        # Discuss / Apps visibility = menu activation (notification is handled
        # client-side via session_info + the systray JS).
        discuss = self.env.ref("mail.menu_root_discuss", raise_if_not_found=False)
        if discuss:
            discuss.sudo().active = truthy("yixin_branding.show_discuss")
        apps = self.env.ref("base.menu_management", raise_if_not_found=False)
        if apps:
            apps.sudo().active = truthy("yixin_branding.show_apps_menu")
