"""
Crea mapeos automáticos de impuestos y diarios faltantes en v18.

Autor: andyengit
Mantenedor: andyengit
"""
import os
import json
from dotenv import load_dotenv
from connections import odoo_v13, odoo_v18

load_dotenv()

COMPANY_ID = int(os.getenv('COMPANY_ID', 1))
MAPPINGS_FILE = 'mappings.json'


def create_tax_mapping():
    """
    Crea mapeo automático de impuestos por porcentaje + tipo.
    Cuando hay múltiples opciones, elige el primero.
    """
    print("\n" + "=" * 70)
    print("CREANDO MAPEO DE IMPUESTOS")
    print("=" * 70)
    
    # Obtener impuestos de v13
    taxes_v13 = odoo_v13.search_read(
        'account.tax',
        [('company_id', '=', COMPANY_ID)],
        fields=['id', 'name', 'type_tax_use', 'amount']
    )
    
    # Obtener impuestos de v18
    taxes_v18 = odoo_v18.search_read(
        'account.tax',
        [('company_id', '=', COMPANY_ID)],
        fields=['id', 'name', 'type_tax_use', 'amount']
    )
    
    # Indexar v18 por (amount, type_tax_use)
    v18_by_amount_type = {}
    for tax in taxes_v18:
        key = (tax['amount'], tax['type_tax_use'])
        if key not in v18_by_amount_type:
            v18_by_amount_type[key] = []
        v18_by_amount_type[key].append(tax)
    
    tax_mapping = {}
    not_found = []
    
    for tax in taxes_v13:
        key = (tax['amount'], tax['type_tax_use'])
        v18_options = v18_by_amount_type.get(key, [])
        
        if v18_options:
            # Tomar el primero disponible
            v18_tax = v18_options[0]
            tax_mapping[tax['id']] = {
                'v13_id': tax['id'],
                'v18_id': v18_tax['id'],
                'v13_name': tax['name'],
                'v18_name': v18_tax['name'],
                'amount': tax['amount'],
                'type': tax['type_tax_use']
            }
        else:
            not_found.append(tax)
    
    print(f"\n✓ Impuestos mapeados: {len(tax_mapping)}")
    print(f"✗ Sin mapeo: {len(not_found)}")
    
    if not_found:
        print("\nImpuestos sin equivalente en v18:")
        for tax in not_found:
            print(f"  - [{tax['id']}] {tax['name']} ({tax['type_tax_use']}, {tax['amount']}%)")
    
    return tax_mapping


def create_account_mapping():
    """Crea mapeo de cuentas contables por código."""
    print("\n" + "=" * 70)
    print("CREANDO MAPEO DE CUENTAS CONTABLES")
    print("=" * 70)
    
    accounts_v13 = odoo_v13.search_read(
        'account.account',
        [('company_id', '=', COMPANY_ID)],
        fields=['id', 'code', 'name']
    )
    
    accounts_v18 = odoo_v18.search_read(
        'account.account',
        [],
        fields=['id', 'code', 'name']
    )
    
    v18_by_code = {a['code']: a for a in accounts_v18}
    
    account_mapping = {}
    not_found = []
    
    for acc in accounts_v13:
        v18_acc = v18_by_code.get(acc['code'])
        if v18_acc:
            account_mapping[acc['id']] = {
                'v13_id': acc['id'],
                'v18_id': v18_acc['id'],
                'code': acc['code'],
                'name': acc['name']
            }
        else:
            not_found.append(acc)
    
    print(f"\n✓ Cuentas mapeadas: {len(account_mapping)}")
    print(f"✗ Sin mapeo: {len(not_found)}")
    
    if not_found:
        print("\nCuentas sin equivalente:")
        for acc in not_found:
            print(f"  - [{acc['id']}] {acc['code']} - {acc['name']}")
    
    return account_mapping, not_found


def create_missing_journals():
    """Crea los diarios faltantes en v18."""
    print("\n" + "=" * 70)
    print("CREANDO DIARIOS FALTANTES EN V18")
    print("=" * 70)
    
    # Obtener diarios de v13
    journals_v13 = odoo_v13.search_read(
        'account.journal',
        [('company_id', '=', COMPANY_ID)],
        fields=['id', 'code', 'name', 'type', 'currency_id']
    )
    
    # Obtener diarios de v18
    journals_v18 = odoo_v18.search_read(
        'account.journal',
        [('company_id', '=', COMPANY_ID)],
        fields=['id', 'code', 'name', 'type']
    )
    
    v18_codes = {j['code'] for j in journals_v18}
    
    created_journals = []
    
    for journal in journals_v13:
        if journal['code'] not in v18_codes:
            print(f"\nCreando diario: {journal['code']} - {journal['name']}")
            
            # Preparar valores para crear en v18
            vals = {
                'name': journal['name'],
                'code': journal['code'],
                'type': journal['type'],
                'company_id': COMPANY_ID,
            }
            
            try:
                new_id = odoo_v18.create('account.journal', vals)
                created_journals.append({
                    'v13_id': journal['id'],
                    'v18_id': new_id,
                    'code': journal['code'],
                    'name': journal['name']
                })
                print(f"  ✓ Creado con ID: {new_id}")
            except Exception as e:
                print(f"  ✗ Error: {e}")
    
    print(f"\n✓ Diarios creados: {len(created_journals)}")
    return created_journals


def create_journal_mapping():
    """Crea mapeo completo de diarios."""
    print("\n" + "=" * 70)
    print("CREANDO MAPEO DE DIARIOS")
    print("=" * 70)
    
    journals_v13 = odoo_v13.search_read(
        'account.journal',
        [('company_id', '=', COMPANY_ID)],
        fields=['id', 'code', 'name', 'type']
    )
    
    journals_v18 = odoo_v18.search_read(
        'account.journal',
        [('company_id', '=', COMPANY_ID)],
        fields=['id', 'code', 'name', 'type']
    )
    
    v18_by_code = {j['code']: j for j in journals_v18}
    
    journal_mapping = {}
    
    for journal in journals_v13:
        v18_journal = v18_by_code.get(journal['code'])
        if v18_journal:
            journal_mapping[journal['id']] = {
                'v13_id': journal['id'],
                'v18_id': v18_journal['id'],
                'code': journal['code'],
                'name': journal['name']
            }
    
    print(f"\n✓ Diarios mapeados: {len(journal_mapping)}")
    return journal_mapping


def save_mappings(mappings):
    """Guarda los mapeos en un archivo JSON."""
    with open(MAPPINGS_FILE, 'w') as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Mapeos guardados en {MAPPINGS_FILE}")


def main():
    print("=" * 70)
    print(f"CREACIÓN DE MAPEOS - COMPANY_ID: {COMPANY_ID}")
    print("=" * 70)
    
    # 1. Crear diarios faltantes primero
    create_missing_journals()
    
    # 2. Crear mapeos
    tax_mapping = create_tax_mapping()
    account_mapping, accounts_missing = create_account_mapping()
    journal_mapping = create_journal_mapping()
    
    # 3. Guardar mapeos
    mappings = {
        'taxes': {str(k): v for k, v in tax_mapping.items()},
        'accounts': {str(k): v for k, v in account_mapping.items()},
        'journals': {str(k): v for k, v in journal_mapping.items()}
    }
    save_mappings(mappings)
    
    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Impuestos mapeados: {len(tax_mapping)}")
    print(f"Cuentas mapeadas: {len(account_mapping)}")
    print(f"Diarios mapeados: {len(journal_mapping)}")
    
    return mappings


if __name__ == '__main__':
    main()
