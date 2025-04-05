# autoriza/models.py
from django.db import models
from django.utils import timezone
from core.models import TimeStampedModel


class ErrorValidacion(models.Model):
    """
    Catálogo de tipos de errores de validación
    """
    TIPO_NIT_EMISOR = 'NIT_EMISOR'
    TIPO_NIT_RECEPTOR = 'NIT_RECEPTOR'
    TIPO_IVA = 'IVA'
    TIPO_TOTAL = 'TOTAL'
    TIPO_REFERENCIA_DUPLICADA = 'REFERENCIA_DUPLICADA'
    TIPO_FORMATO = 'FORMATO'
    
    TIPOS = [
        (TIPO_NIT_EMISOR, 'NIT emisor inválido'),
        (TIPO_NIT_RECEPTOR, 'NIT receptor inválido'),
        (TIPO_IVA, 'IVA mal calculado'),
        (TIPO_TOTAL, 'Total mal calculado'),
        (TIPO_REFERENCIA_DUPLICADA, 'Referencia duplicada'),
        (TIPO_FORMATO, 'Error de formato'),
    ]
    
    codigo = models.CharField(max_length=30, choices=TIPOS, unique=True)
    descripcion = models.CharField(max_length=255)
    
    class Meta:
        verbose_name = "Error de Validación"
        verbose_name_plural = "Errores de Validación"
        
    def __str__(self):
        return self.descripcion


class Autorizacion(TimeStampedModel):
    """
    Modelo para gestionar la autorización de documentos tributarios
    """
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_APROBADO = 'APROBADO'
    ESTADO_RECHAZADO = 'RECHAZADO'
    
    ESTADOS = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_APROBADO, 'Aprobado'),
        (ESTADO_RECHAZADO, 'Rechazado'),
    ]
    
    documento = models.OneToOneField(
        'emisor.DocumentoTributario', 
        on_delete=models.CASCADE,
        related_name='autorizacion'
    )
    numero_autorizacion = models.CharField(max_length=20, blank=True, null=True, unique=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_PENDIENTE)
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    correlativo = models.PositiveIntegerField(null=True, blank=True)
    
    # Campo para registro de errores
    errores = models.ManyToManyField(
        ErrorValidacion, 
        through='AutorizacionError',
        related_name='autorizaciones'
    )
    
    class Meta:
        verbose_name = "Autorización"
        verbose_name_plural = "Autorizaciones"
        ordering = ['-fecha_autorizacion']
        # Índice para búsquedas rápidas por fecha
        indexes = [
            models.Index(fields=['fecha_autorizacion']),
        ]
    
    def __str__(self):
        if self.numero_autorizacion:
            return f"Autorización {self.numero_autorizacion} - {self.get_estado_display()}"
        return f"Autorización de {self.documento} - {self.get_estado_display()}"
    
    def aprobar(self):
        """
        Aprueba la autorización, generando el número de autorización
        """
        if self.estado != self.ESTADO_PENDIENTE:
            raise ValueError("Solo se pueden aprobar autorizaciones pendientes")
            
        # Obtener fecha actual para el número de autorización
        now = timezone.now()
        self.fecha_autorizacion = now
        
        # Generar correlativo diario
        fecha_str = now.strftime("%Y%m%d")
        
        # Buscar el último correlativo para este día
        ultimo = Autorizacion.objects.filter(
            fecha_autorizacion__year=now.year,
            fecha_autorizacion__month=now.month,
            fecha_autorizacion__day=now.day,
            estado=self.ESTADO_APROBADO
        ).order_by('-correlativo').first()
        
        self.correlativo = 1
        if ultimo and ultimo.correlativo:
            self.correlativo = ultimo.correlativo + 1
            
        # Generar número de autorización
        self.numero_autorizacion = f"{fecha_str}{self.correlativo:08d}"
        self.estado = self.ESTADO_APROBADO
        
        # Actualizar estado del documento
        self.documento.estado = 'AUTORIZADO'
        self.documento.save(update_fields=['estado'])
        
        self.save()
        
        return self.numero_autorizacion
    
    def rechazar(self):
        """
        Rechaza la autorización
        """
        if self.estado != self.ESTADO_PENDIENTE:
            raise ValueError("Solo se pueden rechazar autorizaciones pendientes")
            
        self.estado = self.ESTADO_RECHAZADO
        self.fecha_autorizacion = timezone.now()
        
        # Actualizar estado del documento
        self.documento.estado = 'RECHAZADO'
        self.documento.save(update_fields=['estado'])
        
        self.save()


class AutorizacionError(TimeStampedModel):
    """
    Relación entre Autorización y ErrorValidacion con detalles
    """
    autorizacion = models.ForeignKey(Autorizacion, on_delete=models.CASCADE)
    error = models.ForeignKey(ErrorValidacion, on_delete=models.CASCADE)
    detalle = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Error en Autorización"
        verbose_name_plural = "Errores en Autorización"
        
    def __str__(self):
        return f"{self.error} en {self.autorizacion}"


class EstadisticaDiaria(models.Model):
    """
    Modelo para almacenar estadísticas diarias de autorizaciones
    """
    fecha = models.DateField(unique=True)
    facturas_recibidas = models.PositiveIntegerField(default=0)
    errores_nit_emisor = models.PositiveIntegerField(default=0)
    errores_nit_receptor = models.PositiveIntegerField(default=0)
    errores_iva = models.PositiveIntegerField(default=0)
    errores_total = models.PositiveIntegerField(default=0)
    errores_referencia_duplicada = models.PositiveIntegerField(default=0)
    facturas_correctas = models.PositiveIntegerField(default=0)
    cantidad_emisores = models.PositiveIntegerField(default=0)
    cantidad_receptores = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = "Estadística Diaria"
        verbose_name_plural = "Estadísticas Diarias"
        ordering = ['-fecha']
        
    def __str__(self):
        return f"Estadísticas del {self.fecha}"
    
    @property
    def total_errores(self):
        """
        Devuelve el total de errores detectados
        """
        return (self.errores_nit_emisor + 
                self.errores_nit_receptor + 
                self.errores_iva + 
                self.errores_total + 
                self.errores_referencia_duplicada)