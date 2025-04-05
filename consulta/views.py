# consulta/views.py
from django.shortcuts import render
from django.views.generic import TemplateView, ListView, DetailView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth, TruncDay
from django.utils import timezone
import datetime
import csv
import json

from emisor.models import DocumentoTributario, Contribuyente
from autoriza.models import Autorizacion, EstadisticaDiaria
from .forms import ReporteFechaForm, ReporteRangoFechasForm, ReporteIvaForm


class AuditorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin para verificar que el usuario es un auditor
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'AUDITOR'


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Vista de dashboard que muestra estadísticas generales según el rol del usuario
    """
    template_name = 'consulta/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        
        # Si es contribuyente
        if hasattr(user, 'contribuyente'):
            contribuyente = user.contribuyente
            
            # Documentos del último mes
            ultimo_mes = timezone.now() - datetime.timedelta(days=30)
            
            # Documentos emitidos
            emitidos = DocumentoTributario.objects.filter(
                emisor=contribuyente,
                fecha_emision__gte=ultimo_mes
            )
            
            # Documentos recibidos
            recibidos = DocumentoTributario.objects.filter(
                receptor=contribuyente,
                fecha_emision__gte=ultimo_mes
            )
            
            # Estadísticas de documentos emitidos
            total_emitidos = emitidos.count()
            monto_emitido = emitidos.aggregate(total=Sum('total'))['total'] or 0
            iva_emitido = emitidos.aggregate(total=Sum('iva'))['total'] or 0
            
            # Estadísticas de documentos recibidos
            total_recibidos = recibidos.count()
            monto_recibido = recibidos.aggregate(total=Sum('total'))['total'] or 0
            iva_recibido = recibidos.aggregate(total=Sum('iva'))['total'] or 0
            
            # Estadísticas por estado
            por_estado = emitidos.values('estado').annotate(
                count=Count('id')
            ).order_by('estado')
            
            # Datos para gráfica de documentos por día
            emitidos_por_dia = emitidos.annotate(
                dia=TruncDay('fecha_emision')
            ).values('dia').annotate(
                count=Count('id'),
                monto=Sum('total')
            ).order_by('dia')
            
            context.update({
                'es_contribuyente': True,
                'total_emitidos': total_emitidos,
                'monto_emitido': monto_emitido,
                'iva_emitido': iva_emitido,
                'total_recibidos': total_recibidos,
                'monto_recibido': monto_recibido,
                'iva_recibido': iva_recibido,
                'por_estado': por_estado,
                'emitidos_por_dia': emitidos_por_dia,
            })
        
        # Si es auditor o admin
        elif user.role in ['AUDITOR', 'ADMIN']:
            # Estadísticas generales del último mes
            ultimo_mes = timezone.now() - datetime.timedelta(days=30)
            
            # Total de documentos
            total_docs = DocumentoTributario.objects.filter(
                fecha_emision__gte=ultimo_mes
            ).count()
            
            # Total de autorizaciones
            total_autorizaciones = Autorizacion.objects.filter(
                fecha_autorizacion__gte=ultimo_mes,
                estado=Autorizacion.ESTADO_APROBADO
            ).count()
            
            # Total de rechazos
            total_rechazos = Autorizacion.objects.filter(
                fecha_autorizacion__gte=ultimo_mes,
                estado=Autorizacion.ESTADO_RECHAZADO
            ).count()
            
            # Documentos por día
            docs_por_dia = DocumentoTributario.objects.filter(
                fecha_emision__gte=ultimo_mes
            ).annotate(
                dia=TruncDay('fecha_emision')
            ).values('dia').annotate(
                count=Count('id')
            ).order_by('dia')
            
            # Top contribuyentes por cantidad de emisiones
            top_emisores = Contribuyente.objects.annotate(
                num_docs=Count('documentos_emitidos', filter=Q(
                    documentos_emitidos__fecha_emision__gte=ultimo_mes
                ))
            ).filter(num_docs__gt=0).order_by('-num_docs')[:10]
            
            # Estadísticas por estado
            por_estado = DocumentoTributario.objects.filter(
                fecha_emision__gte=ultimo_mes
            ).values('estado').annotate(
                count=Count('id')
            ).order_by('estado')
            
            context.update({
                'es_auditor': True,
                'total_docs': total_docs,
                'total_autorizaciones': total_autorizaciones,
                'total_rechazos': total_rechazos,
                'docs_por_dia': docs_por_dia,
                'top_emisores': top_emisores,
                'por_estado': por_estado,
            })
        
        return context


class EstadisticasView(AuditorRequiredMixin, ListView):
    """
    Vista que muestra estadísticas diarias de las autorizaciones
    """
    model = EstadisticaDiaria
    template_name = 'consulta/estadisticas.html'
    context_object_name = 'estadisticas'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = EstadisticaDiaria.objects.all().order_by('-fecha')
        
        # Filtrar por fecha si se especifica
        fecha = self.request.GET.get('fecha')
        if fecha:
            try:
                fecha_parsed = datetime.datetime.strptime(fecha, '%Y-%m-%d').date()
                queryset = queryset.filter(fecha=fecha_parsed)
            except ValueError:
                pass
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas generales
        totales = EstadisticaDiaria.objects.aggregate(
            total_recibidas=Sum('facturas_recibidas'),
            total_correctas=Sum('facturas_correctas'),
            total_emisores=Sum('cantidad_emisores'),
            total_receptores=Sum('cantidad_receptores'),
            total_errores_nit_emisor=Sum('errores_nit_emisor'),
            total_errores_nit_receptor=Sum('errores_nit_receptor'),
            total_errores_iva=Sum('errores_iva'),
            total_errores_total=Sum('errores_total'),
            total_errores_referencia=Sum('errores_referencia_duplicada')
        )
        
        context['totales'] = totales
        
        # Datos para gráfica de facturas por día
        facturas_por_dia = EstadisticaDiaria.objects.values('fecha').annotate(
            recibidas=Sum('facturas_recibidas'),
            correctas=Sum('facturas_correctas')
        ).order_by('fecha')
        
        context['facturas_por_dia'] = list(facturas_por_dia)
        
        return context


class ReporteIvaView(AuditorRequiredMixin, FormView):
    """
    Vista para generar reporte de IVA por fecha y NIT
    """
    template_name = 'consulta/reporte_iva.html'
    form_class = ReporteIvaForm
    
    def form_valid(self, form):
        fecha = form.cleaned_data['fecha']
        nit = form.cleaned_data['nit']
        
        # Si se especifica un NIT, filtrar por ese NIT
        if nit:
            # Buscar contribuyente por NIT
            try:
                contribuyente = Contribuyente.objects.get(nit=nit)
                
                # Documentos emitidos (IVA cobrado)
                emitidos = DocumentoTributario.objects.filter(
                    emisor=contribuyente,
                    fecha_emision__date=fecha,
                    estado=DocumentoTributario.ESTADO_AUTORIZADO
                )
                
                iva_emitido = emitidos.aggregate(total=Sum('iva'))['total'] or 0
                
                # Documentos recibidos (IVA pagado)
                recibidos = DocumentoTributario.objects.filter(
                    receptor=contribuyente,
                    fecha_emision__date=fecha,
                    estado=DocumentoTributario.ESTADO_AUTORIZADO
                )
                
                iva_recibido = recibidos.aggregate(total=Sum('iva'))['total'] or 0
                
                data = {
                    'nit': nit,
                    'nombre': contribuyente.nombre,
                    'fecha': fecha.strftime('%d/%m/%Y'),
                    'iva_emitido': float(iva_emitido),
                    'iva_recibido': float(iva_recibido),
                    'diferencia': float(iva_emitido - iva_recibido)
                }
                
                return render(self.request, 'consulta/reporte_iva_resultado.html', {
                    'form': form,
                    'contribuyente': contribuyente,
                    'iva_emitido': iva_emitido,
                    'iva_recibido': iva_recibido,
                    'fecha': fecha,
                    'data_json': json.dumps(data)
                })
                
            except Contribuyente.DoesNotExist:
                form.add_error('nit', 'No existe un contribuyente con ese NIT.')
                return self.form_invalid(form)
        
        # Si no se especifica NIT, mostrar todos los contribuyentes para esa fecha
        else:
            # Obtener todos los contribuyentes con actividad en esa fecha
            contribuyentes_emisores = Contribuyente.objects.filter(
                documentos_emitidos__fecha_emision__date=fecha,
                documentos_emitidos__estado=DocumentoTributario.ESTADO_AUTORIZADO
            ).distinct()
            
            contribuyentes_receptores = Contribuyente.objects.filter(
                documentos_recibidos__fecha_emision__date=fecha,
                documentos_recibidos__estado=DocumentoTributario.ESTADO_AUTORIZADO
            ).distinct()
            
            # Combinar y eliminar duplicados
            contribuyentes_ids = set(contribuyentes_emisores.values_list('id', flat=True)).union(
                contribuyentes_receptores.values_list('id', flat=True)
            )
            
            # Resultado con datos de IVA
            resultado = []
            series_emitido = []
            series_recibido = []
            labels = []
            
            for contribuyente in Contribuyente.objects.filter(id__in=contribuyentes_ids):
                # IVA emitido
                iva_emitido = DocumentoTributario.objects.filter(
                    emisor=contribuyente,
                    fecha_emision__date=fecha,
                    estado=DocumentoTributario.ESTADO_AUTORIZADO
                ).aggregate(total=Sum('iva'))['total'] or 0
                
                # IVA recibido
                iva_recibido = DocumentoTributario.objects.filter(
                    receptor=contribuyente,
                    fecha_emision__date=fecha,
                    estado=DocumentoTributario.ESTADO_AUTORIZADO
                ).aggregate(total=Sum('iva'))['total'] or 0
                
                resultado.append({
                    'contribuyente': contribuyente,
                    'iva_emitido': iva_emitido,
                    'iva_recibido': iva_recibido,
                    'diferencia': iva_emitido - iva_recibido
                })
                
                # Datos para la gráfica
                series_emitido.append(float(iva_emitido))
                series_recibido.append(float(iva_recibido))
                labels.append(contribuyente.nombre)
            
            # Ordenar por diferencia de mayor a menor
            resultado.sort(key=lambda x: x['diferencia'], reverse=True)
            
            # Datos para el JSON de la gráfica
            data_json = {
                'labels': labels,
                'series_emitido': series_emitido,
                'series_recibido': series_recibido
            }
            
            return render(self.request, 'consulta/reporte_iva_global.html', {
                'form': form,
                'resultado': resultado,
                'fecha': fecha,
                'data_json': json.dumps(data_json)
            })


class ReporteRangoFechasView(AuditorRequiredMixin, FormView):
    """
    Vista para generar reporte por rango de fechas
    """
    template_name = 'consulta/reporte_rango_fechas.html'
    form_class = ReporteRangoFechasForm
    
    def form_valid(self, form):
        fecha_desde = form.cleaned_data['fecha_desde']
        fecha_hasta = form.cleaned_data['fecha_hasta']
        incluir_iva = form.cleaned_data['incluir_iva']
        
        # Verificar que el rango de fechas sea válido
        if fecha_hasta < fecha_desde:
            form.add_error('fecha_hasta', 'La fecha final debe ser mayor o igual a la fecha inicial.')
            return self.form_invalid(form)
        
        # Consultar documentos en el rango de fechas
        documentos = DocumentoTributario.objects.filter(
            fecha_emision__date__gte=fecha_desde,
            fecha_emision__date__lte=fecha_hasta,
            estado=DocumentoTributario.ESTADO_AUTORIZADO
        )
        
        # Agrupar por día
        documentos_por_dia = documentos.annotate(
            dia=TruncDay('fecha_emision')
        ).values('dia').annotate(
            total=Sum('total'),
            subtotal=Sum('subtotal'),
            iva=Sum('iva'),
            cantidad=Count('id')
        ).order_by('dia')
        
        # Preparar datos para la gráfica
        labels = []
        totales = []
        iva_valores = []
        subtotales = []
        
        for item in documentos_por_dia:
            labels.append(item['dia'].strftime('%d/%m/%Y'))
            totales.append(float(item['total']))
            iva_valores.append(float(item['iva']))
            subtotales.append(float(item['subtotal']))
        
        data_json = {
            'labels': labels,
            'totales': totales,
            'iva': iva_valores,
            'subtotales': subtotales,
            'incluir_iva': incluir_iva
        }
        
        return render(self.request, 'consulta/reporte_rango_fechas_resultado.html', {
            'form': form,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta,
            'incluir_iva': incluir_iva,
            'documentos_por_dia': documentos_por_dia,
            'data_json': json.dumps(data_json)
        })


class ExportarCsvView(AuditorRequiredMixin, FormView):
    """
    Vista para exportar datos a CSV
    """
    template_name = 'consulta/exportar_csv.html'
    form_class = ReporteRangoFechasForm
    
    def form_valid(self, form):
        fecha_desde = form.cleaned_data['fecha_desde']
        fecha_hasta = form.cleaned_data['fecha_hasta']
        
        # Consultar documentos en el rango de fechas
        documentos = DocumentoTributario.objects.filter(
            fecha_emision__date__gte=fecha_desde,
            fecha_emision__date__lte=fecha_hasta
        ).select_related('emisor', 'receptor', 'tipo_documento')
        
        # Crear respuesta HTTP con el CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="documentos_{fecha_desde}_{fecha_hasta}.csv"'
        
        # Crear escritor CSV
        writer = csv.writer(response)
        # Escribir encabezados
        writer.writerow([
            'ID', 'Tipo Documento', 'Referencia', 'Fecha Emisión',
            'Emisor NIT', 'Emisor Nombre', 'Receptor NIT', 'Receptor Nombre',
            'Subtotal', 'IVA', 'Total', 'Estado', 'Número Autorización'
        ])
        
        # Escribir filas de datos
        for doc in documentos:
            try:
                autorizacion = doc.autorizacion
                numero_autorizacion = autorizacion.numero_autorizacion or '-'
            except:
                numero_autorizacion = '-'
                
            writer.writerow([
                doc.id,
                doc.tipo_documento.nombre,
                doc.referencia_interna,
                doc.fecha_emision.strftime('%d/%m/%Y %H:%M'),
                doc.emisor.nit,
                doc.emisor.nombre,
                doc.receptor.nit,
                doc.receptor.nombre,
                doc.subtotal,
                doc.iva,
                doc.total,
                doc.get_estado_display(),
                numero_autorizacion
            ])
        
        return response


class GenerarPdfView(AuditorRequiredMixin, FormView):
    """
    Vista para generar reportes en PDF
    """
    template_name = 'consulta/generar_pdf.html'
    form_class = ReporteRangoFechasForm
    
    def form_valid(self, form):
        fecha_desde = form.cleaned_data['fecha_desde']
        fecha_hasta = form.cleaned_data['fecha_hasta']
        
        # Generar reporte PDF usando ReportLab o WeasyPrint
        # Este es un ejemplo usando WeasyPrint (requiere instalación adicional)
        # from django.template.loader import render_to_string
        # from weasyprint import HTML
        # from weasyprint.fonts import FontConfiguration
        
        # Consultar datos
        documentos = DocumentoTributario.objects.filter(
            fecha_emision__date__gte=fecha_desde,
            fecha_emision__date__lte=fecha_hasta
        ).select_related('emisor', 'receptor', 'tipo_documento')
        
        # Renderizar template a string
        # html_string = render_to_string('consulta/pdf_template.html', {
        #     'documentos': documentos,
        #     'fecha_desde': fecha_desde,
        #     'fecha_hasta': fecha_hasta,
        #     'fecha_generacion': timezone.now()
        # })
        
        # Generar PDF
        # font_config = FontConfiguration()
        # html = HTML(string=html_string)
        # result = html.write_pdf(font_config=font_config)
        
        # Crear respuesta HTTP con el PDF
        # response = HttpResponse(result, content_type='application/pdf')
        # response['Content-Disposition'] = f'attachment; filename="reporte_{fecha_desde}_{fecha_hasta}.pdf"'
        
        # NOTA: En este punto, deberíamos retornar la respuesta con el PDF,
        # pero como WeasyPrint requiere instalación adicional, aquí simplemente
        # redirigimos a una página de ejemplo.
        
        # Por ahora, solo renderizamos una página informativa
        return render(self.request, 'consulta/pdf_preview.html', {
            'documentos': documentos,
            'fecha_desde': fecha_desde,
            'fecha_hasta': fecha_hasta
        })