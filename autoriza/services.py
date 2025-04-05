# autoriza/services.py
from django.db import transaction
from django.utils import timezone

from emisor.models import DocumentoTributario
from .models import Autorizacion, ErrorValidacion, AutorizacionError, EstadisticaDiaria


@transaction.atomic
def crear_solicitud_autorizacion(documento):
    """
    Crea una solicitud de autorización para un documento tributario
    
    Parámetros:
    - documento: Instancia de DocumentoTributario
    
    Retorna:
    - Instancia de Autorización creada
    """
    # Verificar que el documento esté en estado emitido
    if documento.estado != DocumentoTributario.ESTADO_EMITIDO:
        raise ValueError("Solo se pueden autorizar documentos en estado EMITIDO")
    
    # Crear la autorización
    autorizacion = Autorizacion(
        documento=documento,
        estado=Autorizacion.ESTADO_PENDIENTE
    )
    autorizacion.save()
    
    # Iniciar proceso de validación
    validar_documento(autorizacion)
    
    return autorizacion


def validar_documento(autorizacion):
    """
    Valida un documento tributario para su autorización
    
    Parámetros:
    - autorizacion: Instancia de Autorización a validar
    
    Retorna:
    - True si el documento es válido, False en caso contrario
    """
    documento = autorizacion.documento
    errores = []
    
    # 1. Validar NIT del emisor
    try:
        from core.validators import validate_nit
        validate_nit(documento.emisor.nit)
    except Exception as e:
        error = ErrorValidacion.objects.get(codigo=ErrorValidacion.TIPO_NIT_EMISOR)
        AutorizacionError.objects.create(
            autorizacion=autorizacion,
            error=error,
            detalle=str(e)
        )
        errores.append(error.codigo)
    
    # 2. Validar NIT del receptor
    try:
        validate_nit(documento.receptor.nit)
    except Exception as e:
        error = ErrorValidacion.objects.get(codigo=ErrorValidacion.TIPO_NIT_RECEPTOR)
        AutorizacionError.objects.create(
            autorizacion=autorizacion,
            error=error,
            detalle=str(e)
        )
        errores.append(error.codigo)
    
    # 3. Validar cálculo de IVA
    iva_calculado = documento.calcular_iva()
    if documento.iva != iva_calculado:
        error = ErrorValidacion.objects.get(codigo=ErrorValidacion.TIPO_IVA)
        AutorizacionError.objects.create(
            autorizacion=autorizacion,
            error=error,
            detalle=f"El IVA reportado ({documento.iva}) no coincide con el calculado ({iva_calculado})"
        )
        errores.append(error.codigo)
    
    # 4. Validar cálculo de total
    total_calculado = documento.calcular_total()
    if documento.total != total_calculado:
        error = ErrorValidacion.objects.get(codigo=ErrorValidacion.TIPO_TOTAL)
        AutorizacionError.objects.create(
            autorizacion=autorizacion,
            error=error,
            detalle=f"El total reportado ({documento.total}) no coincide con el calculado ({total_calculado})"
        )
        errores.append(error.codigo)
    
    # 5. Validar referencia única para el día
    fecha = documento.fecha_emision.date()
    duplicado = DocumentoTributario.objects.filter(
        emisor=documento.emisor,
        referencia_interna=documento.referencia_interna,
        fecha_emision__date=fecha
    ).exclude(id=documento.id).exists()
    
    if duplicado:
        error = ErrorValidacion.objects.get(codigo=ErrorValidacion.TIPO_REFERENCIA_DUPLICADA)
        AutorizacionError.objects.create(
            autorizacion=autorizacion,
            error=error,
            detalle=f"Ya existe un documento con la referencia {documento.referencia_interna} emitido el {fecha}"
        )
        errores.append(error.codigo)
    
    # Si no hay errores, aprobar la autorización
    if not errores:
        autorizacion.aprobar()
        # Actualizar estadísticas
        actualizar_estadisticas(autorizacion, True)
        return True
    else:
        # Rechazar la autorización
        autorizacion.rechazar()
        # Actualizar estadísticas
        actualizar_estadisticas(autorizacion, False)
        return False


def actualizar_estadisticas(autorizacion, aprobado):
    """
    Actualiza las estadísticas diarias de autorización
    
    Parámetros:
    - autorizacion: Instancia de Autorización
    - aprobado: Boolean indicando si la autorización fue aprobada
    """
    fecha = autorizacion.documento.fecha_emision.date()
    
    # Buscar o crear estadística para la fecha
    estadistica, created = EstadisticaDiaria.objects.get_or_create(
        fecha=fecha
    )
    
    # Incrementar contador de facturas recibidas
    estadistica.facturas_recibidas += 1
    
    # Si fue aprobada, incrementar contador de facturas correctas
    if aprobado:
        estadistica.facturas_correctas += 1
    else:
        # Incrementar contadores de errores
        errores = autorizacion.autorizacionerror_set.all()
        for error in errores:
            codigo = error.error.codigo
            if codigo == ErrorValidacion.TIPO_NIT_EMISOR:
                estadistica.errores_nit_emisor += 1
            elif codigo == ErrorValidacion.TIPO_NIT_RECEPTOR:
                estadistica.errores_nit_receptor += 1
            elif codigo == ErrorValidacion.TIPO_IVA:
                estadistica.errores_iva += 1
            elif codigo == ErrorValidacion.TIPO_TOTAL:
                estadistica.errores_total += 1
            elif codigo == ErrorValidacion.TIPO_REFERENCIA_DUPLICADA:
                estadistica.errores_referencia_duplicada += 1
    
    # Actualizar contadores de emisores y receptores únicos
    documento = autorizacion.documento
    
    # Contar emisores únicos para esta fecha
    emisores_unicos = DocumentoTributario.objects.filter(
        fecha_emision__date=fecha
    ).values('emisor').distinct().count()
    
    # Contar receptores únicos para esta fecha
    receptores_unicos = DocumentoTributario.objects.filter(
        fecha_emision__date=fecha
    ).values('receptor').distinct().count()
    
    estadistica.cantidad_emisores = emisores_unicos
    estadistica.cantidad_receptores = receptores_unicos
    
    estadistica.save()


