"""
Conexiones preconfiguradas a Odoo v13 y v18.

Autor: andyengit
Mantenedor: andyengit
"""
import os
from dotenv import load_dotenv
from odoo_client import OdooClient, OdooClientReadOnlyError

load_dotenv()


def get_odoo_v13() -> OdooClient:
    """
    Retorna un cliente de Odoo v13 configurado como SOLO LECTURA.
    
    Este cliente está diseñado para consultar datos del sistema origen,
    no permite operaciones de escritura (create, write, unlink).
    
    Returns:
        OdooClient configurado para Odoo v13 en modo readonly
    """
    return OdooClient(
        url=os.getenv('V13_URL', 'http://localhost:8013'),
        db=os.getenv('V13_DB', 'odoo13'),
        username=os.getenv('V13_USERNAME', 'admin'),
        password=os.getenv('V13_PASSWORD', 'admin'),
        readonly=True
    )


def get_odoo_v18() -> OdooClient:
    """
    Retorna un cliente de Odoo v18 con permisos de lectura/escritura.
    
    Este cliente está diseñado para el sistema destino,
    permite todas las operaciones incluyendo escritura.
    
    Returns:
        OdooClient configurado para Odoo v18 con permisos completos
    """
    return OdooClient(
        url=os.getenv('V18_URL', 'http://localhost:8018'),
        db=os.getenv('V18_DB', 'odoo18'),
        username=os.getenv('V18_USERNAME', 'admin'),
        password=os.getenv('V18_PASSWORD', 'admin'),
        readonly=False
    )


odoo_v13 = get_odoo_v13()
odoo_v18 = get_odoo_v18()

__all__ = [
    'odoo_v13',
    'odoo_v18',
    'get_odoo_v13',
    'get_odoo_v18',
    'OdooClient',
    'OdooClientReadOnlyError'
]
