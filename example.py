"""
Ejemplo de uso de las conexiones a Odoo v13 y v18.

Autor: andyengit
Mantenedor: andyengit
"""
from connections import odoo_v13, odoo_v18, OdooClientReadOnlyError


def main():
    print("=" * 60)
    print("CONEXIÓN A ODOO V13 (Solo Lectura)")
    print("=" * 60)
    
    try:
        odoo_v13.authenticate()
        version_info = odoo_v13.version()
        print(f"Versión: {version_info.get('server_version', 'N/A')}")
        print(f"Cliente: {odoo_v13}")
        
        partners = odoo_v13.search_read(
            'res.partner',
            [('is_company', '=', True)],
            fields=['name', 'email', 'phone'],
            limit=5
        )
        print(f"\nEmpresas encontradas: {len(partners)}")
        for partner in partners:
            print(f"  - {partner['name']}")
        
        print("\nIntentando crear un registro (debería fallar)...")
        try:
            odoo_v13.create('res.partner', {'name': 'Test'})
        except OdooClientReadOnlyError as e:
            print(f"  ✓ Bloqueado correctamente: {e}")
            
    except Exception as e:
        print(f"Error conectando a Odoo v13: {e}")
    
    print("\n" + "=" * 60)
    print("CONEXIÓN A ODOO V18 (Lectura/Escritura)")
    print("=" * 60)
    
    try:
        odoo_v18.authenticate()
        version_info = odoo_v18.version()
        print(f"Versión: {version_info.get('server_version', 'N/A')}")
        print(f"Cliente: {odoo_v18}")
        
        partners = odoo_v18.search_read(
            'res.partner',
            [('is_company', '=', True)],
            fields=['name', 'email', 'phone'],
            limit=5
        )
        print(f"\nEmpresas encontradas: {len(partners)}")
        for partner in partners:
            print(f"  - {partner['name']}")
            
    except Exception as e:
        print(f"Error conectando a Odoo v18: {e}")


if __name__ == '__main__':
    main()
