# -*- coding: utf-8 -*-
{
    'name': 'Quick Search',
    'version': '18.0',
    'author': 'Odoo Hub',
    'summary': 'Open Odoo global search with a single click. quick search quicksearch global search universal search odoo search odoo global search odoo quick search command palette odoo command palette command search action search menu search search menu odoo open search open global search open command palette open search palette search shortcut shortcut search keyboard shortcut alternative ctrl k cmd k search button search icon search systray systray search top bar search header search navbar search navigation navigation tool navigation helper fast navigation instant navigation productivity productivity tool productivity addon odoo productivity workflow improvement workflow optimization user experience ux ui user interface odoo ui odoo ux frontend backend web client odoo web odoo backend odoo frontend odoo javascript odoo xml owl component odoo owl web assets odoo addon odoo module odoo app search panel search popup search overlay action launcher launcher menu app launcher quick action quick access one click search tap search tap to search mobile search tablet search ios odoo ios android odoo android desktop odoo touch friendly mobile friendly no keyboard shortcut mouse navigation click navigation lightweight addon fast addon minimal addon simple addon utility addon ui enhancement usability enhancement navigation improvement speed improvement efficiency tool developer tool technical addon system tray system systray icon based search discoverability tool search helper search assistant search opener open menu fast search entry point application search database navigation record navigation menu access command access productivity enhancement time saving addon',
    'category': 'Productivity',
    'description': """
        Quick Search adds a search icon to the Odoo top bar, allowing users to instantly open the global search (Command Palette) with a single click.
        This module is especially useful for mobile and tablet users where keyboard shortcuts like Ctrl+K or Cmd+K are not available.
        
        Key features:
        - One-click access to global search
        - Works on desktop, iOS, and Android
        - No configuration required
        - Lightweight and fast
        
        Improve navigation speed and user experience with Quick Search.
    """,
    'maintainer': 'Odoo Hub',
    'website': 'https://apps.odoo.com/apps/modules/browse?author=Odoo%20Hub',
    'depends': ['base', 'web'],
    'assets': {
        'web.assets_backend': [
            'oh_quick_search/static/src/**/*',
        ],
    },
    'images': ['static/description/banner.png'],
    'live_test_url': 'https://youtu.be/ufTjvsA48dM',
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
