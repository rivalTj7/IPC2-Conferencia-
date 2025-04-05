# core/models.py
from django.db import models


class TimeStampedModel(models.Model):
    """
    Modelo abstracto que proporciona campos de auditoría (created, modified)
    """
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# core/validators.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_nit(value):
    """
    Valida un NIT según el algoritmo:
    1. Multiplique cada carácter por su posición respectiva (siendo la posición 1 el carácter más a la derecha), excepto el último
    2. Sume todos los resultados
    3. Obtenga el módulo 11 de la sumatoria
    4. A 11 réstale el resultado obtenido en el punto 3
    5. Calcule el módulo 11 del resultado obtenido en el punto 4, si este resultado es 10, entonces el dígito verificador del NIT deberá ser K
    """
    # Elimina guiones y otros caracteres especiales
    nit_limpio = ''.join(c for c in value if c.isalnum())
    
    # Verificamos que el NIT tenga al menos 2 caracteres
    if len(nit_limpio) < 2:
        raise ValidationError(
            _('El NIT debe tener al menos 2 caracteres'),
        )
    
    # Separamos el dígito verificador
    digito_verificador = nit_limpio[-1].upper()
    cuerpo = nit_limpio[:-1]
    
    # Verificamos que el cuerpo sea numérico
    if not cuerpo.isdigit():
        raise ValidationError(
            _('El NIT debe contener solo números y el dígito verificador'),
        )
    
    # Calculamos el dígito verificador
    suma = 0
    for i, digito in enumerate(reversed(cuerpo)):
        suma += int(digito) * (i + 2)
    
    modulo = suma % 11
    resultado = 11 - modulo
    resultado_final = resultado % 11
    
    # Convertimos 10 a 'K' para comparar
    digito_esperado = 'K' if resultado_final == 10 else str(resultado_final)
    
    if digito_verificador != digito_esperado:
        raise ValidationError(
            _(f'El dígito verificador del NIT es incorrecto. Debería ser {digito_esperado}'),
        )