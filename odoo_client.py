import xmlrpc.client
from typing import Any, Optional


class OdooClientReadOnlyError(Exception):
    """Excepción cuando se intenta modificar datos en un cliente de solo lectura."""
    pass


class OdooClient:
    """
    Cliente para conectarse a Odoo vía XML-RPC.
    
    Autor: andyengit
    Mantenedor: andyengit
    """
    
    def __init__(
        self,
        url: str,
        db: str,
        username: str,
        password: str,
        readonly: bool = False
    ):
        """
        Inicializa el cliente de Odoo.
        
        Args:
            url: URL del servidor Odoo (ej: http://localhost:8069)
            db: Nombre de la base de datos
            username: Usuario de Odoo
            password: Contraseña del usuario
            readonly: Si es True, bloquea operaciones de escritura (create, write, unlink)
        """
        self.url = url.rstrip('/')
        self.db = db
        self.username = username
        self.password = password
        self.readonly = readonly
        self.uid: Optional[int] = None
        
        self._common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
        self._models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
    
    def authenticate(self) -> int:
        """
        Autentica al usuario y retorna el UID.
        
        Returns:
            UID del usuario autenticado
            
        Raises:
            Exception: Si la autenticación falla
        """
        self.uid = self._common.authenticate(
            self.db, self.username, self.password, {}
        )
        if not self.uid:
            raise Exception(
                f"Error de autenticación en {self.url} con usuario {self.username}"
            )
        return self.uid
    
    def version(self) -> dict:
        """Retorna información de la versión de Odoo."""
        return self._common.version()
    
    def _ensure_authenticated(self):
        """Asegura que el cliente esté autenticado."""
        if self.uid is None:
            self.authenticate()
    
    def _check_readonly(self, method: str):
        """Verifica si la operación está permitida en modo readonly."""
        write_methods = ['create', 'write', 'unlink', 'copy']
        if self.readonly and method in write_methods:
            raise OdooClientReadOnlyError(
                f"Operación '{method}' no permitida: cliente configurado como solo lectura"
            )
    
    def execute(
        self,
        model: str,
        method: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Ejecuta un método en un modelo de Odoo.
        
        Args:
            model: Nombre del modelo (ej: 'res.partner')
            method: Método a ejecutar (ej: 'search', 'read', 'create')
            *args: Argumentos posicionales
            **kwargs: Argumentos de palabra clave
            
        Returns:
            Resultado de la operación
        """
        self._ensure_authenticated()
        self._check_readonly(method)
        
        return self._models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model,
            method,
            args,
            kwargs
        )
    
    def search(
        self,
        model: str,
        domain: list,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None
    ) -> list:
        """
        Busca registros que coincidan con el dominio.
        
        Args:
            model: Nombre del modelo
            domain: Dominio de búsqueda
            offset: Número de registros a saltar
            limit: Número máximo de registros a retornar
            order: Ordenamiento (ej: 'name asc, id desc')
            
        Returns:
            Lista de IDs
        """
        kwargs = {'offset': offset}
        if limit is not None:
            kwargs['limit'] = limit
        if order is not None:
            kwargs['order'] = order
        
        return self.execute(model, 'search', domain, **kwargs)
    
    def search_count(self, model: str, domain: list) -> int:
        """
        Cuenta registros que coincidan con el dominio.
        
        Args:
            model: Nombre del modelo
            domain: Dominio de búsqueda
            
        Returns:
            Cantidad de registros
        """
        return self.execute(model, 'search_count', domain)
    
    def read(
        self,
        model: str,
        ids: list,
        fields: Optional[list] = None
    ) -> list:
        """
        Lee registros por sus IDs.
        
        Args:
            model: Nombre del modelo
            ids: Lista de IDs a leer
            fields: Lista de campos a retornar (None = todos)
            
        Returns:
            Lista de diccionarios con los datos
        """
        kwargs = {}
        if fields is not None:
            kwargs['fields'] = fields
        
        return self.execute(model, 'read', ids, **kwargs)
    
    def search_read(
        self,
        model: str,
        domain: list,
        fields: Optional[list] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        order: Optional[str] = None
    ) -> list:
        """
        Busca y lee registros en una sola llamada.
        
        Args:
            model: Nombre del modelo
            domain: Dominio de búsqueda
            fields: Lista de campos a retornar
            offset: Número de registros a saltar
            limit: Número máximo de registros
            order: Ordenamiento
            
        Returns:
            Lista de diccionarios con los datos
        """
        kwargs = {'offset': offset}
        if fields is not None:
            kwargs['fields'] = fields
        if limit is not None:
            kwargs['limit'] = limit
        if order is not None:
            kwargs['order'] = order
        
        return self.execute(model, 'search_read', domain, **kwargs)
    
    def create(self, model: str, values: dict) -> int:
        """
        Crea un nuevo registro.
        
        Args:
            model: Nombre del modelo
            values: Diccionario con los valores del registro
            
        Returns:
            ID del registro creado
            
        Raises:
            OdooClientReadOnlyError: Si el cliente es de solo lectura
        """
        return self.execute(model, 'create', values)
    
    def write(self, model: str, ids: list, values: dict) -> bool:
        """
        Actualiza registros existentes.
        
        Args:
            model: Nombre del modelo
            ids: Lista de IDs a actualizar
            values: Diccionario con los valores a actualizar
            
        Returns:
            True si la operación fue exitosa
            
        Raises:
            OdooClientReadOnlyError: Si el cliente es de solo lectura
        """
        return self.execute(model, 'write', ids, values)
    
    def unlink(self, model: str, ids: list) -> bool:
        """
        Elimina registros.
        
        Args:
            model: Nombre del modelo
            ids: Lista de IDs a eliminar
            
        Returns:
            True si la operación fue exitosa
            
        Raises:
            OdooClientReadOnlyError: Si el cliente es de solo lectura
        """
        return self.execute(model, 'unlink', ids)
    
    def fields_get(
        self,
        model: str,
        attributes: Optional[list] = None
    ) -> dict:
        """
        Obtiene la definición de campos de un modelo.
        
        Args:
            model: Nombre del modelo
            attributes: Lista de atributos a retornar (ej: ['string', 'type'])
            
        Returns:
            Diccionario con la definición de campos
        """
        kwargs = {}
        if attributes is not None:
            kwargs['attributes'] = attributes
        
        return self.execute(model, 'fields_get', [], **kwargs)
    
    def __repr__(self) -> str:
        mode = "readonly" if self.readonly else "read/write"
        return f"<OdooClient {self.url} db={self.db} user={self.username} mode={mode}>"
