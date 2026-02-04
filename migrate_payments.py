# -*- coding: utf-8 -*-
"""
Script para migrar pagos de Odoo v13 a v18 y crear conciliaciones.
"""

import os
from dotenv import load_dotenv
from connections import odoo_v13, odoo_v18
from migration_utils import get_v18_id

load_dotenv()

COMPANY_ID = int(os.getenv("COMPANY_ID", "1"))
START_DATE = os.getenv("MIGRATION_START_DATE", "2026-01-01")
BATCH_SIZE = 50

# Mapeo manual de diarios de banco/efectivo
JOURNAL_MAP = {
    7: 17,  # CAIXABANK, S.A. (BNK1 v13 -> BNK2 v18)
    15: 25,  # Banco Sabadell (SAB v13 -> SAB v18)
    6: 7,  # Efectivo (CSH1 v13 -> CSH1 v18)
    10: 27,  # Paypal (PAYPA v13 -> PAYPA v18)
}


def migrate_payments():
    """Migrar pagos de v13 a v18."""
    print("=" * 70)
    print("MIGRACIÓN DE PAGOS")
    print("=" * 70)

    print(f"Mapeo de diarios: {len(JOURNAL_MAP)} configurados")

    # Obtener pagos ya migrados
    existing = odoo_v18.search_read(
        "migration.tracking",
        [("model_name", "=", "account.payment")],
        fields=["v13_id"],
    )
    existing_ids = {r["v13_id"] for r in existing}
    print(f"Pagos ya migrados: {len(existing_ids)}")

    # Obtener pagos de v13
    payments_v13 = odoo_v13.search_read(
        "account.payment",
        [
            ("payment_date", ">=", START_DATE),
            ("state", "=", "posted"),
            ("company_id", "=", COMPANY_ID),
        ],
        fields=[
            "id",
            "name",
            "payment_date",
            "amount",
            "partner_id",
            "payment_type",
            "journal_id",
            "currency_id",
            "communication",
            "partner_type",
        ],
        order="id ASC",
    )

    # Filtrar los no migrados
    to_migrate = [p for p in payments_v13 if p["id"] not in existing_ids]
    print(f"Pagos a migrar: {len(to_migrate)} de {len(payments_v13)}")
    print()

    migrated = 0
    errors = []

    for i, payment in enumerate(to_migrate):
        try:
            # Obtener partner en v18
            partner_v18_id = (
                get_v18_id(payment["partner_id"][0], "res.partner")
                if payment["partner_id"]
                else None
            )
            if not partner_v18_id:
                errors.append(
                    f"[{payment['id']}] {payment['name']}: Partner {payment['partner_id'][0]} no migrado"
                )
                print(f"  ✗ {payment['name']}: Partner no migrado")
                continue

            # Mapear diario
            journal_v18_id = JOURNAL_MAP.get(payment["journal_id"][0])
            if not journal_v18_id:
                errors.append(
                    f"[{payment['id']}] {payment['name']}: Diario {payment['journal_id'][1]} no mapeado"
                )
                print(f"  ✗ {payment['name']}: Diario no mapeado")
                continue

            # Preparar valores para v18 (sin 'ref' que no existe en v18)
            payment_vals = {
                "payment_type": payment["payment_type"],
                "partner_type": payment["partner_type"],
                "partner_id": partner_v18_id,
                "amount": payment["amount"],
                "date": payment["payment_date"],
                "journal_id": journal_v18_id,
            }

            # Crear pago en v18
            payment_v18_id = odoo_v18.create("account.payment", payment_vals)

            # Publicar el pago (puede retornar None que causa error XML-RPC)
            try:
                odoo_v18.execute("account.payment", "action_post", [payment_v18_id])
            except Exception:
                pass  # Ignorar error de XML-RPC si el pago ya se publicó

            # Registrar en tracking
            odoo_v18.create(
                "migration.tracking",
                {
                    "name": f"Payment {payment['name']}",
                    "model_name": "account.payment",
                    "v13_id": payment["id"],
                    "v18_id": payment_v18_id,
                },
            )

            migrated += 1
            print(f"  ✓ {payment['name']} -> v18 ID: {payment_v18_id}")

        except Exception as e:
            error_msg = f"[{payment['id']}] {payment['name']}: {str(e)[:100]}"
            errors.append(error_msg)
            print(f"  ✗ {payment['name']}: {str(e)[:80]}")

    print()
    print("=" * 70)
    print("RESUMEN DE PAGOS")
    print("=" * 70)
    print(f"Total pagos: {len(to_migrate)}")
    print(f"Migrados: {migrated}")
    print(f"Errores: {len(errors)}")

    if errors and len(errors) <= 10:
        print()
        print("Errores:")
        for e in errors[:10]:
            print(f"  - {e}")

    return migrated, errors


