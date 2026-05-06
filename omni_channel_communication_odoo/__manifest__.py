{
    "name": "Omnichannel Communication Odoo | Odoo WhatsApp, Facebook & Instagram Messenger Integration",
    "version": "18.1",
    "author": "TechUltra Solutions Private Limited",
    "category": "Marketing",
    "live_test_url": "https://www.youtube.com/playlist?list=PL8o8i9mlxsWiGhybME4miEeftUCcTLNoj",
    "company": "TechUltra Solutions Private Limited",
    "website": "https://www.techultrasolutions.com/",
    "summary": """OmniChat Suit | OmniConnect Suite | Multichannel | Unified Messaging Suite | Cross-Platform Communication Toolkit | Bidirectional Conversation with Official Cloud/Graph API by Meta
                  Odoo WhatsApp Integration | Odoo Facebook Messenger Integration | Odoo Instagram Messaging Integration""",
    "description": """
        Omni Channel Communication Odoo Community
        Omni Channel Communication Odoo
        Omni Channel Communication
        OmniChat Suit
        OmniConnect Suite 
        Multichannel 
        Unified Messaging Suite
        Cross-Platform Communication Toolkit
        Bidirectional Conversation with Official Cloud/Graph API by Meta
        Odoo WhatsApp Integration
        Odoo Facebook Messenger Integration
        Odoo Instagram Messaging Integration 
        Odoo V12 to V16 (Both Community and Enterprise Editions)
        Odoo V17 to V18 (Only in Community Version)
        Odoo 
        Odoo Community
        WhatsApp Base
        WhatsApp Discuss
        Odoo Facebook Instagram Messenger
        Odoo ERP
        V18 WhatsApp
        Odoo WhatsApp
        Odoo Facebook
        Odoo Instagram
        Meta
        Facebook
        Integration
        Cloud API
        WhatsApp Cloud API
        Community
    """,
    "depends": ['base', 'mail', 'mail_group', 'base_automation'],
    "data": [
        # tus_meta_whatsapp_base
        'tus_meta_whatsapp_base/security/whatsapp_security.xml',
        'tus_meta_whatsapp_base/security/ir.model.access.csv',
        'tus_meta_whatsapp_base/data/cron.xml',
        'tus_meta_whatsapp_base/data/wa_template.xml',
        'tus_meta_whatsapp_base/wizard/wa_compose_message_view.xml',
        'tus_meta_whatsapp_base/views/provider_base.xml',
        'tus_meta_whatsapp_base/views/res_users.xml',
        'tus_meta_whatsapp_base/views/channel_provider_line.xml',
        'tus_meta_whatsapp_base/views/res_partner.xml',
        'tus_meta_whatsapp_base/views/whatsapp_history.xml',
        'tus_meta_whatsapp_base/views/wa_template.xml',
        'tus_meta_whatsapp_base/views/variables.xml',
        'tus_meta_whatsapp_base/views/components.xml',
        'tus_meta_whatsapp_base/views/mail_channel.xml',
        'tus_meta_whatsapp_base/views/mail_message.xml',
        'tus_meta_whatsapp_base/views/provider_meta.xml',
        'tus_meta_whatsapp_base/views/ir_actions.xml',
        'tus_meta_whatsapp_base/views/interactive_list_views.xml',
        'tus_meta_whatsapp_base/views/interactive_product_list_views.xml',
        'tus_meta_whatsapp_base/views/wa_button_component_views.xml',
        'tus_meta_whatsapp_base/views/wa_carousel_component_view.xml',

        # tus_meta_wa_discuss
        'tus_meta_wa_discuss/views/res_config_settings_views.xml',

        # odoo_facebook_instagram_messenger
        "odoo_facebook_instagram_messenger/security/ir.model.access.csv",
        "odoo_facebook_instagram_messenger/wizard/messenger_compose_message_view.xml",
        "odoo_facebook_instagram_messenger/wizard/instagram_compose_message_view.xml",
        "odoo_facebook_instagram_messenger/views/mail_channel.xml",
        "odoo_facebook_instagram_messenger/views/messenger_provider_base.xml",
        "odoo_facebook_instagram_messenger/views/messenger_history_views.xml",
        "odoo_facebook_instagram_messenger/views/instagram_history_views.xml",
        "odoo_facebook_instagram_messenger/views/messenger_channel_provider_line_views.xml",
        "odoo_facebook_instagram_messenger/views/res_partner_views_inherit.xml",
        "odoo_facebook_instagram_messenger/views/res_users_inherit.xml",
        "odoo_facebook_instagram_messenger/views/messenger_template_views.xml",
        "odoo_facebook_instagram_messenger/views/template_buttons_views.xml",
        "odoo_facebook_instagram_messenger/views/template_components_views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            # tus_meta_whatsapp_base
            'omni_channel_communication_odoo/static/tus_meta_whatsapp_base/static/src/css/style.css',
            'omni_channel_communication_odoo/static/tus_meta_whatsapp_base/static/src/scss/kanban_view.scss',

            #tus_meta_wa_discuss
            'omni_channel_communication_odoo/static/tus_meta_wa_discuss/static/src/xml/message.xml',
            'omni_channel_communication_odoo/static/tus_meta_wa_discuss/static/src/xml/AgentsList.xml',
            # 'omni_channel_communication_odoo/static/tus_meta_wa_discuss/static/src/xml/channel_load.xml',
            'omni_channel_communication_odoo/static/tus_meta_wa_discuss/static/src/js/common/**/*',
            'omni_channel_communication_odoo/static/tus_meta_wa_discuss/static/src/js/agents/**/*',
            'omni_channel_communication_odoo/static/tus_meta_wa_discuss/static/src/scss/*.scss',
            'omni_channel_communication_odoo/static/tus_meta_wa_discuss/static/src/js/templates/**/*',
            'omni_channel_communication_odoo/static/tus_meta_wa_discuss/static/src/core/common/**/*',
            'omni_channel_communication_odoo/static/tus_meta_wa_discuss/static/src/core/web/**/*',

            #odoo_facebook_instagram_messenger
            # "omni_channel_communication_odoo/static/odoo_facebook_instagram_messenger/static/src/xml/AgentsList.xml",
            "omni_channel_communication_odoo/static/odoo_facebook_instagram_messenger/static/src/js/common/**/*",
        ],
    },
    "price": 219,
    "currency": "USD",
    "installable": True,
    "auto_install": False,
    "license": "OPL-1",
    "images": ["static/description/banner.gif"],
}
