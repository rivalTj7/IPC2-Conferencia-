# sigte/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView, TemplateView
from rest_framework.documentation import include_docs_urls

urlpatterns = [
    # Admin de Django
    path('admin/', admin.site.urls),
    
    # Página de inicio (redirecciona al dashboard)
    path('', RedirectView.as_view(pattern_name='dashboard'), name='home'),
    
    # Apps del proyecto
    path('accounts/', include('accounts.urls')),
    path('emisor/', include('emisor.urls')),
    path('autoriza/', include('autoriza.urls')),
    path('consulta/', include('consulta.urls')),
    
    # Dashboard
    path('dashboard/', include('core.urls')),
    
    # API
    path('api/v1/', include('api.urls')),
    
    # Documentación de API
    path('api/docs/', include_docs_urls(title='SIGTE API')),
    
    # Autenticación de Django (para desarrollo)
    path('accounts/', include('django.contrib.auth.urls')),
    
    # Página de información del proyecto
    path('acerca/', TemplateView.as_view(template_name='acerca.html'), name='acerca'),
]

# Servir archivos estáticos y media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# emisor/urls.py
from django.urls import path
from .views import (
    DocumentoListView, DocumentoDetailView, DocumentoCreateView,
    DocumentoBorradorCreateView, DocumentoBorradorUpdateView,
    DocumentoBorradorEmitirView, EstablecimientoListView,
    EstablecimientoCreateView, EstablecimientoUpdateView,
    ContribuyenteDetailView
)

app_name = 'emisor'

urlpatterns = [
    # Documentos
    path('documentos/', DocumentoListView.as_view(), name='documento_list'),
    path('documentos/<int:pk>/', DocumentoDetailView.as_view(), name='documento_detail'),
    path('documentos/crear/', DocumentoCreateView.as_view(), name='documento_create'),
    
    # Borradores
    path('borradores/crear/', DocumentoBorradorCreateView.as_view(), name='documento_borrador_create'),
    path('borradores/<int:pk>/editar/', DocumentoBorradorUpdateView.as_view(), name='documento_borrador_update'),
    path('borradores/<int:pk>/emitir/', DocumentoBorradorEmitirView.as_view(), name='documento_borrador_emitir'),
    
    # Establecimientos
    path('establecimientos/', EstablecimientoListView.as_view(), name='establecimiento_list'),
    path('establecimientos/crear/', EstablecimientoCreateView.as_view(), name='establecimiento_create'),
    path('establecimientos/<int:pk>/editar/', EstablecimientoUpdateView.as_view(), name='establecimiento_update'),
    
    # Contribuyente
    path('perfil/', ContribuyenteDetailView.as_view(), name='contribuyente_detail'),
]


# consulta/urls.py
from django.urls import path
from .views import (
    DashboardView, EstadisticasView, ReporteIvaView,
    ReporteRangoFechasView, ExportarCsvView, GenerarPdfView
)

app_name = 'consulta'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('estadisticas/', EstadisticasView.as_view(), name='estadisticas'),
    path('reporte-iva/', ReporteIvaView.as_view(), name='reporte_iva'),
    path('reporte-rango-fechas/', ReporteRangoFechasView.as_view(), name='reporte_rango_fechas'),
    path('exportar-csv/', ExportarCsvView.as_view(), name='exportar_csv'),
    path('generar-pdf/', GenerarPdfView.as_view(), name='generar_pdf'),
]


# accounts/urls.py
from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    LoginView, RegisterView, ProfileView,
    PasswordChangeView, PasswordResetView,
    PasswordResetConfirmView
)

app_name = 'accounts'

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('password-change/', PasswordChangeView.as_view(), name='password_change'),
    path('password-reset/', PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]


# core/urls.py
from django.urls import path
from .views import DashboardView

app_name = 'core'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
]