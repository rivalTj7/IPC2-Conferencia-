
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.utils import timezone
import uuid

from core.models import TimeStampedModel
from core.validators import validate_nit


class Contribuyente(TimeStampedModel):
    """
    Modelo que representa a un contribuyente (emisor o receptor de documentos)
    """
    nit = models.CharField(max_length=20, validators=[validate_nit], unique=True)
    nombre = models.CharField(max_length=255)
    nombre_comercial = models.CharField(max_length=255, blank=True)
    direccion = models.CharField(max_length=255)
    correo = models.EmailField()
    telefono = models.CharField(max_length=15, blank=True)
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='contribuyente',
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = "Contribuyente"
        verbose_name_plural = "Contribuyentes"
        ordering = ['nombre']
        
    def __str__(self):
        return f"{self.nombre} ({self.nit})"


class Establecimiento(TimeStampedModel):
    """
    Modelo para los establecimientos comerciales de un contribuyente
    """
    contribuyente = models.ForeignKey(
        Contribuyente, 
        on_delete=models.CASCADE,
        related_name='establecimientos'
    )
    codigo = models.CharField(max_length=3)
    nombre = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Establecimiento"
        verbose_name_plural = "Establecimientos"
        unique_together = [['contribuyente', 'codigo']]
        
    def __str__(self):
        return f"{self.nombre} ({self.codigo}) - {self.contribuyente.nombre}"


class TipoDocumento(models.Model):
    """
    Catálogo de tipos de documentos tributarios
    """
    codigo = models.CharField(max_length=10, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Tipo de Documento"
        verbose_name_plural = "Tipos de Documentos"
        
    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class DocumentoTributario(TimeStampedModel):
    """
    Modelo base para documentos tributarios electrónicos (DTE)
    """
    ESTADO_BORRADOR = 'BORRADOR'
    ESTADO_EMITIDO = 'EMITIDO'
    ESTADO_AUTORIZADO = 'AUTORIZADO'
    ESTADO_RECHAZADO = 'RECHAZADO'
    ESTADO_ANULADO = 'ANULADO'
    
    ESTADOS = [
        (ESTADO_BORRADOR, 'Borrador'),
        (ESTADO_EMITIDO, 'Emitido'),
        (ESTADO_AUTORIZADO, 'Autorizado'),
        (ESTADO_RECHAZADO, 'Rechazado'),
        (ESTADO_ANULADO, 'Anulado'),
    ]
    
    # Campos de identificación
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    tipo_documento = models.ForeignKey(TipoDocumento, on_delete=models.PROTECT)
    referencia_interna = models.CharField(max_length=40)
    
    # Campos de emisor/receptor
    emisor = models.ForeignKey(
        Contribuyente, 
        on_delete=models.PROTECT,
        related_name='documentos_emitidos'
    )
    establecimiento = models.ForeignKey(
        Establecimiento,
        on_delete=models.PROTECT,
        related_name='documentos'
    )
    receptor = models.ForeignKey(
        Contribuyente,
        on_delete=models.PROTECT,
        related_name='documentos_recibidos'
    )
    
    # Fechas
    fecha_emision = models.DateTimeField(default=timezone.now)
    
    # Montos
    moneda = models.CharField(max_length=3, default='GTQ')  # Quetzal guatemalteco
    subtotal = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    descuento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    iva = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default=ESTADO_BORRADOR
    )
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    
    # Si es borrador, puede ser editado por el usuario
    es_borrador = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Documento Tributario"
        verbose_name_plural = "Documentos Tributarios"
        # No puede haber duplicados en referencia para el mismo emisor y fecha
        unique_together = [['emisor', 'referencia_interna', 'fecha_emision']]
        ordering = ['-fecha_emision']
    
    def __str__(self):
        return f"{self.tipo_documento} - {self.referencia_interna} ({self.estado})"
    
    def calcular_iva(self):
        """Calcula el IVA según la base imponible (subtotal - descuento)"""
        base_imponible = self.subtotal - self.descuento
        return round(base_imponible * Decimal('0.12'), 2)
    
    def calcular_total(self):
        """Calcula el total (subtotal - descuento + iva)"""
        return self.subtotal - self.descuento + self.iva
    
    def validar_calculos(self):
        """
        Valida los cálculos de IVA y total
        Retorna tupla (es_valido, mensaje_error)
        """
        iva_calculado = self.calcular_iva()
        if self.iva != iva_calculado:
            return False, f"El IVA calculado ({iva_calculado}) no coincide con el reportado ({self.iva})"
        
        total_calculado = self.calcular_total()
        if self.total != total_calculado:
            return False, f"El total calculado ({total_calculado}) no coincide con el reportado ({self.total})"
            
        return True, ""
    
    def generar_numero_autorizacion(self):
        """
        Genera el número de autorización con formato YYYYMMDD########
        """
        from autoriza.models import Autorizacion
        
        fecha = self.fecha_emision
        fecha_str = fecha.strftime("%Y%m%d")
        
        # Obtiene el último correlativo para la fecha actual
        ultimo = Autorizacion.objects.filter(
            fecha_autorizacion__year=fecha.year,
            fecha_autorizacion__month=fecha.month,
            fecha_autorizacion__day=fecha.day
        ).order_by('-correlativo').first()
        
        correlativo = 1
        if ultimo:
            correlativo = ultimo.correlativo + 1
            
        # Formatea el correlativo con ceros a la izquierda (8 dígitos)
        correlativo_str = f"{correlativo:08d}"
        
        return f"{fecha_str}{correlativo_str}"
    
    def save(self, *args, **kwargs):
        if not self.pk:
            # Si es nuevo registro y no se ha especificado IVA o total
            if not self.iva:
                self.iva = self.calcular_iva()
            if not self.total:
                self.total = self.calcular_total()
                
        super().save(*args, **kwargs)


class LineaDocumento(TimeStampedModel):
    """
    Línea o detalle de un documento tributario
    """
    documento = models.ForeignKey(
        DocumentoTributario, 
        on_delete=models.CASCADE,
        related_name='lineas'
    )
    descripcion = models.CharField(max_length=255)
    cantidad = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    precio_unitario = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    descuento = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        verbose_name = "Línea de Documento"
        verbose_name_plural = "Líneas de Documentos"
        ordering = ['id']
    
    def __str__(self):
        return f"{self.descripcion} - {self.cantidad} x {self.precio_unitario}"
    
    def calcular_subtotal(self):
        """Calcula el subtotal (cantidad * precio_unitario - descuento)"""
        return (self.cantidad * self.precio_unitario) - self.descuento
    
    def save(self, *args, **kwargs):
        if not self.subtotal:
            self.subtotal = self.calcular_subtotal()
        super().save(*args, **kwargs)