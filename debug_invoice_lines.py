import os
import json
from dotenv import load_dotenv
from connections import odoo_v13, odoo_v18
from migrate_invoices import load_mappings, get_account_v18_id, get_tax_v18_id

load_dotenv()


def debug_invoice(invoice_name):
    print(f"DEBUGGING INVOICE: {invoice_name}")

    # 1. Get v13 Invoice
    invoice_v13 = odoo_v13.search_read(
        "account.move", [("name", "=", invoice_name)], fields=["id", "name"]
    )
    if not invoice_v13:
        print("Invoice not found in v13")
        return
    invoice_v13 = invoice_v13[0]
    print(f"v13 ID: {invoice_v13['id']}")

    # 2. Get v18 Invoice
    invoice_v18 = odoo_v18.search_read(
        "account.move", [("name", "=", invoice_name)], fields=["id", "name"]
    )
    if not invoice_v18:
        print("Invoice not found in v18")
        return
    invoice_v18 = invoice_v18[0]
    print(f"v18 ID: {invoice_v18['id']}")

    # 3. Get v13 Lines (excluding invoice tab for matching candidates)
    other_lines_v13 = odoo_v13.search_read(
        "account.move.line",
        [
            ("move_id", "=", invoice_v13["id"]),
            ("exclude_from_invoice_tab", "=", True),
        ],
        fields=["name", "account_id", "debit", "credit", "tax_line_id"],
    )
    print(f"\nv13 Candidate Lines ({len(other_lines_v13)}):")
    for l in other_lines_v13:
        print(
            f"  - [{l['id']}] {l['name']} | Acc: {l['account_id'][1]} ({l['account_id'][0]}) | Dr: {l['debit']} | Cr: {l['credit']} | TaxLine: {l['tax_line_id']}"
        )

    # 4. Get v18 Lines (missing x_v13_id)
    lines_v18 = odoo_v18.search_read(
        "account.move.line",
        [("move_id", "=", invoice_v18["id"]), ("x_v13_id", "=", False)],
        fields=["name", "account_id", "debit", "credit", "tax_line_id"],
    )
    print(f"\nv18 Lines missing x_v13_id ({len(lines_v18)}):")
    for l in lines_v18:
        print(
            f"  - [{l['id']}] {l['name']} | AccID: {l['account_id'][0]} ({l['account_id'][1]}) | Dr: {l['debit']} | Cr: {l['credit']} | TaxLine: {l['tax_line_id']}"
        )

    # 5. Simulate Matching
    print("\nSIMULATING MATCHING:")
    mappings = load_mappings()

    for line_v18 in lines_v18:
        print(
            f"\nMatching v18 Line [{line_v18['id']}] Dr:{line_v18['debit']} Cr:{line_v18['credit']} Acc:{line_v18['account_id'][1]}"
        )
        match = None
        for line_v13 in other_lines_v13:
            print(
                f"  vs v13 Line [{line_v13['id']}] Dr:{line_v13['debit']} Cr:{line_v13['credit']} Acc:{line_v13['account_id'][1]}"
            )

            # Check Account
            acc_v18_id = get_account_v18_id(mappings, line_v13["account_id"][0])
            if acc_v18_id != line_v18["account_id"][0]:
                print(
                    f"    -> Mismatch Account: Expected {acc_v18_id} got {line_v18['account_id'][0]}"
                )
                continue

            # Check Amount
            if (
                abs(line_v13["debit"] - line_v18["debit"]) > 0.01
                or abs(line_v13["credit"] - line_v18["credit"]) > 0.01
            ):
                print(f"    -> Mismatch Amount")
                continue

            # Check Tax
            if line_v18.get("tax_line_id"):
                if not line_v13.get("tax_line_id"):
                    print(f"    -> Mismatch Tax: v18 has tax, v13 none")
                    continue
                tax_v18_id = get_tax_v18_id(mappings, line_v13["tax_line_id"][0])
                if tax_v18_id != line_v18["tax_line_id"][0]:
                    print(
                        f"    -> Mismatch TaxID: Expected {tax_v18_id} got {line_v18['tax_line_id'][0]}"
                    )
                    continue

            print("    -> MATCH FOUND!")
            match = line_v13
            break

        if match:
            other_lines_v13.remove(match)


if __name__ == "__main__":
    debug_invoice("VEN/058611")
