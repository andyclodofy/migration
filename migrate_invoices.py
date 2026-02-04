"""
Migra facturas de 2026 de Odoo v13 a v18.

- Solo facturas publicadas (state = 'posted')
- Fecha >= 01/01/2026
- Todos los tipos: out_invoice, in_invoice, out_refund, in_refund

Autor: andyengit
Mantenedor: andyengit
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from connections import odoo_v13, odoo_v18
from migration_utils import get_v18_id

load_dotenv()

COMPANY_ID = int(os.getenv("COMPANY_ID", 1))
MIGRATION_START_DATE = os.getenv("MIGRATION_START_DATE", "2026-01-01")
BATCH_SIZE = 50
MAPPINGS_FILE = "mappings.json"


def load_mappings():
    """Carga los mapeos desde el archivo JSON."""
    with open(MAPPINGS_FILE, "r") as f:
        return json.load(f)


def get_tax_v18_id(mappings, v13_tax_id):
    """Obtiene el ID de impuesto en v18."""
    tax_map = mappings["taxes"].get(str(v13_tax_id))
    return tax_map["v18_id"] if tax_map else None


def get_account_v18_id(mappings, v13_account_id):
    """Obtiene el ID de cuenta en v18."""
    acc_map = mappings["accounts"].get(str(v13_account_id))
    return acc_map["v18_id"] if acc_map else None


def get_journal_v18_id(mappings, v13_journal_id):
    """Obtiene el ID de diario en v18."""
    journal_map = mappings["journals"].get(str(v13_journal_id))
    return journal_map["v18_id"] if journal_map else None


def migrate_invoice(invoice_v13, mappings):
    """
    Migra una factura individual de v13 a v18.

    Returns:
        tuple: (v18_id, error_message)
    """
    try:
        # Mapear partner
        partner_v18_id = get_v18_id(invoice_v13["partner_id"][0], "res.partner")
        if not partner_v18_id:
            return None, f"Partner {invoice_v13['partner_id'][0]} no migrado"

        # Mapear diario
        journal_v18_id = get_journal_v18_id(mappings, invoice_v13["journal_id"][0])
        if not journal_v18_id:
            return None, f"Diario {invoice_v13['journal_id'][1]} no mapeado"

        # Mapear moneda si existe
        currency_v18_id = False
        if invoice_v13.get("currency_id"):
            currency_name = invoice_v13["currency_id"][1]
            if not getattr(migrate_invoice, "currency_cache", None):
                migrate_invoice.currency_cache = {}

            if currency_name in migrate_invoice.currency_cache:
                currency_v18_id = migrate_invoice.currency_cache[currency_name]
            else:
                # Buscar moneda por nombre en v18
                currency = odoo_v18.search_read(
                    "res.currency",
                    [("name", "=", currency_name)],
                    fields=["id"],
                    limit=1,
                )
                if currency:
                    currency_v18_id = currency[0]["id"]
                    migrate_invoice.currency_cache[currency_name] = currency_v18_id

        # Obtener líneas de la factura en v13
        lines_v13 = odoo_v13.search_read(
            "account.move.line",
            [
                ("move_id", "=", invoice_v13["id"]),
                ("exclude_from_invoice_tab", "=", False),
            ],
            fields=[
                "name",
                "quantity",
                "price_unit",
                "discount",
                "account_id",
                "product_id",
                "tax_ids",
                "price_subtotal",
                "price_total",
                "user",
            ],
        )

        # Obtener otras líneas (impuestos, cxc, cxp) de v13 para mapeo posterior
        other_lines_v13 = odoo_v13.search_read(
            "account.move.line",
            [
                ("move_id", "=", invoice_v13["id"]),
                ("exclude_from_invoice_tab", "=", True),
            ],
            fields=["name", "account_id", "debit", "credit", "tax_line_id"],
        )

        # Preparar líneas para v18
        invoice_lines = []
        for line in lines_v13:
            line_vals = {
                "name": line["name"] or "/",
                "quantity": line["quantity"],
                "price_unit": line["price_unit"],
                "discount": line.get("discount", 0),
                "x_v13_id": line["id"],
            }

            # Mapear cuenta
            if line.get("account_id"):
                account_v18_id = get_account_v18_id(mappings, line["account_id"][0])
                if account_v18_id:
                    line_vals["account_id"] = account_v18_id

            # Mapear producto
            if line.get("product_id"):
                product_v18_id = get_v18_id(line["product_id"][0], "product.product")
                if product_v18_id:
                    line_vals["product_id"] = product_v18_id

            # Mapear impuestos
            if line.get("tax_ids"):
                tax_v18_ids = []
                for tax_v13_id in line["tax_ids"]:
                    tax_v18_id = get_tax_v18_id(mappings, tax_v13_id)
                    if tax_v18_id:
                        tax_v18_ids.append(tax_v18_id)
                if tax_v18_ids:
                    line_vals["tax_ids"] = [(6, 0, tax_v18_ids)]

            # Mapear user -> final_user_id
            if line.get("user"):
                user_v18_id = get_v18_id(line["user"][0], "res.partner")
                if user_v18_id:
                    line_vals["final_user_id"] = user_v18_id

            invoice_lines.append((0, 0, line_vals))

        # Preparar valores de la factura
        move_type = invoice_v13.get("type") or invoice_v13.get("move_type")

        invoice_vals = {
            "move_type": move_type,
            "name": invoice_v13.get("name"),  # Mantener nombre original de v13
            "partner_id": partner_v18_id,
            "journal_id": journal_v18_id,
            "invoice_date": invoice_v13.get("invoice_date") or invoice_v13.get("date"),
            "date": invoice_v13.get("date"),
            "ref": invoice_v13.get("ref"),
            "narration": invoice_v13.get("narration"),
            "company_id": COMPANY_ID,
            "invoice_line_ids": invoice_lines,
        }

        if currency_v18_id:
            invoice_vals["currency_id"] = currency_v18_id

        # Crear factura en v18 usando migration.helper (wrapper para v18)
        new_invoice_id = odoo_v18.execute(
            "migration.helper", "create_invoice_xmlrpc", invoice_vals
        )

        # Publicar la factura
        odoo_v18.execute("account.move", "action_post", [new_invoice_id])

        # Actualizar líneas automáticas (impuestos, cxc) con x_v13_id
        if other_lines_v13:
            # Obtener líneas de v18
            lines_v18 = odoo_v18.search_read(
                "account.move.line",
                [("move_id", "=", new_invoice_id), ("x_v13_id", "=", False)],
                fields=["account_id", "debit", "credit", "tax_line_id"],
            )

            for line_v18 in lines_v18:
                # Buscar coincidencia en other_lines_v13
                match = None
                for line_v13 in other_lines_v13:
                    # Mapear cuenta de v13 para comparar
                    acc_v18_id = get_account_v18_id(mappings, line_v13["account_id"][0])

                    # Verificar cuenta
                    if acc_v18_id != line_v18["account_id"][0]:
                        continue

                    # Verificar montos (con pequeña tolerancia por redondeo)
                    if (
                        abs(line_v13["debit"] - line_v18["debit"]) > 0.01
                        or abs(line_v13["credit"] - line_v18["credit"]) > 0.01
                    ):
                        continue

                    # Verificar impuesto si aplica (para líneas de impuesto)
                    if line_v18.get("tax_line_id"):
                        # Si es línea de impuesto, verificar que coincida el impuesto mapeado
                        if not line_v13.get("tax_line_id"):
                            continue
                        tax_v18_id = get_tax_v18_id(
                            mappings, line_v13["tax_line_id"][0]
                        )
                        if tax_v18_id != line_v18["tax_line_id"][0]:
                            continue

                    match = line_v13
                    break

                if match:
                    odoo_v18.write(
                        "account.move.line", [line_v18["id"]], {"x_v13_id": match["id"]}
                    )
                    # Quitar de la lista para evitar doble asignación (aunque difícil si montos son iguales)
                    other_lines_v13.remove(match)

        # Registrar en migration.tracking
        tracking_vals = {
            "name": f"account.move:{invoice_v13['id']}",
            "model_name": "account.move",
            "v13_id": invoice_v13["id"],
            "v18_id": new_invoice_id,
        }
        odoo_v18.execute("migration.tracking", "create", [tracking_vals])

        return new_invoice_id, None

    except Exception as e:
        return None, str(e)


def migrate_invoices():
    """Migra todas las facturas de 2026."""
    print("=" * 70)
    print("MIGRACIÓN DE FACTURAS 2026")
    print("=" * 70)
    print(f"Fecha inicio: {MIGRATION_START_DATE}")
    print(f"Company ID: {COMPANY_ID}")

    # Cargar mapeos
    mappings = load_mappings()
    print(f"\nMapeos cargados desde {MAPPINGS_FILE}")

    # Contar facturas a migrar
    domain = [
        ("company_id", "=", COMPANY_ID),
        ("state", "=", "posted"),
        ("date", ">=", MIGRATION_START_DATE),
        ("type", "in", ["out_invoice", "in_invoice", "out_refund", "in_refund"]),
    ]

    total = odoo_v13.search_count("account.move", domain)
    print(f"\nFacturas a migrar: {total}")

    if total == 0:
        print("No hay facturas para migrar.")
        return

    # Verificar cuáles ya están migradas
    already_migrated = odoo_v18.search_read(
        "migration.tracking", [("model_name", "=", "account.move")], fields=["v13_id"]
    )
    migrated_v13_ids = {m["v13_id"] for m in already_migrated}
    print(f"Ya migradas: {len(migrated_v13_ids)}")

    migrated = 0
    skipped = 0
    errors = []

    # Procesar en lotes
    for offset in range(0, total, BATCH_SIZE):
        batch_num = (offset // BATCH_SIZE) + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"\n[Lote {batch_num}/{total_batches}] Procesando...")

        invoices = odoo_v13.search_read(
            "account.move",
            domain,
            fields=[
                "id",
                "name",
                "ref",
                "type",
                "state",
                "partner_id",
                "journal_id",
                "currency_id",
                "date",
                "invoice_date",
                "narration",
            ],
            offset=offset,
            limit=BATCH_SIZE,
        )

        for invoice in invoices:
            if invoice["id"] in migrated_v13_ids:
                skipped += 1
                continue

            v18_id, error = migrate_invoice(invoice, mappings)

            if v18_id:
                migrated += 1
                print(f"  ✓ {invoice['name']} -> v18 ID: {v18_id}")
            else:
                errors.append(
                    {"v13_id": invoice["id"], "name": invoice["name"], "error": error}
                )
                print(f"  ✗ {invoice['name']}: {error}")

    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Total facturas: {total}")
    print(f"Migradas: {migrated}")
    print(f"Ya existían: {skipped}")
    print(f"Errores: {len(errors)}")

    if errors:
        print("\nPrimeros 10 errores:")
        for err in errors[:10]:
            print(f"  - [{err['v13_id']}] {err['name']}: {err['error']}")

    return {"migrated": migrated, "skipped": skipped, "errors": errors}


if __name__ == "__main__":
    migrate_invoices()
