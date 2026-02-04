# -*- coding: utf-8 -*-
"""
Script para migrar asientos contables (entry) de Odoo v13 a v18.
"""

import os
import json
from dotenv import load_dotenv
from connections import odoo_v13, odoo_v18
from migration_utils import get_v18_id

load_dotenv()

COMPANY_ID = int(os.getenv("COMPANY_ID", "1"))
START_DATE = os.getenv("MIGRATION_START_DATE", "2026-01-01")


def load_mappings():
    """Cargar mapeos desde mappings.json."""
    with open("mappings.json", "r") as f:
        data = json.load(f)

    # Mapeo de cuentas
    account_map = data.get("accounts", {})

    # Mapeo de diarios
    journal_map = {}
    for j in data.get("journals", {}).values():
        if "v13_id" in j and "v18_id" in j:
            journal_map[j["v13_id"]] = j["v18_id"]

    return account_map, journal_map


def migrate_entries():
    """Migrar asientos contables de v13 a v18."""
    print("=" * 70)
    print("MIGRACIÓN DE ASIENTOS CONTABLES")
    print("=" * 70)

    # Cargar mapeos
    account_map, journal_map = load_mappings()
    print(f"Mapeo de cuentas: {len(account_map)} configuradas")
    print(f"Mapeo de diarios: {len(journal_map)} configurados")

    # Obtener asientos ya migrados
    existing = odoo_v18.search_read(
        "migration.tracking",
        [("model_name", "=", "account.move.entry")],
        fields=["v13_id"],
    )
    existing_ids = {r["v13_id"] for r in existing}
    print(f"Asientos ya migrados: {len(existing_ids)}")

    # Obtener asientos entry de v13
    entries_v13 = odoo_v13.search_read(
        "account.move",
        [
            ("date", ">=", START_DATE),
            ("state", "=", "posted"),
            ("company_id", "=", COMPANY_ID),
            ("type", "=", "entry"),
        ],
        fields=["id", "name", "date", "journal_id", "ref", "narration", "line_ids"],
        order="id ASC",
    )

    # Filtrar los no migrados
    to_migrate = [e for e in entries_v13 if e["id"] not in existing_ids]
    print(f"Asientos a migrar: {len(to_migrate)} de {len(entries_v13)}")
    print()

    migrated = 0
    errors = []

    for i, entry in enumerate(to_migrate):
        try:
            # Mapear diario
            journal_v18_id = journal_map.get(entry["journal_id"][0])
            if not journal_v18_id:
                # Cache de diarios
                if not getattr(migrate_entries, "journal_cache", None):
                    migrate_entries.journal_cache = {}

                journal_name_clean = entry["journal_id"][1].split(" (")[0]
                if journal_name_clean in migrate_entries.journal_cache:
                    journal_v18_id = migrate_entries.journal_cache[journal_name_clean]
                else:
                    # Buscar por nombre
                    journals = odoo_v18.search_read(
                        "account.journal",
                        [("name", "ilike", journal_name_clean)],
                        fields=["id"],
                        limit=1,
                    )
                    if journals:
                        journal_v18_id = journals[0]["id"]
                        migrate_entries.journal_cache[journal_name_clean] = (
                            journal_v18_id
                        )
                    else:
                        errors.append(
                            f"[{entry['id']}] {entry['name']}: Diario no mapeado"
                        )
                        print(f"  ✗ {entry['name']}: Diario no mapeado")
                        continue

            # Obtener líneas del asiento
            lines_v13 = odoo_v13.search_read(
                "account.move.line",
                [("move_id", "=", entry["id"])],
                fields=[
                    "name",
                    "account_id",
                    "debit",
                    "credit",
                    "partner_id",
                    "analytic_account_id",
                    "tax_ids",
                    "tax_line_id",
                ],
            )

            # Preparar líneas para v18
            line_ids = []
            skip_entry = False

            if not getattr(migrate_entries, "account_cache", None):
                migrate_entries.account_cache = {}

            for line in lines_v13:
                # Mapear cuenta
                account_v13_name = line["account_id"][1]
                account_v18_id = account_map.get(account_v13_name)

                if not account_v18_id:
                    account_code = account_v13_name.split(" ")[0]

                    if account_code in migrate_entries.account_cache:
                        account_v18_id = migrate_entries.account_cache[account_code]
                    else:
                        # Buscar por código
                        accounts = odoo_v18.search_read(
                            "account.account",
                            [("code", "=", account_code)],
                            fields=["id"],
                            limit=1,
                        )
                        if accounts:
                            account_v18_id = accounts[0]["id"]
                            migrate_entries.account_cache[account_code] = account_v18_id
                        else:
                            errors.append(
                                f"[{entry['id']}] {entry['name']}: Cuenta {account_v13_name} no mapeada"
                            )
                            print(
                                f"  ✗ {entry['name']}: Cuenta {account_v13_name} no mapeada"
                            )
                            skip_entry = True
                            break

                # Mapear partner si existe
                partner_v18_id = None
                if line["partner_id"]:
                    partner_v18_id = get_v18_id(line["partner_id"][0], "res.partner")

                line_vals = {
                    "name": line["name"] or "/",
                    "account_id": account_v18_id,
                    "debit": line["debit"],
                    "credit": line["credit"],
                    "x_v13_id": line["id"],
                }

                if partner_v18_id:
                    line_vals["partner_id"] = partner_v18_id

                line_ids.append((0, 0, line_vals))

            if skip_entry:
                continue

            # Crear asiento en v18
            entry_vals = {
                "move_type": "entry",
                "journal_id": journal_v18_id,
                "date": entry["date"],
                "ref": entry["ref"] or entry["name"],
                "line_ids": line_ids,
            }

            # Usar migration.helper para crear (pasar dict directamente, no en lista)
            entry_v18_id = odoo_v18.execute(
                "migration.helper", "create_invoice_xmlrpc", entry_vals
            )

            # Publicar
            try:
                odoo_v18.execute("account.move", "action_post", [entry_v18_id])
            except Exception:
                pass  # Puede retornar None

            # Registrar en tracking
            odoo_v18.create(
                "migration.tracking",
                {
                    "name": f"Entry {entry['name']}",
                    "model_name": "account.move.entry",
                    "v13_id": entry["id"],
                    "v18_id": entry_v18_id,
                },
            )

            migrated += 1
            print(f"  ✓ {entry['name']} -> v18 ID: {entry_v18_id}")

        except Exception as e:
            error_msg = f"[{entry['id']}] {entry['name']}: {str(e)[:100]}"
            errors.append(error_msg)
            print(f"  ✗ {entry['name']}: {str(e)[:80]}")

    print()
    print("=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Total asientos: {len(to_migrate)}")
    print(f"Migrados: {migrated}")
    print(f"Errores: {len(errors)}")

    if errors and len(errors) <= 15:
        print()
        print("Errores:")
        for e in errors[:15]:
            print(f"  - {e}")

    return migrated, errors


