# -*- coding: utf-8 -*-
{
    'name': 'Migration Helper - Invoice Creation via XML-RPC',
    'version': '18.0.1.0.0',
    'category': 'Technical',
    'summary': 'Helper module to create invoices via XML-RPC for migration from v13 to v18',
    'description': """
Migration Helper
================

This module provides XML-RPC compatible methods to create invoices.

In Odoo v18, the account.move.create() method uses @api.model_create_multi
which is not directly compatible with XML-RPC calls. This module provides
a simple wrapper method that can be called via XML-RPC.

Features:
---------
* create_invoice_xmlrpc: Creates a single invoice and returns its ID
* Fully compatible with XML-RPC
* Handles invoice lines and taxes
* Returns integer ID (not recordset)

Usage via XML-RPC:
------------------
invoice_id = models.execute_kw(
    db, uid, password,
    'migration.helper', 'create_invoice_xmlrpc',
    [invoice_vals], {}
)

Author: andyengit
    """,
    'author': 'andyengit',
    'maintainer': 'andyengit',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
