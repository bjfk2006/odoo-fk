# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo.tools import file_open

LOGO_PATH = 'yixin_branding/static/src/img/yx-logo-blue.png'


def post_init_hook(env):
    """Set the Yixin logo on every company when the module is installed."""
    with file_open(LOGO_PATH, 'rb') as f:
        logo = base64.b64encode(f.read())
    env['res.company'].search([]).write({'logo': logo})
