# emisor/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect, JsonResponse
from django.db import transaction
from django.utils import timezone

from .models import DocumentoTributario, LineaDocumento, Contribuyente, Establecimiento
from .forms import (
    DocumentoTributarioForm, LineaDocumentoFormSet, 
    BusquedaDocumentoForm, ContribuyenteForm,
    EstablecimientoForm
)


class ContribuyenteRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin para verificar que el usuario es un contribuyente
    """
    def test_func(self):
        return hasattr(self.request.user, 'contribuyente')
    
    def handle_no_permission(self):
        messages.error(
            self.request,
            'Debe completar su registro como contribuyente para acceder a esta página.'
        )
        return super().handle_no_permission()


class DocumentoListView(ContribuyenteRequiredMixin, ListView):
    """
    Vista para listar los documentos del contribuyente
    """
    model = DocumentoTributario
    template_name = 'emisor/documento_list.html'
    context_object_name = 'documentos'
    paginate_by = 10
    
    def get_queryset(self):
        """
        Filtrar documentos por el contribuyente actual
        """
        contribuyente = self.request.user.contribuyente
        queryset = DocumentoTributario.objects.filter(emisor=contribuyente)
        
        # Aplicar filtros de búsqueda
        form = BusquedaDocumentoForm(self.request.GET)
        if form.is_valid():
            data = form.cleaned_data
            
            if data.get('referencia'):
                queryset = queryset.filter(referencia_interna__icontains=data['referencia'])
            
            if data.get('fecha_desde'):
                queryset = queryset.filter(fecha_emision__date__gte=data['fecha_desde'])
                
            if data.get('fecha_hasta'):
                queryset = queryset.filter(fecha_emision__date__lte=data['fecha_hasta'])
                
            if data.get('nit_receptor'):
                queryset = queryset.filter(receptor__nit__icontains=data['nit_receptor'])
                
            if data.get('estado'):
                queryset = queryset.filter(estado=data['estado'])
                
            if data.get('monto_minimo'):
                queryset = queryset.filter(total__gte=data['monto_minimo'])
                
            if data.get('monto_maximo'):
                queryset = queryset.filter(total__lte=data['monto_maximo'])
        
        return queryset.order_by('-fecha_emision')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BusquedaDocumentoForm(self.request.GET)
        return context


class DocumentoDetailView(ContribuyenteRequiredMixin, DetailView):
    """
    Vista para mostrar el detalle de un documento
    """
    model = DocumentoTributario
    template_name = 'emisor/documento_detail.html'
    context_object_name = 'documento'
    
    def get_queryset(self):
        """
        Garantizar que solo se muestren documentos del contribuyente
        """
        contribuyente = self.request.user.contribuyente
        return DocumentoTributario.objects.filter(
            emisor=contribuyente
        ).prefetch_related('lineas')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Añadir info de autorización si existe
        documento = self.get_object()
        try:
            context['autorizacion'] = documento.autorizacion
        except:
            pass
            
        return context


class DocumentoCreateView(ContribuyenteRequiredMixin, CreateView):
    """
    Vista para crear un nuevo documento
    """
    model = DocumentoTributario
    form_class = DocumentoTributarioForm
    template_name = 'emisor/documento_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Pasar el emisor al formulario
        kwargs['emisor'] = self.request.user.contribuyente
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Añadir formset para líneas
        if self.request.POST:
            context['lineas_formset'] = LineaDocumentoFormSet(self.request.POST)
        else:
            context['lineas_formset'] = LineaDocumentoFormSet()
            
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        # Asignar el emisor al documento
        form.instance.emisor = self.request.user.contribuyente
        
        # Validar el formset de líneas
        context = self.get_context_data()
        lineas_formset = context['lineas_formset']
        
        if lineas_formset.is_valid():
            # Guardar el documento
            self.object = form.save()
            
            # Guardar las líneas
            lineas_formset.instance = self.object
            lineas_formset.save()
            
            # Calcular totales
            self.object.subtotal = sum(linea.subtotal for linea in self.object.lineas.all())
            self.object.descuento = sum(linea.descuento for linea in self.object.lineas.all())
            self.object.iva = self.object.calcular_iva()
            self.object.total = self.object.calcular_total()
            self.object.save()
            
            # Cambiar estado a emitido
            self.object.estado = DocumentoTributario.ESTADO_EMITIDO
            self.object.es_borrador = False
            self.object.save()
            
            # Crear solicitud de autorización
            from autoriza.services import crear_solicitud_autorizacion
            autorizacion = crear_solicitud_autorizacion(self.object)
            
            messages.success(self.request, 'Documento creado correctamente y enviado para autorización')
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        return reverse('emisor:documento_detail', kwargs={'pk': self.object.pk})


class DocumentoBorradorCreateView(ContribuyenteRequiredMixin, CreateView):
    """
    Vista para crear un borrador de documento
    """
    model = DocumentoTributario
    form_class = DocumentoTributarioForm
    template_name = 'emisor/documento_borrador_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['emisor'] = self.request.user.contribuyente
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['lineas_formset'] = LineaDocumentoFormSet(self.request.POST)
        else:
            context['lineas_formset'] = LineaDocumentoFormSet()
            
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        form.instance.emisor = self.request.user.contribuyente
        form.instance.estado = DocumentoTributario.ESTADO_BORRADOR
        form.instance.es_borrador = True
        
        context = self.get_context_data()
        lineas_formset = context['lineas_formset']
        
        if lineas_formset.is_valid():
            self.object = form.save()
            
            lineas_formset.instance = self.object
            lineas_formset.save()
            
            # Calcular totales
            self.object.subtotal = sum(linea.subtotal for linea in self.object.lineas.all())
            self.object.descuento = sum(linea.descuento for linea in self.object.lineas.all())
            self.object.iva = self.object.calcular_iva()
            self.object.total = self.object.calcular_total()
            self.object.save()
            
            messages.success(self.request, 'Borrador guardado correctamente')
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        return reverse('emisor:documento_detail', kwargs={'pk': self.object.pk})


class DocumentoBorradorUpdateView(ContribuyenteRequiredMixin, UpdateView):
    """
    Vista para editar un borrador de documento
    """
    model = DocumentoTributario
    form_class = DocumentoTributarioForm
    template_name = 'emisor/documento_borrador_form.html'
    
    def get_queryset(self):
        """
        Solo permitir editar borradores del contribuyente actual
        """
        contribuyente = self.request.user.contribuyente
        return DocumentoTributario.objects.filter(
            emisor=contribuyente,
            estado=DocumentoTributario.ESTADO_BORRADOR,
            es_borrador=True
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['emisor'] = self.request.user.contribuyente
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['lineas_formset'] = LineaDocumentoFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context['lineas_formset'] = LineaDocumentoFormSet(instance=self.object)
            
        return context
    
    @transaction.atomic
    def form_valid(self, form):
        context = self.get_context_data()
        lineas_formset = context['lineas_formset']
        
        if lineas_formset.is_valid():
            self.object = form.save()
            
            lineas_formset.instance = self.object
            lineas_formset.save()
            
            # Recalcular totales
            self.object.subtotal = sum(linea.subtotal for linea in self.object.lineas.all())
            self.object.descuento = sum(linea.descuento for linea in self.object.lineas.all())
            self.object.iva = self.object.calcular_iva()
            self.object.total = self.object.calcular_total()
            self.object.save()
            
            messages.success(self.request, 'Borrador actualizado correctamente')
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))
    
    def get_success_url(self):
        return reverse('emisor:documento_detail', kwargs={'pk': self.object.pk})


class DocumentoBorradorEmitirView(ContribuyenteRequiredMixin, UpdateView):
    """
    Vista para emitir un borrador (convertirlo en documento formal)
    """
    model = DocumentoTributario
    template_name = 'emisor/documento_emitir_confirm.html'
    fields = []  # No necesitamos campos, solo confirmación
    
    def get_queryset(self):
        """
        Solo permitir emitir borradores del contribuyente actual
        """
        contribuyente = self.request.user.contribuyente
        return DocumentoTributario.objects.filter(
            emisor=contribuyente,
            estado=DocumentoTributario.ESTADO_BORRADOR,
            es_borrador=True
        )
    
    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save(commit=False)
        
        # Validar el documento antes de emitirlo
        es_valido, mensaje = self.object.validar_calculos()
        
        if not es_valido:
            messages.error(self.request, f'Error en los cálculos: {mensaje}')
            return HttpResponseRedirect(reverse('emisor:documento_borrador_update', kwargs={'pk': self.object.pk}))
        
        # Cambiar estado a emitido
        self.object.estado = DocumentoTributario.ESTADO_EMITIDO
        self.object.es_borrador = False
        self.object.fecha_emision = timezone.now()
        self.object.save()
        
        # Crear solicitud de autorización
        from autoriza.services import crear_solicitud_autorizacion
        autorizacion = crear_solicitud_autorizacion(self.object)
        
        messages.success(self.request, 'Documento emitido correctamente y enviado para autorización')
        return HttpResponseRedirect(self.get_success_url())
    
    def get_success_url(self):
        return reverse('emisor:documento_detail', kwargs={'pk': self.object.pk})


class EstablecimientoListView(ContribuyenteRequiredMixin, ListView):
    """
    Vista para listar establecimientos del contribuyente
    """
    model = Establecimiento
    template_name = 'emisor/establecimiento_list.html'
    context_object_name = 'establecimientos'
    
    def get_queryset(self):
        contribuyente = self.request.user.contribuyente
        return Establecimiento.objects.filter(contribuyente=contribuyente)


class EstablecimientoCreateView(ContribuyenteRequiredMixin, CreateView):
    """
    Vista para crear un nuevo establecimiento
    """
    model = Establecimiento
    form_class = EstablecimientoForm
    template_name = 'emisor/establecimiento_form.html'
    success_url = reverse_lazy('emisor:establecimiento_list')
    
    def form_valid(self, form):
        form.instance.contribuyente = self.request.user.contribuyente
        messages.success(self.request, 'Establecimiento creado correctamente')
        return super().form_valid(form)


class EstablecimientoUpdateView(ContribuyenteRequiredMixin, UpdateView):
    """
    Vista para actualizar un establecimiento
    """
    model = Establecimiento
    form_class = EstablecimientoForm
    template_name = 'emisor/establecimiento_form.html'
    success_url = reverse_lazy('emisor:establecimiento_list')
    
    def get_queryset(self):
        contribuyente = self.request.user.contribuyente
        return Establecimiento.objects.filter(contribuyente=contribuyente)
    
    def form_valid(self, form):
        messages.success(self.request, 'Establecimiento actualizado correctamente')
        return super().form_valid(form)


class ContribuyenteDetailView(ContribuyenteRequiredMixin, DetailView):
    """
    Vista para mostrar detalles del contribuyente
    """
    model = Contribuyente
    template_name = 'emisor/contribuyente_detail.html'
    context_object_name = 'contribuyente'
    
    def get_object(self):
        return self.request.user.contribuyente