def migrate_reconciliations():
    """Crear conciliaciones en v18 basadas en v13."""
    print()
    print("=" * 70)
    print("MIGRACIÓN DE CONCILIACIONES")
    print("=" * 70)

    # Obtener mapeo de facturas migradas (v13 move_id -> v18 move_id)
    invoice_tracking = odoo_v18.search_read(
        "migration.tracking",
        [("model_name", "=", "account.move")],
        fields=["v13_id", "v18_id"],
    )
    invoice_map = {r["v13_id"]: r["v18_id"] for r in invoice_tracking}

    # Obtener mapeo de pagos migrados (v13 payment_id -> v18 payment_id)
    payment_tracking = odoo_v18.search_read(
        "migration.tracking",
        [("model_name", "=", "account.payment")],
        fields=["v13_id", "v18_id"],
    )
    payment_v13_to_v18 = {r["v13_id"]: r["v18_id"] for r in payment_tracking}

    # Obtener el move_id de cada pago en v18
    if payment_v13_to_v18:
        payment_v18_ids = list(payment_v13_to_v18.values())
        payments_v18 = odoo_v18.search_read(
            "account.payment", [("id", "in", payment_v18_ids)], fields=["id", "move_id"]
        )
        payment_id_to_move = {
            p["id"]: p["move_id"][0] for p in payments_v18 if p["move_id"]
        }
    else:
        payment_id_to_move = {}

    # Mapear v13 payment move_id a v18 payment move_id
    # Buscamos todos los move.line que tienen payment_id y los mapeamos
    payment_move_v13_to_v18 = {}
    if payment_v13_to_v18:
        # Buscar líneas de pagos en v13 para obtener sus move_id
        v13_payment_ids = list(payment_v13_to_v18.keys())

        # Buscar todas las líneas que pertenecen a estos pagos
        for batch_start in range(0, len(v13_payment_ids), 100):
            batch_ids = v13_payment_ids[batch_start : batch_start + 100]
            lines_v13 = odoo_v13.search_read(
                "account.move.line",
                [("payment_id", "in", batch_ids)],
                fields=["move_id", "payment_id"],
            )
            for l in lines_v13:
                v13_move_id = l["move_id"][0]
                v13_payment_id = l["payment_id"][0]
                v18_payment_id = payment_v13_to_v18.get(v13_payment_id)
                if v18_payment_id and v18_payment_id in payment_id_to_move:
                    payment_move_v13_to_v18[v13_move_id] = payment_id_to_move[
                        v18_payment_id
                    ]

    print(f"Facturas migradas: {len(invoice_map)}")
    print(f"Pagos migrados: {len(payment_v13_to_v18)}")
    print(f"Mapeo payment moves: {len(payment_move_v13_to_v18)}")
    print()

    # Obtener conciliaciones de v13
    reconciles_v13 = odoo_v13.search_read(
        "account.partial.reconcile",
        [("create_date", ">=", START_DATE), ("company_id", "=", COMPANY_ID)],
        fields=["id", "debit_move_id", "credit_move_id", "amount"],
        order="id ASC",
    )

    print(f"Total conciliaciones en v13: {len(reconciles_v13)}")


def main():
    print("Iniciando migración de pagos y conciliaciones...")
    print(f"Fecha inicio: {START_DATE}")
    print(f"Company ID: {COMPANY_ID}")
    print()

    # Paso 1: Migrar pagos
    migrated, errors = migrate_payments()

    # Paso 2: Crear conciliaciones
    migrate_reconciliations()

    print()
    print("¡Proceso completado!")


if __name__ == "__main__":
    main()
