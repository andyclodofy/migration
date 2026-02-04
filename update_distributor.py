"""
Actualiza el campo distributor_id en sale.subscription (v18)
con el invoice_partner_id de contract.contract (v13)

VERSION OPTIMIZADA - Consultas en lote

Autor: andyengit
Mantenedor: andyengit
"""
from connections import odoo_v13, odoo_v18

BATCH_SIZE = 500


def update_distributor_ids():
    """
    Para todos los contratos migrados:
    1. Obtiene el invoice_partner_id de v13 (en lote)
    2. Busca los IDs correspondientes en v18 (en lote)
    3. Actualiza distributor_id en v18
    """
    print("=" * 70)
    print("ACTUALIZANDO distributor_id EN sale.subscription (v18)")
    print("=" * 70)
    
    # 1. Contar total de contratos migrados
    total = odoo_v18.search_count(
        'migration.tracking',
        [('model_name', '=', 'sale.subscription')]
    )
    print(f"\nContratos migrados encontrados: {total}")
    
    if total == 0:
        print("No hay contratos migrados.")
        return
    
    updated = 0
    skipped_no_invoice_partner = 0
    skipped_partner_not_migrated = 0
    errors = []
    
    # Procesar en lotes
    for offset in range(0, total, BATCH_SIZE):
        batch_num = (offset // BATCH_SIZE) + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\n[Lote {batch_num}/{total_batches}] Procesando {offset} - {min(offset + BATCH_SIZE, total)}...")
        
        # 1. Obtener lote de contratos migrados
        migrated_contracts = odoo_v18.search_read(
            'migration.tracking',
            [('model_name', '=', 'sale.subscription')],
            fields=['v13_id', 'v18_id'],
            offset=offset,
            limit=BATCH_SIZE
        )
        
        # Crear mapeos
        v13_to_v18_contract = {c['v13_id']: c['v18_id'] for c in migrated_contracts}
        v13_contract_ids = list(v13_to_v18_contract.keys())
        
        # 2. Leer todos los invoice_partner_id de v13 en UNA llamada
        v13_contracts = odoo_v13.search_read(
            'contract.contract',
            [('id', 'in', v13_contract_ids)],
            fields=['id', 'invoice_partner_id']
        )
        
        # Mapear v13_contract_id -> invoice_partner_v13_id
        contract_to_invoice_partner = {}
        invoice_partner_v13_ids = set()
        
        for c in v13_contracts:
            if c.get('invoice_partner_id'):
                partner_v13_id = c['invoice_partner_id'][0]
                contract_to_invoice_partner[c['id']] = partner_v13_id
                invoice_partner_v13_ids.add(partner_v13_id)
            else:
                skipped_no_invoice_partner += 1
        
        if not invoice_partner_v13_ids:
            continue
        
        # 3. Buscar todos los partners en migration.tracking en UNA llamada
        partner_mappings = odoo_v18.search_read(
            'migration.tracking',
            [
                ('model_name', '=', 'res.partner'),
                ('v13_id', 'in', list(invoice_partner_v13_ids))
            ],
            fields=['v13_id', 'v18_id']
        )
        
        # Mapear v13_partner -> v18_partner
        partner_v13_to_v18 = {p['v13_id']: p['v18_id'] for p in partner_mappings}
        
        # 4. Preparar actualizaciones
        for v13_contract_id, invoice_partner_v13_id in contract_to_invoice_partner.items():
            v18_contract_id = v13_to_v18_contract[v13_contract_id]
            distributor_v18_id = partner_v13_to_v18.get(invoice_partner_v13_id)
            
            if not distributor_v18_id:
                skipped_partner_not_migrated += 1
                continue
            
            try:
                odoo_v18.write(
                    'sale.subscription',
                    [v18_contract_id],
                    {'distributor_id': distributor_v18_id}
                )
                updated += 1
            except Exception as e:
                errors.append(f"v18 {v18_contract_id}: {str(e)}")
        
        print(f"   Actualizados en este lote: {updated - sum(1 for _ in range((offset // BATCH_SIZE) * BATCH_SIZE, updated))}")
    
    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Total contratos migrados: {total}")
    print(f"Actualizados correctamente: {updated}")
    print(f"Sin invoice_partner_id: {skipped_no_invoice_partner}")
    print(f"Partner no migrado a v18: {skipped_partner_not_migrated}")
    print(f"Errores: {len(errors)}")
    
    if errors:
        print("\nDetalle de errores:")
        for error in errors[:20]:
            print(f"  - {error}")
        if len(errors) > 20:
            print(f"  ... y {len(errors) - 20} errores más")


if __name__ == '__main__':
    update_distributor_ids()