def analyze_reconciliations():
    """Analizar conciliaciones entre asientos y facturas."""
    print()
    print("=" * 70)
    print("ANÁLISIS DE CONCILIACIONES")
    print("=" * 70)

    # Obtener tracking de facturas
    invoice_tracking = odoo_v18.search_read(
        "migration.tracking",
        [("model_name", "=", "account.move")],
        fields=["v13_id", "v18_id"],
    )
    invoice_map = {r["v13_id"]: r["v18_id"] for r in invoice_tracking}

    # Obtener tracking de asientos entry
    entry_tracking = odoo_v18.search_read(
        "migration.tracking",
        [("model_name", "=", "account.move.entry")],
        fields=["v13_id", "v18_id"],
    )
    entry_map = {r["v13_id"]: r["v18_id"] for r in entry_tracking}

    print(f"Facturas migradas: {len(invoice_map)}")
    print(f"Asientos migrados: {len(entry_map)}")

    # Buscar conciliaciones en v13 que involucren asientos entry


def main():
    print("Iniciando migración de asientos contables...")
    print(f"Fecha inicio: {START_DATE}")
    print(f"Company ID: {COMPANY_ID}")
    print()

    # Paso 1: Migrar asientos
    migrated, errors = migrate_entries()

    # Paso 2: Analizar y crear conciliaciones
    analyze_reconciliations()

    print()
    print("¡Proceso completado!")


if __name__ == "__main__":
    main()
