"""
Crea la cuenta contable faltante en v18.
"""
import os
import json
from dotenv import load_dotenv
from connections import odoo_v13, odoo_v18

load_dotenv()

COMPANY_ID = int(os.getenv('COMPANY_ID', 1))
MAPPINGS_FILE = 'mappings.json'

print("=" * 70)
print("CREANDO CUENTA FALTANTE EN V18")
print("=" * 70)

# Obtener datos de la cuenta en v13
account_v13 = odoo_v13.search_read(
    'account.account',
    [('code', '=', '5729991'), ('company_id', '=', COMPANY_ID)],
    fields=['id', 'code', 'name', 'user_type_id', 'reconcile']
)

if not account_v13:
    print("Cuenta 5729991 no encontrada en v13")
    exit()

acc = account_v13[0]
print(f"\nCuenta en v13:")
print(f"  - ID: {acc['id']}")
print(f"  - Código: {acc['code']}")
print(f"  - Nombre: {acc['name']}")
print(f"  - Tipo: {acc['user_type_id'][1] if acc['user_type_id'] else 'N/A'}")

# Buscar tipo de cuenta equivalente en v18
# En v18 el campo es account_type en lugar de user_type_id
# Tipos comunes: asset_receivable, asset_cash, liability_payable, etc.

# Buscar una cuenta similar en v18 para determinar el tipo
similar_accounts = odoo_v18.search_read(
    'account.account',
    [('code', 'like', '572%')],
    fields=['id', 'code', 'name', 'account_type'],
    limit=5
)

print(f"\nCuentas similares en v18 (572%):")
account_type = 'asset_current'  # Por defecto
for sa in similar_accounts:
    print(f"  - {sa['code']}: {sa['name']} ({sa['account_type']})")
    if sa['code'].startswith('572'):
        account_type = sa['account_type']

# Crear la cuenta en v18
print(f"\nCreando cuenta con tipo: {account_type}")

vals = {
    'code': acc['code'],
    'name': acc['name'],
    'account_type': account_type,
    'reconcile': acc.get('reconcile', False),
}

try:
    new_id = odoo_v18.create('account.account', vals)
    print(f"✓ Cuenta creada con ID: {new_id}")
    
    # Actualizar mappings.json
    with open(MAPPINGS_FILE, 'r') as f:
        mappings = json.load(f)
    
    mappings['accounts'][str(acc['id'])] = {
        'v13_id': acc['id'],
        'v18_id': new_id,
        'code': acc['code'],
        'name': acc['name']
    }
    
    with open(MAPPINGS_FILE, 'w') as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Mapeo actualizado en {MAPPINGS_FILE}")
    
except Exception as e:
    print(f"✗ Error: {e}")
