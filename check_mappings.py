"""
Verifica y crea mapeos de impuestos, cuentas contables y diarios
entre Odoo v13 y v18 usando el nombre como referencia.

Autor: andyengit
Mantenedor: andyengit
"""
import os
from dotenv import load_dotenv
from connections import odoo_v13, odoo_v18

load_dotenv()

COMPANY_ID = int(os.getenv('COMPANY_ID', 1))


def check_taxes():
    """Verifica mapeo de impuestos por nombre."""
    print("\n" + "=" * 70)
    print("IMPUESTOS (account.tax)")
    print("=" * 70)
    
    # Obtener impuestos de v13
    taxes_v13 = odoo_v13.search_read(
        'account.tax',
        [('company_id', '=', COMPANY_ID)],
        fields=['id', 'name', 'type_tax_use', 'amount']
    )
    print(f"\nImpuestos en v13: {len(taxes_v13)}")
    
    # Obtener impuestos de v18
    taxes_v18 = odoo_v18.search_read(
        'account.tax',
        [('company_id', '=', COMPANY_ID)],
        fields=['id', 'name', 'type_tax_use', 'amount']
    )
    print(f"Impuestos en v18: {len(taxes_v18)}")
    
    # Crear mapeo por nombre
    v18_taxes_by_name = {t['name']: t for t in taxes_v18}
    
    mapped = []
    not_found = []
    
    for tax in taxes_v13:
        v18_tax = v18_taxes_by_name.get(tax['name'])
        if v18_tax:
            mapped.append({
                'v13_id': tax['id'],
                'v18_id': v18_tax['id'],
                'name': tax['name']
            })
        else:
            not_found.append(tax)
    
    print(f"\n✓ Mapeados: {len(mapped)}")
    print(f"✗ No encontrados en v18: {len(not_found)}")
    
    if not_found:
        print("\nImpuestos de v13 sin equivalente en v18:")
        for tax in not_found[:10]:
            print(f"  - [{tax['id']}] {tax['name']} ({tax['type_tax_use']}, {tax['amount']}%)")
        if len(not_found) > 10:
            print(f"  ... y {len(not_found) - 10} más")
    
    return mapped, not_found


def check_accounts():
    """Verifica mapeo de cuentas contables por código."""
    print("\n" + "=" * 70)
    print("CUENTAS CONTABLES (account.account)")
    print("=" * 70)
    
    # Obtener cuentas de v13
    accounts_v13 = odoo_v13.search_read(
        'account.account',
        [('company_id', '=', COMPANY_ID)],
        fields=['id', 'code', 'name']
    )
    print(f"\nCuentas en v13: {len(accounts_v13)}")
    
    # Obtener cuentas de v18 (en v18 no hay company_id en account.account)
    accounts_v18 = odoo_v18.search_read(
        'account.account',
        [],
        fields=['id', 'code', 'name']
    )
    print(f"Cuentas en v18: {len(accounts_v18)}")
    
    # Crear mapeo por código (más confiable que nombre)
    v18_accounts_by_code = {a['code']: a for a in accounts_v18}
    
    mapped = []
    not_found = []
    
    for account in accounts_v13:
        v18_account = v18_accounts_by_code.get(account['code'])
        if v18_account:
            mapped.append({
                'v13_id': account['id'],
                'v18_id': v18_account['id'],
                'code': account['code'],
                'name': account['name']
            })
        else:
            not_found.append(account)
    
    print(f"\n✓ Mapeados por código: {len(mapped)}")
    print(f"✗ No encontrados en v18: {len(not_found)}")
    
    if not_found:
        print("\nCuentas de v13 sin equivalente en v18:")
        for acc in not_found[:10]:
            print(f"  - [{acc['id']}] {acc['code']} - {acc['name']}")
        if len(not_found) > 10:
            print(f"  ... y {len(not_found) - 10} más")
    
    return mapped, not_found


def check_journals():
    """Verifica mapeo de diarios por código o nombre."""
    print("\n" + "=" * 70)
    print("DIARIOS (account.journal)")
    print("=" * 70)
    
    # Obtener diarios de v13
    journals_v13 = odoo_v13.search_read(
        'account.journal',
        [('company_id', '=', COMPANY_ID)],
        fields=['id', 'code', 'name', 'type']
    )
    print(f"\nDiarios en v13: {len(journals_v13)}")
    
    # Obtener diarios de v18
    journals_v18 = odoo_v18.search_read(
        'account.journal',
        [('company_id', '=', COMPANY_ID)],
        fields=['id', 'code', 'name', 'type']
    )
    print(f"Diarios en v18: {len(journals_v18)}")
    
    # Crear mapeo por código
    v18_journals_by_code = {j['code']: j for j in journals_v18}
    
    mapped = []
    not_found = []
    
    for journal in journals_v13:
        v18_journal = v18_journals_by_code.get(journal['code'])
        if v18_journal:
            mapped.append({
                'v13_id': journal['id'],
                'v18_id': v18_journal['id'],
                'code': journal['code'],
                'name': journal['name']
            })
        else:
            not_found.append(journal)
    
    print(f"\n✓ Mapeados por código: {len(mapped)}")
    print(f"✗ No encontrados en v18: {len(not_found)}")
    
    if not_found:
        print("\nDiarios de v13 sin equivalente en v18:")
        for j in not_found:
            print(f"  - [{j['id']}] {j['code']} - {j['name']} ({j['type']})")
    
    return mapped, not_found


def main():
    print("=" * 70)
    print(f"VERIFICACIÓN DE MAPEOS - COMPANY_ID: {COMPANY_ID}")
    print("=" * 70)
    
    taxes_mapped, taxes_missing = check_taxes()
    accounts_mapped, accounts_missing = check_accounts()
    journals_mapped, journals_missing = check_journals()
    
    print("\n" + "=" * 70)
    print("RESUMEN GENERAL")
    print("=" * 70)
    print(f"\nImpuestos:  {len(taxes_mapped)} mapeados, {len(taxes_missing)} faltantes")
    print(f"Cuentas:    {len(accounts_mapped)} mapeadas, {len(accounts_missing)} faltantes")
    print(f"Diarios:    {len(journals_mapped)} mapeados, {len(journals_missing)} faltantes")
    
    if taxes_missing or accounts_missing or journals_missing:
        print("\n⚠️  Hay elementos sin mapear. Revisa antes de continuar con la migración.")
    else:
        print("\n✅ Todo mapeado correctamente. Listo para migrar facturas.")
    
    return {
        'taxes': {'mapped': taxes_mapped, 'missing': taxes_missing},
        'accounts': {'mapped': accounts_mapped, 'missing': accounts_missing},
        'journals': {'mapped': journals_mapped, 'missing': journals_missing}
    }


if __name__ == '__main__':
    main()