def generar_informe_xml():
    """
    Genera un archivo XML con las estadísticas y autorizaciones
    
    Retorna:
    - String con el contenido XML
    """
    from lxml import etree
    from django.utils.dateparse import parse_date
    
    # Crear elemento raíz
    root = etree.Element("LISTAAUTORIZACIONES")
    
    # Obtener todas las estadísticas ordenadas por fecha
    estadisticas = EstadisticaDiaria.objects.all().order_by('fecha')
    
    for estadistica in estadisticas:
        # Crear elemento AUTORIZACION para cada fecha
        autorizacion_elem = etree.SubElement(root, "AUTORIZACION")
        
        # Añadir fecha
        fecha_elem = etree.SubElement(autorizacion_elem, "FECHA")
        fecha_elem.text = estadistica.fecha.strftime("%d/%m/%Y")
        
        # Añadir facturas recibidas
        facturas_elem = etree.SubElement(autorizacion_elem, "FACTURAS_RECIBIDAS")
        facturas_elem.text = str(estadistica.facturas_recibidas)
        
        # Añadir errores
        errores_elem = etree.SubElement(autorizacion_elem, "ERRORES")
        
        nit_emisor_elem = etree.SubElement(errores_elem, "NIT_EMISOR")
        nit_emisor_elem.text = str(estadistica.errores_nit_emisor)
        
        nit_receptor_elem = etree.SubElement(errores_elem, "NIT_RECEPTOR")
        nit_receptor_elem.text = str(estadistica.errores_nit_receptor)
        
        iva_elem = etree.SubElement(errores_elem, "IVA")
        iva_elem.text = str(estadistica.errores_iva)
        
        total_elem = etree.SubElement(errores_elem, "TOTAL")
        total_elem.text = str(estadistica.errores_total)
        
        ref_dup_elem = etree.SubElement(errores_elem, "REFERENCIA_DUPLICADA")
        ref_dup_elem.text = str(estadistica.errores_referencia_duplicada)
        
        # Añadir facturas correctas
        correctas_elem = etree.SubElement(autorizacion_elem, "FACTURAS_CORRECTAS")
        correctas_elem.text = str(estadistica.facturas_correctas)
        
        # Añadir cantidad de emisores
        emisores_elem = etree.SubElement(autorizacion_elem, "CANTIDAD_EMISORES")
        emisores_elem.text = str(estadistica.cantidad_emisores)
        
        # Añadir cantidad de receptores
        receptores_elem = etree.SubElement(autorizacion_elem, "CANTIDAD_RECEPTORES")
        receptores_elem.text = str(estadistica.cantidad_receptores)
        
        # Añadir listado de autorizaciones
        listado_elem = etree.SubElement(autorizacion_elem, "LISTADO_AUTORIZACIONES")
        
        # Obtener autorizaciones aprobadas para esta fecha
        autorizaciones = Autorizacion.objects.filter(
            fecha_autorizacion__date=estadistica.fecha,
            estado=Autorizacion.ESTADO_APROBADO
        ).select_related('documento__emisor')
        
        for aut in autorizaciones:
            aprobacion_elem = etree.SubElement(listado_elem, "APROBACION")
            
            nit_emisor_elem = etree.SubElement(aprobacion_elem, "NIT_EMISOR")
            nit_emisor_elem.set("ref", aut.documento.referencia_interna)
            nit_emisor_elem.text = aut.documento.emisor.nit
            
            codigo_elem = etree.SubElement(aprobacion_elem, "CODIGO_APROBACION")
            codigo_elem.text = aut.numero_autorizacion
        
        # Añadir total de aprobaciones
        total_aprobaciones_elem = etree.SubElement(listado_elem, "TOTAL_APROBACIONES")
        total_aprobaciones_elem.text = str(autorizaciones.count())
    
    # Convertir a cadena XML
    return etree.tostring(root, pretty_print=True, encoding='UTF-8', xml_declaration=True)


def guardar_informe_xml(path='autorizaciones.xml'):
    """
    Guarda el informe XML en un archivo
    
    Parámetros:
    - path: Ruta donde guardar el archivo
    """
    xml_content = generar_informe_xml()
    
    with open(path, 'wb') as f:
        f.write(xml_content)