# api/serializers.py
from rest_framework import serializers

from emisor.models import DocumentoTributario, LineaDocumento, Contribuyente, TipoDocumento
from autoriza.models import Autorizacion, EstadisticaDiaria


class ContribuyenteSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Contribuyente
    """
    class Meta:
        model = Contribuyente
        fields = ['id', 'nit', 'nombre', 'nombre_comercial', 'direccion', 'correo', 'telefono']
        read_only_fields = ['id']


class TipoDocumentoSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo TipoDocumento
    """
    class Meta:
        model = TipoDocumento
        fields = ['id', 'codigo', 'nombre', 'descripcion', 'activo']
        read_only_fields = ['id']


class LineaDocumentoSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo LineaDocumento
    """
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = LineaDocumento
        fields = ['id', 'descripcion', 'cantidad', 'precio_unitario', 'descuento', 'subtotal']
        read_only_fields = ['id', 'subtotal']
    
    def validate(self, data):
        """
        Validar que el descuento no sea mayor que el valor total
        """
        cantidad = data.get('cantidad')
        precio_unitario = data.get('precio_unitario')
        descuento = data.get('descuento', 0)
        
        if cantidad and precio_unitario and descuento > (cantidad * precio_unitario):
            raise serializers.ValidationError(
                "El descuento no puede ser mayor que el valor total (cantidad * precio_unitario)"
            )
        
        return data


class DocumentoTributarioSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo DocumentoTributario
    """
    emisor = serializers.PrimaryKeyRelatedField(read_only=True)
    lineas = LineaDocumentoSerializer(many=True, required=True)
    receptor_nit = serializers.CharField(write_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = DocumentoTributario
        fields = [
            'id', 'uuid', 'tipo_documento', 'referencia_interna',
            'emisor', 'establecimiento', 'receptor', 'receptor_nit',
            'fecha_emision', 'moneda', 'subtotal', 'descuento',
            'iva', 'total', 'estado', 'estado_display', 'observaciones',
            'es_borrador', 'lineas'
        ]
        read_only_fields = [
            'id', 'uuid', 'emisor', 'receptor', 'subtotal',
            'iva', 'total', 'estado', 'es_borrador'
        ]
    
    def validate_receptor_nit(self, value):
        """
        Validar el NIT del receptor y buscar el contribuyente correspondiente
        """
        from core.validators import validate_nit
        
        try:
            # Limpiar NIT
            nit_limpio = ''.join(c for c in value if c.isalnum())
            
            # Validar formato del NIT
            validate_nit(nit_limpio)
            
            # Buscar contribuyente por NIT
            try:
                receptor = Contribuyente.objects.get(nit=nit_limpio)
                return receptor
            except Contribuyente.DoesNotExist:
                raise serializers.ValidationError(
                    "No existe un contribuyente con el NIT proporcionado"
                )
                
        except Exception as e:
            raise serializers.ValidationError(str(e))
    
    def validate(self, data):
        """
        Validaciones adicionales para el documento
        """
        # Validar que no exista un documento con la misma referencia para el mismo emisor en el mismo día
        emisor = self.context['request'].user.contribuyente
        referencia = data.get('referencia_interna')
        
        if referencia and emisor:
            from django.utils import timezone
            hoy = timezone.now().date()
            
            # Excluir el documento actual en caso de actualización
            query = DocumentoTributario.objects.filter(
                emisor=emisor,
                referencia_interna=referencia,
                fecha_emision__date=hoy
            )
            
            if self.instance:
                query = query.exclude(pk=self.instance.pk)
                
            if query.exists():
                raise serializers.ValidationError(
                    {"referencia_interna": "Ya existe un documento con esta referencia para el día de hoy"}
                )
        
        return data
    
    def create(self, validated_data):
        """
        Crear documento con sus líneas
        """
        # Extraer datos de líneas
        lineas_data = validated_data.pop('lineas')
        receptor = validated_data.pop('receptor_nit')
        
        # Crear documento
        documento = DocumentoTributario(
            emisor=self.context['request'].user.contribuyente,
            receptor=receptor,
            **validated_data
        )
        
        # Guardar para tener un ID
        documento.save()
        
        # Crear líneas
        for linea_data in lineas_data:
            LineaDocumento.objects.create(
                documento=documento,
                **linea_data
            )
        
        # Calcular totales
        documento.subtotal = sum(linea.subtotal for linea in documento.lineas.all())
        documento.descuento = sum(linea.descuento for linea in documento.lineas.all())
        documento.iva = documento.calcular_iva()
        documento.total = documento.calcular_total()
        documento.save()
        
        return documento
    
    def update(self, instance, validated_data):
        """
        Actualizar documento y sus líneas
        """
        # Solo permitir actualizar borradores
        if not instance.es_borrador or instance.estado != DocumentoTributario.ESTADO_BORRADOR:
            raise serializers.ValidationError(
                "Solo se pueden actualizar documentos en estado borrador"
            )
        
        # Actualizar campos del documento
        for attr, value in validated_data.items():
            if attr != 'lineas' and attr != 'receptor_nit':
                setattr(instance, attr, value)
        
        # Actualizar receptor si se proporciona
        if 'receptor_nit' in validated_data:
            instance.receptor = validated_data.get('receptor_nit')
        
        # Actualizar líneas si se proporcionan
        if 'lineas' in validated_data:
            # Eliminar líneas existentes
            instance.lineas.all().delete()
            
            # Crear nuevas líneas
            for linea_data in validated_data.get('lineas'):
                LineaDocumento.objects.create(
                    documento=instance,
                    **linea_data
                )
        
        # Recalcular totales
        instance.subtotal = sum(linea.subtotal for linea in instance.lineas.all())
        instance.descuento = sum(linea.descuento for linea in instance.lineas.all())
        instance.iva = instance.calcular_iva()
        instance.total = instance.calcular_total()
        instance.save()
        
        return instance


class AutorizacionSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo Autorizacion
    """
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    documento = DocumentoTributarioSerializer(read_only=True)
    
    class Meta:
        model = Autorizacion
        fields = [
            'id', 'documento', 'numero_autorizacion', 'estado',
            'estado_display', 'fecha_autorizacion'
        ]
        read_only_fields = fields


class EstadisticaDiariaSerializer(serializers.ModelSerializer):
    """
    Serializer para el modelo EstadisticaDiaria
    """
    total_errores = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = EstadisticaDiaria
        fields = [
            'id', 'fecha', 'facturas_recibidas', 'errores_nit_emisor',
            'errores_nit_receptor', 'errores_iva', 'errores_total',
            'errores_referencia_duplicada', 'facturas_correctas',
            'cantidad_emisores', 'cantidad_receptores', 'total_errores'
        ]
        read_only_fields = fields