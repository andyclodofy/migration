# -*- coding: utf-8 -*-

from odoo import models, api


class MigrationHelper(models.AbstractModel):
    """
    Helper model to provide XML-RPC compatible methods for invoice creation.
    
    This module is specifically designed to help with migration from Odoo v13 to v18.
    In v18, account.move.create() uses @api.model_create_multi which changes the
    method signature and makes it incompatible with XML-RPC calls.
    
    This helper provides simple wrapper methods that can be called via XML-RPC.
    """
    _name = 'migration.helper'
    _description = 'Migration Helper for XML-RPC Invoice Creation'

    @api.model
    def create_invoice_xmlrpc(self, vals):
        """
        Create a single invoice via XML-RPC.
        
        This method is a wrapper around account.move.create() that is compatible
        with XML-RPC calls. It accepts a single dictionary of values and returns
        the integer ID of the created invoice.
        
        Args:
            vals (dict): Dictionary with invoice values. Should include:
                - move_type: Type of invoice ('out_invoice', 'in_invoice', etc.)
                - partner_id: Customer/Supplier ID
                - invoice_date: Invoice date
                - company_id: Company ID
                - journal_id: Journal ID (optional, will use default if not provided)
                - invoice_line_ids: List of invoice lines in format [(0, 0, {...})]
                
        Returns:
            int: ID of the created invoice
            
        Example usage via XML-RPC:
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': 1,
                'invoice_date': '2026-01-28',
                'company_id': 1,
                'invoice_line_ids': [(0, 0, {
                    'product_id': 1,
                    'quantity': 1,
                    'price_unit': 100.0,
                    'name': 'Product Name',
                    'tax_ids': [(6, 0, [1, 2])],
                })],
            }
            
            invoice_id = models.execute_kw(
                db, uid, password,
                'migration.helper', 'create_invoice_xmlrpc',
                [invoice_vals], {}
            )
        """
        # Ensure we're working with a single dictionary
        if not isinstance(vals, dict):
            raise ValueError("vals must be a dictionary")
        
        # Create the invoice using the standard ORM method
        # account.move.create() expects a list of dicts (vals_list)
        invoice = self.env['account.move'].create([vals])
        
        # Return the integer ID (not the recordset)
        return invoice.id

    @api.model
    def create_invoices_xmlrpc(self, vals_list):
        """
        Create multiple invoices via XML-RPC.
        
        This method accepts a list of dictionaries and creates multiple invoices
        in a single call. More efficient than calling create_invoice_xmlrpc multiple times.
        
        Args:
            vals_list (list): List of dictionaries with invoice values
            
        Returns:
            list: List of IDs of the created invoices
        """
        # Ensure we're working with a list
        if not isinstance(vals_list, list):
            raise ValueError("vals_list must be a list of dictionaries")
        
        # Create the invoices
        invoices = self.env['account.move'].create(vals_list)
        
        # Return the list of IDs
        return invoices.ids

    @api.model
    def test_connection(self):
        """
        Simple test method to verify the module is installed and accessible.
        
        Returns:
            dict: Status information
        """
        return {
            'status': 'ok',
            'message': 'Migration Helper module is installed and ready',
            'model': 'migration.helper',
        }
