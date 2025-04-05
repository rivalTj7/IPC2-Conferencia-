# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from .models import CustomUser
from core.validators import validate_nit


User = get_user_model()


class CustomAuthenticationForm(AuthenticationForm):
    """
    Formulario de autenticación personalizado
    """
    username = forms.EmailField(
        label=_("Correo electrónico"),
        widget=forms.EmailInput(attrs={'autofocus': True, 'class': 'form-control'})
    )
    password = forms.CharField(
        label=_("Contraseña"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    error_messages = {
        'invalid_login': _(
            "Por favor, introduzca un correo electrónico y contraseña correctos. "
            "Note que ambos campos pueden ser sensibles a mayúsculas."
        ),
        'inactive': _("Esta cuenta está inactiva."),
    }


class UserRegistrationForm(UserCreationForm):
    """
    Formulario para registro de nuevos usuarios/contribuyentes
    """
    email = forms.EmailField(
        label=_("Correo electrónico"),
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label=_("Contraseña"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    password2 = forms.CharField(
        label=_("Confirmar contraseña"),
        strip=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )
    first_name = forms.CharField(
        label=_("Nombre"),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label=_("Apellidos"),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    # Campos adicionales para el contribuyente
    nit = forms.CharField(
        label=_("NIT"),
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        validators=[validate_nit]
    )
    nombre_empresa = forms.CharField(
        label=_("Nombre o razón social"),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    nombre_comercial = forms.CharField(
        label=_("Nombre comercial"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    direccion = forms.CharField(
        label=_("Dirección"),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    telefono = forms.CharField(
        label=_("Teléfono"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ('email', 'password1', 'password2', 'first_name', 'last_name')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_("Ya existe un usuario con este correo electrónico."))
        return email
    
    def clean_nit(self):
        nit = self.cleaned_data.get('nit')
        # Eliminar guiones y otros caracteres especiales
        nit_limpio = ''.join(c for c in nit if c.isalnum())
        
        # Verificar que no exista otro contribuyente con el mismo NIT
        from emisor.models import Contribuyente
        if Contribuyente.objects.filter(nit=nit_limpio).exists():
            raise ValidationError(_("Ya existe un contribuyente con este NIT."))
            
        return nit_limpio
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = CustomUser.ROLE_CONTRIBUYENTE
        
        if commit:
            user.save()
            
            # Crear contribuyente asociado
            from emisor.models import Contribuyente
            contribuyente = Contribuyente(
                usuario=user,
                nit=self.cleaned_data.get('nit'),
                nombre=self.cleaned_data.get('nombre_empresa'),
                nombre_comercial=self.cleaned_data.get('nombre_comercial'),
                direccion=self.cleaned_data.get('direccion'),
                correo=user.email,
                telefono=self.cleaned_data.get('telefono')
            )
            contribuyente.save()
            
        return user


class UserProfileForm(forms.ModelForm):
    """
    Formulario para edición de perfil de usuario
    """
    first_name = forms.CharField(
        label=_("Nombre"),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label=_("Apellidos"),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name')