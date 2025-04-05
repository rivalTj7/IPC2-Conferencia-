# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """
    Manager personalizado para CustomUser que permite usar email como
    identificador único en lugar de username.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Crea y guarda un usuario con el email y password dados.
        """
        if not email:
            raise ValueError(_('El Email es obligatorio'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crea y guarda un superusuario con el email y password dados.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
            
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Modelo de usuario personalizado que usa email como identificador único
    en lugar de username.
    """
    ROLE_ADMIN = 'ADMIN'
    ROLE_CONTRIBUYENTE = 'CONTRIBUYENTE'
    ROLE_AUDITOR = 'AUDITOR'
    
    ROLES = [
        (ROLE_ADMIN, _('Administrador')),
        (ROLE_CONTRIBUYENTE, _('Contribuyente')),
        (ROLE_AUDITOR, _('Auditor')),
    ]
    
    username = None
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(_('rol'), max_length=20, choices=ROLES, default=ROLE_CONTRIBUYENTE)
    
    # Control de acceso al sistema
    login_attempts = models.PositiveIntegerField(default=0)
    last_login_attempt = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.email
    
    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN
        
    @property
    def is_contribuyente(self):
        return self.role == self.ROLE_CONTRIBUYENTE
        
    @property
    def is_auditor(self):
        return self.role == self.ROLE_AUDITOR
        
    def get_full_name(self):
        """
        Retorna el nombre completo del usuario
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip() or self.email
        
    def get_short_name(self):
        """
        Retorna el nombre corto del usuario
        """
        return self.first_name or self.email.split('@')[0]