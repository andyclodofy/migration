"""
Prueba: Buscar contrato de v13 en v18 y su invoice_partner_id
"""
from migration_utils import get_v18_id, get_v13_record

V13_CONTRACT_ID = 70611

print("=" * 60)
print(f"BUSCANDO CONTRATO V13 ID: {V13_CONTRACT_ID}")
print("=" * 60)

# 1. Obtener el ID en v18 del contrato (contract.contract -> sale.subscription)
v18_contract_id = get_v18_id(V13_CONTRACT_ID, 'contract.contract')
print(f"\n1. ID del contrato en v18 (sale.subscription): {v18_contract_id}")

# 2. Obtener el invoice_partner_id del contrato en v13
contract_v13 = get_v13_record(
    V13_CONTRACT_ID,
    'contract.contract',
    fields=['name', 'invoice_partner_id']
)

if contract_v13:
    print(f"\n2. Datos del contrato en v13:")
    print(f"   - Nombre: {contract_v13.get('name')}")
    
    invoice_partner = contract_v13.get('invoice_partner_id')
    if invoice_partner:
        invoice_partner_v13_id = invoice_partner[0]
        invoice_partner_name = invoice_partner[1]
        print(f"   - invoice_partner_id (v13): {invoice_partner_v13_id} ({invoice_partner_name})")
        
        # 3. Buscar el ID en v18 del invoice_partner_id
        invoice_partner_v18_id = get_v18_id(invoice_partner_v13_id, 'res.partner')
        print(f"\n3. ID del invoice_partner_id en v18: {invoice_partner_v18_id}")
    else:
        print("   - invoice_partner_id: No tiene asignado")
else:
    print(f"No se encontró el contrato {V13_CONTRACT_ID} en v13")
