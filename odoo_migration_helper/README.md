# Migration Helper - Invoice Creation via XML-RPC

## Descripción

Este módulo proporciona métodos compatibles con XML-RPC para crear facturas en Odoo v18.

En Odoo v18, el método `account.move.create()` fue modificado con el decorador `@api.model_create_multi`, lo que cambia su firma y lo hace incompatible con llamadas XML-RPC directas. Este módulo proporciona métodos wrapper simples que pueden ser llamados via XML-RPC.

## Instalación

1. Copiar este módulo a la carpeta de addons de Odoo v18
2. Actualizar la lista de módulos
3. Instalar el módulo "Migration Helper - Invoice Creation via XML-RPC"

```bash
# Copiar el módulo
cp -r odoo_migration_helper /path/to/odoo/addons/

# Reiniciar Odoo
sudo systemctl restart odoo

# O si usas el servidor de desarrollo
./odoo-bin -u odoo_migration_helper -d tu_database
```

## Uso

### Método: `create_invoice_xmlrpc`

Crea una única factura y retorna su ID.

```python
import xmlrpc.client

url = 'http://localhost:8069'
db = 'tu_database'
username = 'admin'
password = 'admin'

# Autenticación
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

# Conexión al modelo
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Datos de la factura
invoice_vals = {
    'move_type': 'out_invoice',
    'partner_id': 1,
    'invoice_date': '2026-01-28',
    'company_id': 1,
    'invoice_line_ids': [(0, 0, {
        'product_id': 1,
        'quantity': 1,
        'price_unit': 100.0,
        'name': 'Producto de prueba',
        'tax_ids': [(6, 0, [1])],
    })],
}

# Crear factura
invoice_id = models.execute_kw(
    db, uid, password,
    'migration.helper', 'create_invoice_xmlrpc',
    [invoice_vals], {}
)

print(f"Factura creada con ID: {invoice_id}")
```

### Método: `create_invoices_xmlrpc`

Crea múltiples facturas en una sola llamada (más eficiente).

```python
invoices_vals = [
    {
        'move_type': 'out_invoice',
        'partner_id': 1,
        'invoice_date': '2026-01-28',
        'company_id': 1,
    },
    {
        'move_type': 'out_invoice',
        'partner_id': 2,
        'invoice_date': '2026-01-28',
        'company_id': 1,
    },
]

invoice_ids = models.execute_kw(
    db, uid, password,
    'migration.helper', 'create_invoices_xmlrpc',
    [invoices_vals], {}
)

print(f"Facturas creadas: {invoice_ids}")
```

### Método: `test_connection`

Verifica que el módulo esté instalado y accesible.

```python
result = models.execute_kw(
    db, uid, password,
    'migration.helper', 'test_connection',
    [], {}
)

print(result)
# {'status': 'ok', 'message': 'Migration Helper module is installed and ready', 'model': 'migration.helper'}
```

## Estructura de Datos

### Valores de Factura (`invoice_vals`)

```python
{
    'move_type': 'out_invoice',  # o 'in_invoice', 'out_refund', 'in_refund'
    'partner_id': 1,             # ID del cliente/proveedor
    'invoice_date': '2026-01-28', # Fecha de la factura
    'company_id': 1,             # ID de la compañía
    'journal_id': 1,             # Opcional: ID del diario
    'ref': 'REF-001',            # Opcional: Referencia
    'invoice_line_ids': [        # Líneas de factura
        (0, 0, {
            'product_id': 1,
            'name': 'Descripción del producto',
            'quantity': 1.0,
            'price_unit': 100.0,
            'tax_ids': [(6, 0, [1, 2])],  # IDs de impuestos
            'account_id': 1,      # Opcional: cuenta contable
        }),
    ],
}
```

## Notas Técnicas

- El módulo usa `@api.model` para todos los métodos
- Los métodos retornan tipos primitivos (int, list) en lugar de recordsets
- Compatible con XML-RPC protocol
- No requiere dependencias adicionales más allá de `account`

## Autor

- **Autor:** andyengit
- **Mantenedor:** andyengit
- **Licencia:** LGPL-3

## Versión

- **Versión del Módulo:** 1.0.0
- **Versión de Odoo:** 18.0
