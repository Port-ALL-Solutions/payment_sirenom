# -*- coding: utf-8 -*-

{
    'name': 'Moneris Payment',
    'category': 'Hidden',
    'summary': 'Payment Acquirer Moneris',
    'version': '1.0',
    'description': """Moneris Payment Acquirer""",
    'author': 'a.drozdyuk',
    'depends': ['payment', 'website_sale'],
    'data': [
        'views/moneris.xml',
        'views/payment_acquirer.xml',
        'views/res_config_view.xml',
        'data/moneris.xml',
        'views/payment_invoice.xml',
        'views/website_template.xml',
    ],
    'installable': True,
}
