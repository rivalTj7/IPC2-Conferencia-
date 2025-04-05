# api/permissions.py
from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permiso personalizado que permite acceso solo al propietario de un objeto o a administradores.
    """
    
    def has_object_permission(self, request, view, obj):
        # El administrador o auditor siempre tiene permisos
        if request.user.role in ['ADMIN', 'AUDITOR']:
            return True
            
        # Para objetos tipo DocumentoTributario
        if hasattr(obj, 'emisor'):
            # El propietario (emisor) tiene permisos
            return hasattr(request.user, 'contribuyente') and obj.emisor == request.user.contribuyente
            
        # Para cualquier otro tipo de objeto, verificar si tiene un atributo usuario
        if hasattr(obj, 'usuario'):
            return obj.usuario == request.user
            
        # Por defecto, denegar permiso
        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permiso personalizado que permite acceso de lectura a todos los usuarios autenticados,
    pero sólo permite escritura a administradores.
    """
    
    def has_permission(self, request, view):
        # Permitir solicitudes GET, HEAD, OPTIONS a cualquier usuario autenticado
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated
            
        # Escritura solo para administradores
        return request.user and request.user.is_authenticated and request.user.role == 'ADMIN'