"""
Verifica cuántas facturas hay para migrar en 2026.
"""
import os
from dotenv import load_dotenv
from connections import odoo_v13

load_dotenv()

COMPANY_ID = int(os.getenv('COMPANY_ID', 1))
MIGRATION_START_DATE = os.getenv('MIGRATION_START_DATE', '2026-01-01')

print("=" * 70)
print("VERIFICACIÓN DE FACTURAS A MIGRAR")
print("=" * 70)
print(f"Fecha inicio: {MIGRATION_START_DATE}")
print(f"Company ID: {COMPANY_ID}")

# Verificar campos disponibles en account.move de v13
fields = odoo_v13.fields_get('account.move', ['string', 'type'])
print(f"\nCampos type/move_type disponibles:")
if 'type' in fields:
    print(f"  - type: {fields['type']}")
if 'move_type' in fields:
    print(f"  - move_type: {fields['move_type']}")

# Contar por tipo
types = ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']

print(f"\nFacturas publicadas desde {MIGRATION_START_DATE}:")

total = 0
for inv_type in types:
    domain = [
        ('company_id', '=', COMPANY_ID),
        ('state', '=', 'posted'),
        ('date', '>=', MIGRATION_START_DATE),
        ('type', '=', inv_type)
    ]
    count = odoo_v13.search_count('account.move', domain)
    total += count
    
    type_names = {
        'out_invoice': 'Facturas de cliente',
        'in_invoice': 'Facturas de proveedor',
        'out_refund': 'Notas crédito cliente',
        'in_refund': 'Notas crédito proveedor'
    }
    print(f"  {type_names[inv_type]}: {count}")

print(f"\nTOTAL: {total}")

# Mostrar ejemplo
print("\nEjemplo de factura:")
sample = odoo_v13.search_read(
    'account.move',
    [
        ('company_id', '=', COMPANY_ID),
        ('state', '=', 'posted'),
        ('date', '>=', MIGRATION_START_DATE),
        ('type', 'in', types)
    ],
    fields=['name', 'type', 'partner_id', 'date', 'amount_total', 'state'],
    limit=1
)
if sample:
    inv = sample[0]
    print(f"  - {inv['name']}")
    print(f"  - Tipo: {inv['type']}")
    print(f"  - Partner: {inv['partner_id'][1] if inv['partner_id'] else 'N/A'}")
    print(f"  - Fecha: {inv['date']}")
    print(f"  - Total: {inv['amount_total']}")
