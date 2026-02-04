# -*- coding: utf-8 -*-
"""
Crea los contactos faltantes en v18 basándose en v13.
"""

from connections import odoo_v13, odoo_v18
from migration_utils import get_v18_id


def create_missing_partners():
    """Crear contactos faltantes."""
    print("=" * 70)
    print("CREACIÓN DE CONTACTOS FALTANTES")
    print("=" * 70)
    
    # Partners que faltaban en migraciones anteriores
    missing_ids = [146126, 146110]
    
    # Verificar cuáles realmente faltan
    to_create = []
    for partner_id in missing_ids:
        v18_id = get_v18_id(partner_id, 'res.partner')
        if not v18_id:
            to_create.append(partner_id)
        else:
            print(f"  Partner {partner_id} ya existe en v18 como ID {v18_id}")
    
    if not to_create:
        print("\nTodos los partners ya existen en v18")
        return
    
    # Obtener info de v13
    partners_v13 = odoo_v13.search_read(
        'res.partner',
        [('id', 'in', to_create)],
        fields=[
            'id', 'name', 'email', 'phone', 'mobile', 'vat', 
            'street', 'street2', 'city', 'zip', 'country_id', 'state_id',
            'is_company', 'parent_id', 'comment', 'website', 'lang',
            'customer_rank', 'supplier_rank'
        ]
    )
    
    print(f"\nCreando {len(partners_v13)} contactos...")
    
    created = 0
    for partner in partners_v13:
        try:
            # Preparar valores
            vals = {
                'name': partner['name'],
                'is_company': partner['is_company'],
                'email': partner.get('email') or False,
                'phone': partner.get('phone') or False,
                'mobile': partner.get('mobile') or False,
                'vat': partner.get('vat') or False,
                'street': partner.get('street') or False,
                'street2': partner.get('street2') or False,
                'city': partner.get('city') or False,
                'zip': partner.get('zip') or False,
                'comment': partner.get('comment') or False,
                'website': partner.get('website') or False,
                'lang': partner.get('lang') or False,
            }
            
            # Mapear país
            if partner.get('country_id'):
                countries = odoo_v18.search_read(
                    'res.country',
                    [('code', '=', 'ES')],  # Asumimos España
                    fields=['id'],
                    limit=1
                )
                if countries:
                    vals['country_id'] = countries[0]['id']
            
            # Mapear estado/provincia si existe
            if partner.get('state_id'):
                state_name = partner['state_id'][1]
                states = odoo_v18.search_read(
                    'res.country.state',
                    [('name', 'ilike', state_name)],
                    fields=['id'],
                    limit=1
                )
                if states:
                    vals['state_id'] = states[0]['id']
            
            # Mapear parent si existe
            if partner.get('parent_id'):
                parent_v18_id = get_v18_id(partner['parent_id'][0], 'res.partner')
                if parent_v18_id:
                    vals['parent_id'] = parent_v18_id
            
            # Crear en v18
            new_id = odoo_v18.create('res.partner', vals)
            
            # Registrar en tracking
            odoo_v18.create('migration.tracking', {
                'name': f"res.partner:{partner['id']}",
                'model_name': 'res.partner',
                'v13_id': partner['id'],
                'v18_id': new_id,
            })
            
            created += 1
            print(f"  ✓ {partner['name']} (v13:{partner['id']} -> v18:{new_id})")
            
        except Exception as e:
            print(f"  ✗ {partner['name']}: {str(e)[:80]}")
    
    print(f"\n✅ Creados: {created}/{len(partners_v13)}")


if __name__ == '__main__':
    create_missing_partners()
