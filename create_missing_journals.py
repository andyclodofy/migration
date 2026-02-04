"""
Crea los diarios (journals) faltantes en v18 basándose en v13.
"""

import os
import json
from dotenv import load_dotenv
from connections import odoo_v13, odoo_v18

load_dotenv()

COMPANY_ID = int(os.getenv("COMPANY_ID", 1))
MAPPINGS_FILE = "mappings.json"


def load_mappings():
    if os.path.exists(MAPPINGS_FILE):
        with open(MAPPINGS_FILE, "r") as f:
            return json.load(f)
    return {"taxes": {}, "accounts": {}, "journals": {}}


def save_mappings(mappings):
    with open(MAPPINGS_FILE, "w") as f:
        json.dump(mappings, f, indent=2, ensure_ascii=False)


def get_mapped_account_id(mappings, v13_account_id):
    if not v13_account_id:
        return False

    # Buscar en mapeo explícito
    acc_map = mappings.get("accounts", {}).get(str(v13_account_id))
    if acc_map:
        return acc_map["v18_id"]

    # Si no está en mapeo, intentar buscar la cuenta en v13 para obtener su código
    # y buscar ese código en v18 (fallback)
    # Nota: Esto es costoso si se hace mucho, pero para pocos diarios está bien.
    try:
        acc_v13 = odoo_v13.read("account.account", [v13_account_id], ["code"])
        if acc_v13:
            code = acc_v13[0]["code"]
            acc_v18 = odoo_v18.search_read(
                "account.account", [("code", "=", code)], ["id"], limit=1
            )
            if acc_v18:
                return acc_v18[0]["id"]
    except Exception:
        pass

    return False


def main():
    print("=" * 70)
    print("CREACIÓN DE DIARIOS FALTANTES EN V18")
    print("=" * 70)

    mappings = load_mappings()
    if "journals" not in mappings:
        mappings["journals"] = {}

    # 1. Obtener diarios de v13
    print("Leyendo diarios de v13...")
    journals_v13 = odoo_v13.search_read(
        "account.journal",
        [("company_id", "=", COMPANY_ID)],
        fields=[
            "id",
            "name",
            "code",
            "type",
            "default_debit_account_id",
            "default_credit_account_id",
            "sequence_number_next",
        ],
    )

    # 2. Obtener diarios de v18 (para verificar existencia por código)
    print("Leyendo diarios de v18...")
    journals_v18 = odoo_v18.search_read(
        "account.journal", [("company_id", "=", COMPANY_ID)], fields=["id", "code"]
    )
    v18_codes = {j["code"] for j in journals_v18}

    # 3. Identificar faltantes
    missing = []
    for j in journals_v13:
        if j["code"] not in v18_codes:
            missing.append(j)

    print(f"\nDiarios en v13: {len(journals_v13)}")
    print(f"Diarios en v18: {len(journals_v18)}")
    print(f"Faltantes: {len(missing)}")

    if not missing:
        print("\nNo fían diarios por crear.")
        return

    print("\nProcesando diarios faltantes:")
    created_count = 0

    for j in missing:
        print(f"\n  Procesando [{j['id']}] {j['name']} ({j['code']})...")

        # Preparar valores
        vals = {
            "name": j["name"],
            "code": j["code"],
            "type": j["type"],
        }

        # Intentar mapear cuentas por defecto
        # Nota: En v13 es default_debit/credit_account_id
        # En v18 para bank/cash suele ser default_account_id (o suspense, etc)
        # Para sale/purchase es default_account_id

        # Estrategia simple: intentar mapear lo que haya
        debit_acc_id = get_mapped_account_id(
            mappings,
            j["default_debit_account_id"][0]
            if j["default_debit_account_id"]
            else False,
        )
        credit_acc_id = get_mapped_account_id(
            mappings,
            j["default_credit_account_id"][0]
            if j["default_credit_account_id"]
            else False,
        )

        # En v18, 'default_account_id' se usa a menudo para ambos si son el mismo,
        # o 'default_account_id' es la cuenta principal del diario.
        if debit_acc_id:
            vals["default_account_id"] = debit_acc_id
        elif credit_acc_id:
            vals["default_account_id"] = credit_acc_id

        try:
            new_id = odoo_v18.create("account.journal", vals)
            print(f"    ✓ Creado con ID: {new_id}")

            # Actualizar mapeo
            mappings["journals"][str(j["id"])] = {
                "v13_id": j["id"],
                "v18_id": new_id,
                "code": j["code"],
                "name": j["name"],
            }
            created_count += 1

        except Exception as e:
            print(f"    ✗ Error al crear: {e}")

    # Guardar cambios
    if created_count > 0:
        save_mappings(mappings)
        print(f"\n✓ Se crearon {created_count} diarios y se actualizó {MAPPINGS_FILE}")
    else:
        print("\nNo se crearon diarios.")


if __name__ == "__main__":
    main()
