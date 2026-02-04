"""
Utilidades para la migración de datos entre Odoo v13 y v18.

Autor: andyengit
Mantenedor: andyengit
"""

from typing import Optional
from functools import lru_cache
from connections import odoo_v13, odoo_v18


# Mapeo de modelos que cambiaron de nombre entre v13 y v18
# Clave: nombre en v13, Valor: nombre en v18
MODEL_MAP_V13_TO_V18 = {
    "contract.contract": "sale.subscription",
}

# Mapeo inverso: v18 -> v13
MODEL_MAP_V18_TO_V13 = {v: k for k, v in MODEL_MAP_V13_TO_V18.items()}


def get_v18_model(v13_model: str) -> str:
    """Convierte el nombre de un modelo de v13 a v18."""
    return MODEL_MAP_V13_TO_V18.get(v13_model, v13_model)


def get_v13_model(v18_model: str) -> str:
    """Convierte el nombre de un modelo de v18 a v13."""
    return MODEL_MAP_V18_TO_V13.get(v18_model, v18_model)


@lru_cache(maxsize=None)
def get_v18_id(v13_id: int, model: Optional[str] = None) -> Optional[int]:
    """
    Busca el ID correspondiente en Odoo v18 a partir de un ID de v13.

    Consulta la tabla 'migration.tracking' en Odoo v18 para encontrar
    el registro migrado correspondiente.

    Nota: El modelo se convierte automáticamente al nombre de v18 ya que
    migration.tracking guarda los nombres de modelo de v18.
    (ej: 'contract.contract' -> 'sale.subscription')

    Args:
        v13_id: ID del registro en Odoo v13
        model: (Opcional) Nombre del modelo (v13 o v18) para filtrar la búsqueda.
               Si no se proporciona, busca solo por v13_id.

    Returns:
        El v18_id si se encuentra el registro, None en caso contrario.

    Example:
        >>> v18_partner_id = get_v18_id(123, 'contract.contract')
        >>> if v18_partner_id:
        ...     print(f"El registro migrado tiene ID {v18_partner_id} en v18")
        ... else:
        ...     print("El registro no ha sido migrado")
    """
    domain = [("v13_id", "=", v13_id)]

    if model:
        v18_model = get_v18_model(model)
        domain.append(("model_name", "=", v18_model))

    result = odoo_v18.search_read(
        "migration.tracking", domain, fields=["v18_id"], limit=1
    )

    if result:
        return result[0]["v18_id"]

    return None


@lru_cache(maxsize=None)
def get_v13_id(v18_id: int, model: Optional[str] = None) -> Optional[int]:
    """
    Busca el ID correspondiente en Odoo v13 a partir de un ID de v18.

    Consulta la tabla 'migration.tracking' en Odoo v18 para encontrar
    el ID original del registro en v13.

    Args:
        v18_id: ID del registro en Odoo v18
        model: (Opcional) Nombre del modelo (v13 o v18) para filtrar la búsqueda.

    Returns:
        El v13_id si se encuentra el registro, None en caso contrario.
    """
    domain = [("v18_id", "=", v18_id)]

    if model:
        v18_model = get_v18_model(model)
        domain.append(("model_name", "=", v18_model))

    result = odoo_v18.search_read(
        "migration.tracking", domain, fields=["v13_id"], limit=1
    )

    if result:
        return result[0]["v13_id"]

    return None


def is_migrated(v13_id: int, model: Optional[str] = None) -> bool:
    """
    Verifica si un registro de v13 ya fue migrado a v18.

    Args:
        v13_id: ID del registro en Odoo v13
        model: (Opcional) Nombre del modelo para filtrar la búsqueda.

    Returns:
        True si el registro ya fue migrado, False en caso contrario.
    """
    return get_v18_id(v13_id, model) is not None


def get_v18_record(
    v13_id: int, model_name: str, fields: Optional[list] = None
) -> Optional[dict]:
    """
    Obtiene el registro completo de v18 a partir de un ID de v13.

    Busca en 'migration.tracking' el v18_id correspondiente y luego
    lee el registro del modelo especificado con los campos solicitados.

    Nota: Maneja automáticamente el mapeo de modelos (ej: contract.contract -> sale.subscription)

    Args:
        v13_id: ID del registro en Odoo v13
        model_name: Nombre del modelo en v13 (ej: 'res.partner', 'contract.contract')
        fields: Lista de campos a obtener. Si es None, retorna todos los campos.

    Returns:
        Diccionario con los datos del registro en v18, None si no existe.

    Example:
        >>> partner = get_v18_record(123, 'res.partner', ['name', 'email', 'phone'])
        >>> if partner:
        ...     print(f"Partner: {partner['name']}")
    """
    v18_id = get_v18_id(v13_id, model_name)

    if not v18_id:
        return None

    v18_model = get_v18_model(model_name)
    result = odoo_v18.read(v18_model, [v18_id], fields)

    if result:
        return result[0]

    return None


def get_v13_record(
    v13_id: int, model_name: str, fields: Optional[list] = None
) -> Optional[dict]:
    """
    Obtiene el registro de v13 con los campos especificados.

    Args:
        v13_id: ID del registro en Odoo v13
        model_name: Nombre del modelo (ej: 'res.partner')
        fields: Lista de campos a obtener. Si es None, retorna todos los campos.

    Returns:
        Diccionario con los datos del registro en v13, None si no existe.

    Example:
        >>> partner = get_v13_record(123, 'res.partner', ['name', 'email', 'phone'])
        >>> if partner:
        ...     print(f"Partner en v13: {partner['name']}")
    """
    result = odoo_v13.read(model_name, [v13_id], fields)

    if result:
        return result[0]

    return None
