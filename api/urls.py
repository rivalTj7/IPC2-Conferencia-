# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    DocumentoTributarioViewSet, ContribuyenteViewSet,
    TipoDocumentoViewSet, AutorizacionViewSet,
    EstadisticaDiariaViewSet, VerificarDocumentoAPIView,
    EstadisticasGeneralesAPIView
)

# Crear router para viewsets
router = DefaultRouter()
router.register(r'documentos', DocumentoTributarioViewSet, basename='documento')
router.register(r'contribuyentes', ContribuyenteViewSet)
router.register(r'tipos-documento', TipoDocumentoViewSet)
router.register(r'autorizaciones', AutorizacionViewSet, basename='autorizacion')
router.register(r'estadisticas', EstadisticaDiariaViewSet)

urlpatterns = [
    # Incluir URLs del router
    path('', include(router.urls)),
    
    # Endpoints para autenticación con JWT
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Endpoints adicionales
    path('verificar-documento/', VerificarDocumentoAPIView.as_view(), name='verificar-documento'),
    path('estadisticas-generales/', EstadisticasGeneralesAPIView.as_view(), name='estadisticas-generales'),
]