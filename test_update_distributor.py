"""
Prueba: Actualizar distributor_id de un solo contrato
"""
from connections import odoo_v13, odoo_v18
from migration_utils import get_v18_id

V13_CONTRACT_ID = 70611

print("=" * 70)
print(f"PRUEBA: Actualizar distributor_id del contrato v13 ID {V13_CONTRACT_ID}")
print("=" * 70)

# 1. Obtener el v18_id del contrato
v18_contract_id = get_v18_id(V13_CONTRACT_ID, 'contract.contract')
print(f"\n1. ID del contrato en v18: {v18_contract_id}")

if not v18_contract_id:
    print("   ERROR: Contrato no migrado")
    exit()

# 2. Obtener invoice_partner_id de v13
v13_data = odoo_v13.read(
    'contract.contract',
    [V13_CONTRACT_ID],
    ['name', 'invoice_partner_id']
)

if not v13_data:
    print("   ERROR: Contrato no encontrado en v13")
    exit()

v13_record = v13_data[0]
print(f"\n2. Datos del contrato en v13:")
print(f"   - Nombre: {v13_record.get('name')}")

invoice_partner = v13_record.get('invoice_partner_id')
if not invoice_partner:
    print("   - invoice_partner_id: No tiene asignado")
    exit()

invoice_partner_v13_id = invoice_partner[0]
invoice_partner_name = invoice_partner[1]
print(f"   - invoice_partner_id (v13): {invoice_partner_v13_id} ({invoice_partner_name})")

# 3. Buscar el ID del invoice_partner en v18
distributor_v18_id = get_v18_id(invoice_partner_v13_id, 'res.partner')
print(f"\n3. ID del invoice_partner en v18: {distributor_v18_id}")

if not distributor_v18_id:
    print("   ERROR: Partner no migrado a v18")
    exit()

# 4. Ver valor actual de distributor_id en v18
v18_data = odoo_v18.read(
    'sale.subscription',
    [v18_contract_id],
    ['name', 'distributor_id']
)
current_distributor = v18_data[0].get('distributor_id') if v18_data else None
print(f"\n4. Valor actual de distributor_id en v18: {current_distributor}")

# 5. Actualizar distributor_id
print(f"\n5. Actualizando distributor_id = {distributor_v18_id}...")
odoo_v18.write(
    'sale.subscription',
    [v18_contract_id],
    {'distributor_id': distributor_v18_id}
)
print("   ✓ Actualizado correctamente")

# 6. Verificar el cambio
v18_data_after = odoo_v18.read(
    'sale.subscription',
    [v18_contract_id],
    ['distributor_id']
)
new_distributor = v18_data_after[0].get('distributor_id') if v18_data_after else None
print(f"\n6. Nuevo valor de distributor_id: {new_distributor}")
