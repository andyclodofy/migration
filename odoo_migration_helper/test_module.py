#!/usr/bin/env python3
"""
Script para probar que el módulo migration.helper está instalado y funciona
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from odoo_xmlrpc import OdooXMLRPC


def test_migration_helper():
    """
    Prueba el módulo migration.helper
    """
    print("=" * 70)
    print("PRUEBA DEL MÓDULO MIGRATION.HELPER")
    print("=" * 70)
    
    # Conectar a v18
    odoo = OdooXMLRPC('http://localhost:8069', 'd101', 'admin', 'admin')
    odoo.connect()
    
    print("\n✓ Conectado a Odoo v18")
    
    # Probar el método test_connection
    print("\n" + "=" * 70)
    print("1. Probando test_connection()")
    print("=" * 70)
    try:
        result = odoo.execute('migration.helper', 'test_connection')
        print(f"✓ Resultado: {result}")
        
        if result.get('status') == 'ok':
            print("✅ El módulo está instalado y funciona correctamente")
        else:
            print("⚠️  El módulo respondió pero con estado inesperado")
    except Exception as e:
        print(f"❌ Error: {str(e)[:300]}")
        print("\n⚠️  El módulo NO está instalado o no es accesible")
        print("\nPara instalar el módulo:")
        print("1. Copiar la carpeta odoo_migration_helper/ a /path/to/odoo/addons/")
        print("2. Actualizar lista de módulos en Odoo")
        print("3. Instalar el módulo 'Migration Helper - Invoice Creation via XML-RPC'")
        return False
    
    # Probar crear una factura de prueba
    print("\n" + "=" * 70)
    print("2. Probando create_invoice_xmlrpc()")
    print("=" * 70)
    
    invoice_vals = {
        'move_type': 'out_invoice',
        'partner_id': 1,
        'invoice_date': '2026-01-29',
        'company_id': 1,
        'invoice_line_ids': [(0, 0, {
            'name': 'Test Product - Migration Helper',
            'quantity': 1.0,
            'price_unit': 100.0,
        })],
    }
    
    print(f"Valores de prueba: {invoice_vals}")
    
    try:
        invoice_id = odoo.execute('migration.helper', 'create_invoice_xmlrpc', invoice_vals)
        print(f"\n✓ Factura creada con ID: {invoice_id}")
        print(f"  Tipo: {type(invoice_id)}")
        
        # Leer la factura creada
        invoice = odoo.read('account.move', [invoice_id], ['name', 'state', 'amount_total', 'partner_id'])
        print(f"\n📄 Datos de la factura:")
        print(f"  Número: {invoice[0].get('name')}")
        print(f"  Estado: {invoice[0].get('state')}")
        print(f"  Total: {invoice[0].get('amount_total')}")
        print(f"  Cliente: {invoice[0].get('partner_id')}")
        
        # Eliminar la factura de prueba
        odoo.unlink('account.move', [invoice_id])
        print(f"\n✓ Factura de prueba eliminada")
        
        print("\n✅ El módulo funciona correctamente para crear facturas via XML-RPC!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error al crear factura: {str(e)[:500]}")
        return False


if __name__ == '__main__':
    success = test_migration_helper()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ TODAS LAS PRUEBAS PASARON")
        print("=" * 70)
        print("\nEl módulo está listo para usar en la migración de facturas.")
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("❌ LAS PRUEBAS FALLARON")
        print("=" * 70)
        print("\nPor favor instala el módulo antes de continuar.")
        sys.exit(1)
