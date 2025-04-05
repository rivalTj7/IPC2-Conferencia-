# api/views.py
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction
from django.utils import timezone

from emisor.models import DocumentoTributario, Contribuyente, TipoDocumento
from autoriza.models import Autorizacion, EstadisticaDiaria
from .serializers import (
    DocumentoTributarioSerializer, ContribuyenteSerializer, 
    TipoDocumentoSerializer, AutorizacionSerializer,
    EstadisticaDiariaSerializer
)
from .permissions import IsOwnerOrAdmin, IsAdminOrReadOnly


class ContribuyenteViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar contribuyentes
    """
    queryset = Contribuyente.objects.all()
    serializer_class = ContribuyenteSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['nit']
    search_fields = ['nit', 'nombre', 'nombre_comercial']


class TipoDocumentoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para consultar tipos de documentos
    """
    queryset = TipoDocumento.objects.filter(activo=True)
    serializer_class = TipoDocumentoSerializer
    permission_classes = [permissions.IsAuthenticated]


class DocumentoTributarioViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar documentos tributarios
    """
    serializer_class = DocumentoTributarioSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'fecha_emision', 'tipo_documento']
    search_fields = ['referencia_interna', 'observaciones', 'receptor__nit', 'receptor__nombre']
    ordering_fields = ['fecha_emision', 'total', 'referencia_interna']
    ordering = ['-fecha_emision']
    
    def get_queryset(self):
        """
        Filtrar documentos según el rol del usuario
        """
        user = self.request.user
        
        # Si es admin o auditor, mostrar todos los documentos
        if user.role in ['ADMIN', 'AUDITOR']:
            return DocumentoTributario.objects.all()
            
        # Si es contribuyente, mostrar solo sus documentos emitidos
        if hasattr(user, 'contribuyente'):
            return DocumentoTributario.objects.filter(emisor=user.contribuyente)
            
        # En cualquier otro caso, no mostrar documentos
        return DocumentoTributario.objects.none()
    
    def perform_create(self, serializer):
        """
        Asignar el emisor al crear un documento
        """
        serializer.save()
    
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def emitir(self, request, pk=None):
        """
        Emitir un documento borrador
        """
        documento = self.get_object()
        
        # Verificar que sea un borrador
        if not documento.es_borrador or documento.estado != DocumentoTributario.ESTADO_BORRADOR:
            return Response(
                {"error": "Solo se pueden emitir documentos en estado borrador"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar cálculos
        es_valido, mensaje = documento.validar_calculos()
        if not es_valido:
            return Response(
                {"error": f"Error en los cálculos: {mensaje}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cambiar estado a emitido
        documento.estado = DocumentoTributario.ESTADO_EMITIDO
        documento.es_borrador = False
        documento.fecha_emision = timezone.now()
        documento.save()
        
        # Crear solicitud de autorización
        from autoriza.services import crear_solicitud_autorizacion
        autorizacion = crear_solicitud_autorizacion(documento)
        
        return Response(
            {"mensaje": "Documento emitido correctamente y enviado para autorización"},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'])
    def autorizacion(self, request, pk=None):
        """
        Obtener información de autorización de un documento
        """
        documento = self.get_object()
        
        try:
            autorizacion = documento.autorizacion
            serializer = AutorizacionSerializer(autorizacion)
            return Response(serializer.data)
        except:
            return Response(
                {"error": "El documento no tiene autorización"},
                status=status.HTTP_404_NOT_FOUND
            )


class AutorizacionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para consultar autorizaciones
    """
    serializer_class = AutorizacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['estado', 'fecha_autorizacion']
    ordering_fields = ['fecha_autorizacion']
    ordering = ['-fecha_autorizacion']
    
    def get_queryset(self):
        """
        Filtrar autorizaciones según el rol del usuario
        """
        user = self.request.user
        
        # Si es admin o auditor, mostrar todas las autorizaciones
        if user.role in ['ADMIN', 'AUDITOR']:
            return Autorizacion.objects.all()
            
        # Si es contribuyente, mostrar solo sus autorizaciones
        if hasattr(user, 'contribuyente'):
            return Autorizacion.objects.filter(documento__emisor=user.contribuyente)
            
        # En cualquier otro caso, no mostrar autorizaciones
        return Autorizacion.objects.none()


class EstadisticaDiariaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para consultar estadísticas diarias
    """
    queryset = EstadisticaDiaria.objects.all()
    serializer_class = EstadisticaDiariaSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['fecha']
    ordering_fields = ['fecha']
    ordering = ['-fecha']


class VerificarDocumentoAPIView(APIView):
    """
    API endpoint para verificar la validez de un documento tributario
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        numero_autorizacion = request.query_params.get('numero_autorizacion')
        nit_emisor = request.query_params.get('nit_emisor')
        
        if not numero_autorizacion or not nit_emisor:
            return Response(
                {"error": "Se requiere número de autorización y NIT del emisor"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Buscar la autorización
            autorizacion = Autorizacion.objects.get(
                numero_autorizacion=numero_autorizacion,
                documento__emisor__nit=nit_emisor,
                estado=Autorizacion.ESTADO_APROBADO
            )
            
            # Obtener datos básicos del documento
            documento = autorizacion.documento
            
            return Response({
                "valido": True,
                "fecha_autorizacion": autorizacion.fecha_autorizacion,
                "fecha_emision": documento.fecha_emision,
                "emisor": documento.emisor.nombre,
                "nit_emisor": documento.emisor.nit,
                "receptor": documento.receptor.nombre,
                "nit_receptor": documento.receptor.nit,
                "total": str(documento.total),
                "referencia": documento.referencia_interna
            })
            
        except Autorizacion.DoesNotExist:
            return Response(
                {
                    "valido": False,
                    "mensaje": "No se encontró un documento válido con los datos proporcionados"
                },
                status=status.HTTP_404_NOT_FOUND
            )


class EstadisticasGeneralesAPIView(APIView):
    """
    API endpoint para obtener estadísticas generales
    """
    permission_classes = [permissions.IsAuthenticated, IsAdminOrReadOnly]
    
    def get(self, request):
        from django.db.models import Sum, Count
        
        # Estadísticas generales
        total_documentos = DocumentoTributario.objects.count()
        total_autorizados = DocumentoTributario.objects.filter(estado=DocumentoTributario.ESTADO_AUTORIZADO).count()
        total_rechazados = DocumentoTributario.objects.filter(estado=DocumentoTributario.ESTADO_RECHAZADO).count()
        total_emisores = Contribuyente.objects.filter(documentos_emitidos__isnull=False).distinct().count()
        total_receptores = Contribuyente.objects.filter(documentos_recibidos__isnull=False).distinct().count()
        
        # Montos totales
        monto_total = DocumentoTributario.objects.filter(
            estado=DocumentoTributario.ESTADO_AUTORIZADO
        ).aggregate(total=Sum('total'))['total'] or 0
        
        iva_total = DocumentoTributario.objects.filter(
            estado=DocumentoTributario.ESTADO_AUTORIZADO
        ).aggregate(total=Sum('iva'))['total'] or 0
        
        # Principales emisores por volumen
        top_emisores = Contribuyente.objects.annotate(
            num_docs=Count('documentos_emitidos')
        ).filter(num_docs__gt=0).order_by('-num_docs')[:5]
        
        top_emisores_data = [
            {
                'nit': emisor.nit,
                'nombre': emisor.nombre,
                'documentos': emisor.num_docs
            }
            for emisor in top_emisores
        ]
        
        return Response({
            'total_documentos': total_documentos,
            'total_autorizados': total_autorizados,
            'total_rechazados': total_rechazados,
            'total_emisores': total_emisores,
            'total_receptores': total_receptores,
            'monto_total': str(monto_total),
            'iva_total': str(iva_total),
            'top_emisores': top_emisores_data
        })