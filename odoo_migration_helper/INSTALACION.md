# 📦 Instalación del Módulo Migration Helper

## 🎯 Objetivo

Este módulo es necesario para crear facturas en Odoo v18 via XML-RPC durante la migración desde v13.

## 📋 Requisitos Previos

- Acceso al servidor de Odoo v18
- Permisos para instalar módulos
- Usuario con permisos de administrador

## 🚀 Pasos de Instalación

### Opción 1: Instalación en Servidor Local (localhost)

Si estás usando Odoo v18 en localhost:

```bash
# 1. Copiar el módulo a la carpeta de addons
sudo cp -r /Users/andy/dev/xmlrpc/d101subs/odoo_migration_helper /path/to/odoo/addons/

# Ejemplo si Odoo está en ~/odoo:
cp -r /Users/andy/dev/xmlrpc/d101subs/odoo_migration_helper ~/odoo/addons/

# 2. Reiniciar el servidor Odoo
# Si usas systemd:
sudo systemctl restart odoo

# Si usas el servidor de desarrollo:
cd /path/to/odoo
./odoo-bin -u odoo_migration_helper -d d101
```

### Opción 2: Instalación via UI de Odoo

1. **Copiar el módulo** a la carpeta de addons de Odoo
2. **Ir a Odoo** → Aplicaciones
3. **Actualizar Lista de Aplicaciones**:
   - Activar modo desarrollador si no está activo
   - Apps → Update Apps List
4. **Buscar** "Migration Helper" o "odoo_migration_helper"
5. **Instalar** el módulo

### Opción 3: Instalación via Línea de Comandos

```bash
# Actualizar la lista de módulos e instalar
cd /path/to/odoo
./odoo-bin -d d101 -i odoo_migration_helper --stop-after-init
```

## ✅ Verificar la Instalación

Una vez instalado, ejecutar el script de prueba:

```bash
cd /Users/andy/dev/xmlrpc/d101subs/odoo_migration_helper
python3 test_module.py
```

Si todo está correcto, deberías ver:

```
======================================================================
✅ TODAS LAS PRUEBAS PASARON
======================================================================

El módulo está listo para usar en la migración de facturas.
```

## 🔧 Solución de Problemas

### Error: "Object migration.helper doesn't exist"

**Causa**: El módulo no está instalado o no se actualizó la lista de módulos.

**Solución**:
1. Verificar que el módulo esté en la carpeta de addons
2. Actualizar la lista de módulos en Odoo UI
3. Instalar el módulo desde Apps

### Error: "Module not found"

**Causa**: La carpeta del módulo no está en el path de addons de Odoo.

**Solución**:
1. Verificar la ubicación de la carpeta addons de Odoo:
   ```bash
   grep addons_path /etc/odoo/odoo.conf
   ```
2. Copiar el módulo a esa ubicación
3. Reiniciar Odoo

### Error de Permisos

**Causa**: El usuario de Odoo no tiene permisos para leer el módulo.

**Solución**:
```bash
sudo chown -R odoo:odoo /path/to/odoo/addons/odoo_migration_helper
sudo chmod -R 755 /path/to/odoo/addons/odoo_migration_helper
```

## 📞 Soporte

Si tienes problemas con la instalación:

1. Verificar los logs de Odoo: `/var/log/odoo/odoo-server.log`
2. Verificar que el módulo tenga la estructura correcta:
   ```
   odoo_migration_helper/
   ├── __init__.py
   ├── __manifest__.py
   ├── models/
   │   ├── __init__.py
   │   └── migration_helper.py
   └── README.md
   ```
3. Verificar que Odoo pueda ver el módulo:
   ```bash
   ./odoo-bin -d d101 --test-enable --stop-after-init
   ```

## ⏭️ Siguiente Paso

Una vez instalado el módulo, continuar con la migración de facturas ejecutando:

```bash
cd /Users/andy/dev/xmlrpc/d101subs/invoice_migration
python3 invoice_creator.py
```
