"""
Script para migrar conciliaciones (account.partial.reconcile) de Odoo v13 a v18.
Utiliza el campo x_v13_id en v18 para encontrar las líneas correspondientes.
"""

import os
from dotenv import load_dotenv
from connections import odoo_v13, odoo_v18

load_dotenv()

COMPANY_ID = int(os.getenv("COMPANY_ID", "1"))
START_DATE = os.getenv("MIGRATION_START_DATE", "2026-01-01")


def migrate_reconciliations():
    print("=" * 70)
    print("MIGRACIÓN DE CONCILIACIONES")
    print("=" * 70)
    print(f"Fecha inicio: {START_DATE}")
    print(f"Company ID: {COMPANY_ID}")

    # 1. Buscar conciliaciones en v13
    print("\nBuscando conciliaciones en v13...")
    reconciles_v13 = odoo_v13.search_read(
        "account.partial.reconcile",
        [
            ("create_date", ">=", START_DATE),
            ("max_date", ">=", START_DATE),  # Asegurar relevancia en periodo
            # ("company_id", "=", COMPANY_ID) # A veces partial no tiene company_id directo en v13 dependiendo version, pero partial.reconcile suele tenerlo o inferirlo.
            # Verificaremos por lineas mejor si falla.
        ],
        fields=["debit_move_id", "credit_move_id", "amount"],
        order="id asc",
    )

    # Filtrar por company si es necesario (si query no lo soporta directo o para seguridad)
    # Pero asumamos que está bien. Si falla, añadimos check.

    print(f"Encontradas: {len(reconciles_v13)} conciliaciones candidatas.")

    migrated = 0
    errors = 0
    skipped = 0

    # Cache local para evitar muchas lecturas
    # Dict key: v13_line_id -> value: v18_line_id
    line_map_cache = {}

    def get_v18_line_id(v13_line_id):
        if v13_line_id in line_map_cache:
            return line_map_cache[v13_line_id]

        # Buscar en v18 por x_v13_id
        lines = odoo_v18.search_read(
            "account.move.line",
            [("x_v13_id", "=", v13_line_id)],
            fields=["id"],
            limit=1,
        )
        if lines:
            line_map_cache[v13_line_id] = lines[0]["id"]
            return lines[0]["id"]

        return None

    print("\nProcesando conciliaciones...")

    for rec in reconciles_v13:
        try:
            v13_debit_id = rec["debit_move_id"][0]
            v13_credit_id = rec["credit_move_id"][0]
            amount = rec["amount"]

            # Obtener IDs en v18
            v18_debit_id = get_v18_line_id(v13_debit_id)
            v18_credit_id = get_v18_line_id(v13_credit_id)

            if not v18_debit_id:
                # print(f"  Saltado: Línea Débito v13 {v13_debit_id} no encontrada en v18.")
                skipped += 1
                continue

            if not v18_credit_id:
                # print(f"  Saltado: Línea Crédito v13 {v13_credit_id} no encontrada en v18.")
                skipped += 1
                continue

            # Verificar si ya están conciliadas entre sí
            # En v18 partial reconcile conecta las dos lineas.
            # Podemos intentar conciliar y capturar error si ya está.
            # Odoo 'reconcile' method maneja partials.

            try:
                # Intentar conciliar
                # Nota: reconcile() en Odoo toma un recordset de líneas.
                odoo_v18.execute(
                    "account.move.line", "reconcile", [v18_debit_id, v18_credit_id]
                )
                print(
                    f"  ✓ Conciliado: v13[{v13_debit_id} <-> {v13_credit_id}] => v18[{v18_debit_id} <-> {v18_credit_id}] ($ {amount})"
                )
                migrated += 1

            except Exception as e:
                err_str = str(e)
                if (
                    "already reconciled" in err_str
                    or "already created" in err_str
                    or "ya han sido conciliados" in err_str
                ):
                    # print(f"  - Ya conciliado.")
                    skipped += 1
                else:
                    print(
                        f"  ✗ Error conciliando v18[{v18_debit_id}, {v18_credit_id}]: {err_str}"
                    )
                    errors += 1

        except Exception as e:
            print(f"  ✗ Error procesando registro {rec['id']}: {e}")
            errors += 1

    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)
    print(f"Total procesados: {len(reconciles_v13)}")
    print(f"Conciliaciones exitosas: {migrated}")
    print(f"Saltados (no encontrados / ya hechos): {skipped}")
    print(f"Errores: {errors}")


if __name__ == "__main__":
    migrate_reconciliations()
