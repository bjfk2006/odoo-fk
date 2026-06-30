# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Yixin Branding',
    'version': '1.0',
    'category': 'Tools',
    'summary': 'Replace the Odoo company logo and backend favicon with the '
               'Yixin Construction brand (light-blue cube).',
    'depends': ['web', 'mail'],
    'data': [
        'views/webclient_templates.xml',
        'views/res_config_settings_views.xml',
        'views/change_password_views.xml',
        'data/hide_discuss.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'yixin_branding/static/src/css/yixin_theme.css',
            'yixin_branding/static/src/js/yx_systray.js',
        ],
    },
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
