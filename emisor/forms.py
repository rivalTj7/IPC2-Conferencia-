# emisor/forms.py
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.forms import inlineformset_factory
from decimal import Decimal

from .models import DocumentoTributario, LineaDocumento, Contribuyente, Establecimiento, TipoDocumento


class ContribuyenteForm(forms.ModelForm):
    """
    Formulario para la gestión de contribuyentes
    """
    class Meta:
        model = Contribuyente
        fields = ['nit', 'nombre', 'nombre_comercial', 'direccion', 'correo', 'telefono']
        widgets = {
            'nit': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_comercial': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'correo': forms.EmailInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }


class EstablecimientoForm(forms.ModelForm):
    """
    Formulario para la gestión de establecimientos
    """
    class Meta:
        model = Establecimiento
        fields = ['codigo', 'nombre', 'direccion', 'activo']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DocumentoTributarioForm(forms.ModelForm):
    """
    Formulario para la emisión de documentos tributarios
    """
    nit_receptor = forms.CharField(
        label=_("NIT del receptor"),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True,
        help_text=_("Ingrese el NIT del receptor sin guiones.")
    )
    
    class Meta:
        model = DocumentoTributario
        fields = [
            'tipo_documento', 'referencia_interna', 'establecimiento',
            'moneda', 'observaciones'
        ]
        widgets = {
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'referencia_interna': forms.TextInput(attrs={'class': 'form-control'}),
            'establecimiento': forms.Select(attrs={'class': 'form-select'}),
            'moneda': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        # El emisor debe ser pasado al formulario para filtrar establecimientos
        self.emisor = kwargs.pop('emisor', None)
        super().__init__(*args, **kwargs)
        
        # Cargar solo tipos de documento activos
        self.fields['tipo_documento'].queryset = TipoDocumento.objects.filter(activo=True)
        
        # Si hay un emisor, filtrar establecimientos
        if self.emisor:
            self.fields['establecimiento'].queryset = Establecimiento.objects.filter(
                contribuyente=self.emisor,
                activo=True
            )
        else:
            self.fields['establecimiento'].queryset = Establecimiento.objects.none()
    
    def clean_nit_receptor(self):
        """
        Validar el NIT del receptor y buscar o crear el contribuyente
        """
        from core.validators import validate_nit
        
        nit = self.cleaned_data.get('nit_receptor')
        # Limpiar NIT
        nit_limpio = ''.join(c for c in nit if c.isalnum())
        
        try:
            # Validar formato del NIT
            validate_nit(nit_limpio)
            
            # Buscar contribuyente por NIT
            receptor = Contribuyente.objects.filter(nit=nit_limpio).first()
            if not receptor:
                raise ValidationError(_("No existe un contribuyente con el NIT proporcionado."))
                
            return receptor
        except ValidationError as e:
            raise ValidationError(e)
    
    def clean(self):
        """
        Validar que no exista un documento con la misma referencia para el emisor en la misma fecha
        """
        cleaned_data = super().clean()
        
        # Si faltan datos básicos, no seguir validando
        if not self.emisor or 'referencia_interna' not in cleaned_data:
            return cleaned_data
            
        referencia = cleaned_data.get('referencia_interna')
        
        # Buscar documentos existentes con la misma referencia (para el mismo día)
        from django.utils import timezone
        import datetime
        
        hoy = timezone.now().date()
        
        # Filtrar documentos de hoy con la misma referencia y emisor
        existe = DocumentoTributario.objects.filter(
            emisor=self.emisor,
            referencia_interna=referencia,
            fecha_emision__date=hoy
        ).exists()
        
        if existe:
            self.add_error(
                'referencia_interna', 
                _("Ya existe un documento con esta referencia para el día de hoy.")
            )
        
        return cleaned_data
    
    def save(self, commit=True):
        """
        Guardar el documento con los datos calculados
        """
        documento = super().save(commit=False)
        
        # Asignar emisor y receptor
        documento.emisor = self.emisor
        documento.receptor = self.cleaned_data.get('nit_receptor')
        
        # Calcular totales basados en las líneas (si ya existen)
        if documento.pk:
            lineas = documento.lineas.all()
            documento.subtotal = sum(linea.subtotal for linea in lineas)
            documento.descuento = sum(linea.descuento for linea in lineas)
            documento.iva = documento.calcular_iva()
            documento.total = documento.calcular_total()
        
        if commit:
            documento.save()
        
        return documento


class LineaDocumentoForm(forms.ModelForm):
    """
    Formulario para líneas de documento
    """
    class Meta:
        model = LineaDocumento
        fields = ['descripcion', 'cantidad', 'precio_unitario', 'descuento']
        widgets = {
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'cantidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'precio_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'descuento': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }
    
    def clean(self):
        """
        Validar y calcular el subtotal
        """
        cleaned_data = super().clean()
        
        cantidad = cleaned_data.get('cantidad')
        precio_unitario = cleaned_data.get('precio_unitario')
        descuento = cleaned_data.get('descuento', Decimal('0.00'))
        
        if cantidad and precio_unitario:
            # Calcular el subtotal
            subtotal = (cantidad * precio_unitario) - descuento
            
            # Validar que el descuento no sea mayor que el valor total
            if descuento and descuento > (cantidad * precio_unitario):
                self.add_error('descuento', _("El descuento no puede ser mayor que el valor total."))
                
            cleaned_data['subtotal'] = subtotal
        
        return cleaned_data


# Formset para gestionar múltiples líneas de documento
LineaDocumentoFormSet = inlineformset_factory(
    DocumentoTributario,
    LineaDocumento,
    form=LineaDocumentoForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class BusquedaDocumentoForm(forms.Form):
    """
    Formulario para búsqueda de documentos
    """
    ESTADO_CHOICES = [
        ('', 'Todos los estados'),
    ] + list(DocumentoTributario.ESTADOS)
    
    referencia = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    nit_receptor = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    monto_minimo = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
    )
    monto_maximo = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
    )