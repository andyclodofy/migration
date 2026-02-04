# -*- coding: utf-8 -*-
"""
Script para crear conciliaciones precisas basadas en montos exactos.
"""

import os
from dotenv import load_dotenv
from connections import odoo_v13, odoo_v18
from migration_utils import get_v18_id

load_dotenv()

COMPANY_ID = int(os.getenv('COMPANY_ID', '1'))
START_DATE = os.getenv('MIGRATION_START_DATE', '2026-01-01')


def build_move_mapping():
    """Construir mapeo completo de moves v13 -> v18."""
    print("Construyendo mapeo de moves...")
    
    # Facturas
    invoice_tracking = odoo_v18.search_read(
        'migration.tracking',
        [('model_name', '=', 'account.move')],
        fields=['v13_id', 'v18_id']
    )
    
    # Asientos entry
    entry_tracking = odoo_v18.search_read(
        'migration.tracking',
        [('model_name', '=', 'account.move.entry')],
        fields=['v13_id', 'v18_id']
    )
    
    # Pagos - necesitamos el move_id asociado
    payment_tracking = odoo_v18.search_read(
        'migration.tracking',
        [('model_name', '=', 'account.payment')],
        fields=['v13_id', 'v18_id']
    )
    
    move_map = {}
    
    # Agregar facturas y entries
    for t in invoice_tracking:
        move_map[t['v13_id']] = t['v18_id']
    for t in entry_tracking:
        move_map[t['v13_id']] = t['v18_id']
    
    # Para pagos, necesitamos mapear move_id de v13 a move_id de v18
    if payment_tracking:
        payment_v13_to_v18 = {t['v13_id']: t['v18_id'] for t in payment_tracking}
        
        # Obtener move_ids de pagos en v18
        v18_payment_ids = list(payment_v13_to_v18.values())
        v18_payments = odoo_v18.search_read(
            'account.payment',
            [('id', 'in', v18_payment_ids)],
            fields=['id', 'move_id']
        )
        v18_payment_to_move = {p['id']: p['move_id'][0] for p in v18_payments if p['move_id']}
        
        # Obtener move_ids de pagos en v13
        v13_payment_ids = list(payment_v13_to_v18.keys())
        for batch_start in range(0, len(v13_payment_ids), 100):
            batch = v13_payment_ids[batch_start:batch_start + 100]
            lines = odoo_v13.search_read(
                'account.move.line',
                [('payment_id', 'in', batch)],
                fields=['move_id', 'payment_id']
            )
            for l in lines:
                v13_move_id = l['move_id'][0]
                v13_payment_id = l['payment_id'][0]
                v18_payment_id = payment_v13_to_v18.get(v13_payment_id)
                if v18_payment_id:
                    v18_move_id = v18_payment_to_move.get(v18_payment_id)
                    if v18_move_id:
                        move_map[v13_move_id] = v18_move_id
    
    print(f"  Total moves mapeados: {len(move_map)}")
    return move_map


