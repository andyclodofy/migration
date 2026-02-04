"""
Compara impuestos entre v13 y v18 para crear mapeo manual.
"""
import os
from dotenv import load_dotenv
from connections import odoo_v13, odoo_v18

load_dotenv()

COMPANY_ID = int(os.getenv('COMPANY_ID', 1))

print("=" * 100)
print("COMPARACIÓN DE IMPUESTOS V13 vs V18")
print("=" * 100)

# Obtener impuestos de v13
taxes_v13 = odoo_v13.search_read(
    'account.tax',
    [('company_id', '=', COMPANY_ID)],
    fields=['id', 'name', 'type_tax_use', 'amount', 'description']
)

# Obtener impuestos de v18
taxes_v18 = odoo_v18.search_read(
    'account.tax',
    [('company_id', '=', COMPANY_ID)],
    fields=['id', 'name', 'type_tax_use', 'amount', 'description']
)

print(f"\n{'='*50}")
print("IMPUESTOS EN V13 (VENTA)")
print(f"{'='*50}")
for t in sorted([t for t in taxes_v13 if t['type_tax_use'] == 'sale'], key=lambda x: x['amount']):
    print(f"[{t['id']:3}] {t['amount']:6.2f}% | {t['name'][:60]}")

print(f"\n{'='*50}")
print("IMPUESTOS EN V18 (VENTA)")
print(f"{'='*50}")
for t in sorted([t for t in taxes_v18 if t['type_tax_use'] == 'sale'], key=lambda x: x['amount']):
    print(f"[{t['id']:3}] {t['amount']:6.2f}% | {t['name'][:60]}")

print(f"\n{'='*50}")
print("IMPUESTOS EN V13 (COMPRA)")
print(f"{'='*50}")
for t in sorted([t for t in taxes_v13 if t['type_tax_use'] == 'purchase'], key=lambda x: x['amount']):
    print(f"[{t['id']:3}] {t['amount']:6.2f}% | {t['name'][:60]}")

print(f"\n{'='*50}")
print("IMPUESTOS EN V18 (COMPRA)")
print(f"{'='*50}")
for t in sorted([t for t in taxes_v18 if t['type_tax_use'] == 'purchase'], key=lambda x: x['amount']):
    print(f"[{t['id']:3}] {t['amount']:6.2f}% | {t['name'][:60]}")