def fix_reconciliations():
    """Crear conciliaciones precisas basadas en montos exactos."""
    print("=" * 70)
    print("CORRECCIÓN DE CONCILIACIONES")
    print("=" * 70)
    
    move_map = build_move_mapping()
    
    # Obtener todas las conciliaciones de v13
    reconciles_v13 = odoo_v13.search_read(
        'account.partial.reconcile',
        [
            ('create_date', '>=', START_DATE),
            ('company_id', '=', COMPANY_ID)
        ],
        fields=['id', 'debit_move_id', 'credit_move_id', 'amount'],
        order='id ASC'
    )
    
    print(f"Total conciliaciones en v13: {len(reconciles_v13)}")
    
    created = 0
    skipped = 0
    errors = []
    
    for i, rec in enumerate(reconciles_v13):
        if i > 0 and i % 200 == 0:
            print(f"  Procesando {i}/{len(reconciles_v13)}... (creadas: {created})")
        
        try:
            amount = rec['amount']
            
            # Obtener info de líneas en v13
            debit_line_v13 = odoo_v13.search_read(
                'account.move.line',
                [('id', '=', rec['debit_move_id'][0])],
                fields=['move_id', 'debit', 'credit', 'partner_id']
            )
            credit_line_v13 = odoo_v13.search_read(
                'account.move.line',
                [('id', '=', rec['credit_move_id'][0])],
                fields=['move_id', 'debit', 'credit', 'partner_id']
            )
            
            if not debit_line_v13 or not credit_line_v13:
                skipped += 1
                continue
            
            debit_line_v13 = debit_line_v13[0]
            credit_line_v13 = credit_line_v13[0]
            
            debit_move_v13 = debit_line_v13['move_id'][0]
            credit_move_v13 = credit_line_v13['move_id'][0]
            
            # Buscar moves en v18
            debit_move_v18 = move_map.get(debit_move_v13)
            credit_move_v18 = move_map.get(credit_move_v13)
            
            if not debit_move_v18 or not credit_move_v18:
                skipped += 1
                continue
            
            # Buscar línea de débito en v18 con monto exacto y partner
            debit_amount = debit_line_v13['debit']  # El monto del débito original
            
            # Primero intentar con monto exacto + partner
            debit_partner_v18 = None
            if debit_line_v13.get('partner_id'):
                debit_partner_v18 = get_v18_id(debit_line_v13['partner_id'][0], 'res.partner')
            
            domain_debit = [
                ('move_id', '=', debit_move_v18),
                ('account_type', 'in', ['asset_receivable', 'liability_payable']),
                ('debit', '=', debit_amount),
                ('reconciled', '=', False)
            ]
            if debit_partner_v18:
                domain_debit.append(('partner_id', '=', debit_partner_v18))
            
            debit_lines_v18 = odoo_v18.search_read(
                'account.move.line',
                domain_debit,
                fields=['id', 'debit', 'credit', 'amount_residual']
            )
            
            # Si no hay match, intentar sin partner
            if not debit_lines_v18 and debit_partner_v18:
                debit_lines_v18 = odoo_v18.search_read(
                    'account.move.line',
                    [
                        ('move_id', '=', debit_move_v18),
                        ('account_type', 'in', ['asset_receivable', 'liability_payable']),
                        ('debit', '=', debit_amount),
                        ('reconciled', '=', False)
                    ],
                    fields=['id', 'debit', 'credit', 'amount_residual']
                )
            
            # Si no hay match exacto, buscar por residual
            if not debit_lines_v18:
                debit_lines_v18 = odoo_v18.search_read(
                    'account.move.line',
                    [
                        ('move_id', '=', debit_move_v18),
                        ('account_type', 'in', ['asset_receivable', 'liability_payable']),
                        ('reconciled', '=', False),
                        ('amount_residual', '>', 0)
                    ],
                    fields=['id', 'debit', 'credit', 'amount_residual'],
                    limit=1
                )
            
            # Buscar línea de crédito en v18 con monto exacto y partner
            credit_amount = credit_line_v13['credit']  # El monto del crédito original
            
            # Primero intentar con monto exacto + partner
            credit_partner_v18 = None
            if credit_line_v13.get('partner_id'):
                credit_partner_v18 = get_v18_id(credit_line_v13['partner_id'][0], 'res.partner')
            
            domain_credit = [
                ('move_id', '=', credit_move_v18),
                ('account_type', 'in', ['asset_receivable', 'liability_payable']),
                ('credit', '=', credit_amount),
                ('reconciled', '=', False)
            ]
            if credit_partner_v18:
                domain_credit.append(('partner_id', '=', credit_partner_v18))
            
            credit_lines_v18 = odoo_v18.search_read(
                'account.move.line',
                domain_credit,
                fields=['id', 'debit', 'credit', 'amount_residual']
            )
            
            # Si no hay match, intentar sin partner
            if not credit_lines_v18 and credit_partner_v18:
                credit_lines_v18 = odoo_v18.search_read(
                    'account.move.line',
                    [
                        ('move_id', '=', credit_move_v18),
                        ('account_type', 'in', ['asset_receivable', 'liability_payable']),
                        ('credit', '=', credit_amount),
                        ('reconciled', '=', False)
                    ],
                    fields=['id', 'debit', 'credit', 'amount_residual']
                )
            
            # Si no hay match exacto, buscar por residual negativo (crédito)
            if not credit_lines_v18:
                credit_lines_v18 = odoo_v18.search_read(
                    'account.move.line',
                    [
                        ('move_id', '=', credit_move_v18),
                        ('account_type', 'in', ['asset_receivable', 'liability_payable']),
                        ('reconciled', '=', False),
                        ('amount_residual', '<', 0)
                    ],
                    fields=['id', 'debit', 'credit', 'amount_residual'],
                    limit=1
                )
            
            if not debit_lines_v18 or not credit_lines_v18:
                skipped += 1
                continue
            
            # Conciliar las líneas específicas
            line_ids = [debit_lines_v18[0]['id'], credit_lines_v18[0]['id']]
            
            try:
                odoo_v18.execute('account.move.line', 'reconcile', line_ids)
                created += 1
            except Exception as e:
                err_str = str(e).lower()
                if 'already reconciled' in err_str or 'ya conciliado' in err_str:
                    skipped += 1
                elif 'unhashable' not in err_str:
                    errors.append(f"Rec {rec['id']}: {str(e)[:50]}")
        
        except Exception as e:
            errors.append(f"Error {rec['id']}: {str(e)[:50]}")
    
    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Total procesadas: {len(reconciles_v13)}")
    print(f"Creadas: {created}")
    print(f"Saltadas: {skipped}")
    print(f"Errores: {len(errors)}")
    
    if errors[:10]:
        print()
        print("Primeros errores:")
        for e in errors[:10]:
            print(f"  - {e}")


if __name__ == '__main__':
    fix_reconciliations()
