# IPC2-Conferencia-

# SIGTE - Simulador de Gestiones

SIGTE es un sistema integral para la gestión de Documentos desarrollado con Django. El sistema permite la emisión, validación, autorización y consulta de documentos, implementando un flujo completo desde la emisión hasta la autorización.

![SIGTE Dashboard](/screenshots/dashboard.png)

## Características

- Emisión y gestión de documentos tributarios electrónicos
- Validación automática de documentos según reglas tributarias
- Autorización de documentos con generación de números de autorización únicos
- Gestión de contribuyentes y establecimientos
- Reportes y estadísticas con visualizaciones gráficas
- Exportación de datos en formatos CSV y PDF
- API REST completa para integración con otros sistemas
- Sistema de autenticación con múltiples roles (Contribuyente, Auditor, Administrador)
- Interfaz de usuario intuitiva y responsive

## Requisitos del Sistema

- Python 3.8 o superior
- PostgreSQL (recomendado para producción) o SQLite (desarrollo)
- Pip y Virtualenv
- Node.js y npm (opcional, para herramientas de frontend)

## Estructura del Proyecto

```
sigte/
├── accounts/                   # App de usuarios y autenticación
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py                # Formularios de registro, login, perfil
│   ├── managers.py             # Manager personalizado para usuarios
│   ├── models.py               # Modelos de usuario, perfil, contribuyente
│   ├── tests/
│   ├── urls.py
│   └── views.py
├── api/                        # App para la API REST
│   ├── migrations/
│   ├── __init__.py
│   ├── apps.py
│   ├── permissions.py          # Permisos personalizados para la API
│   ├── serializers.py          # Serializadores para los modelos
│   ├── tests/
│   ├── urls.py
│   ├── validators.py
│   └── views.py                # ViewSets y vistas de API
├── autoriza/                   # App para proceso de autorización de DTE
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py
│   ├── models.py               # Modelos para autorización y validación
│   ├── services.py             # Servicios de negocio para autorizaciones
│   ├── tasks.py                # Tareas asíncronas (para Celery)
│   ├── tests/
│   ├── urls.py
│   └── views.py
├── consulta/                   # App para consultas y reportes
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py                # Formularios para búsquedas y filtros
│   ├── models.py
│   ├── reports.py              # Generadores de reportes
│   ├── tests/
│   ├── urls.py
│   └── views.py
├── core/                       # App para funcionalidad central y compartida
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── context_processors.py   # Procesadores de contexto
│   ├── middleware.py           # Middleware personalizado
│   ├── models.py               # Modelos abstractos y bases
│   ├── templatetags/           # Tags y filtros personalizados
│   ├── tests/
│   ├── urls.py
│   ├── utils.py                # Funciones de utilidad
│   ├── validators.py           # Validadores comunes (NIT, etc.)
│   └── views.py
├── emisor/                     # App para emisión de documentos
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py                # Formularios para emisión de DTE
│   ├── models.py               # Modelos para DTE, productos, etc.
│   ├── services.py             # Servicios de negocio para emisión
│   ├── tests/
│   ├── urls.py
│   └── views.py
├── media/                      # Archivos cargados por usuarios
├── sigte/                      # Configuración principal del proyecto
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py             # Configuración base
│   │   ├── development.py      # Configuración para desarrollo
│   │   ├── production.py       # Configuración para producción
│   │   └── test.py             # Configuración para pruebas
│   ├── urls.py                 # URLs principales
│   └── wsgi.py
├── static/                     # Archivos estáticos
│   ├── css/
│   ├── img/
│   ├── js/
│   └── vendor/                 # Bibliotecas de terceros
├── templates/                  # Templates base del proyecto
│   ├── 400.html
│   ├── 403.html
│   ├── 404.html
│   ├── 500.html
│   ├── base.html              # Template base
│   ├── dashboard.html         # Template para dashboard
│   ├── emails/                # Templates para correos
│   └── includes/              # Componentes reutilizables
├── .dockerignore
├── .env.example                # Ejemplo de variables de entorno
├── .gitignore
├── docker-compose.yml          # Configuración Docker
├── Dockerfile
├── LICENSE
├── manage.py
├── README.md
└── requirements/
    ├── base.txt               # Dependencias base
    ├── development.txt        # Dependencias para desarrollo
    ├── production.txt         # Dependencias para producción
    └── test.txt               # Dependencias para pruebas
```

## Instalación y Configuración

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/sigte.git
cd sigte
```

### 2. Configurar Entorno Virtual

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows:
venv\Scripts\activate
# En Linux/Mac:
source venv/bin/activate
```

### 3. Instalar Dependencias

```bash
# Para desarrollo
pip install -r requirements/development.txt

# Para producción
pip install -r requirements/production.txt
```

### 4. Configurar Variables de Entorno

Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:

```
# Desarrollo
DJANGO_SETTINGS_MODULE=sigte.settings.development
DJANGO_SECRET_KEY=una-clave-secreta-segura

# Producción
DJANGO_SETTINGS_MODULE=sigte.settings.production
DJANGO_SECRET_KEY=una-clave-secreta-muy-segura
DJANGO_ALLOWED_HOST=sigte.example.com
DB_NAME=sigte_db
DB_USER=sigte_user
DB_PASSWORD=contraseña-segura
DB_HOST=localhost
DB_PORT=5432
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=user@example.com
EMAIL_HOST_PASSWORD=contraseña-email
DEFAULT_FROM_EMAIL=sigte@example.com
```

### 5. Crear Base de Datos

Para SQLite (desarrollo):
- No se requiere configuración adicional.

Para PostgreSQL (producción):
```bash
# Crear base de datos
createdb sigte_db

# O usar SQL
CREATE DATABASE sigte_db;
CREATE USER sigte_user WITH PASSWORD 'contraseña-segura';
GRANT ALL PRIVILEGES ON DATABASE sigte_db TO sigte_user;
```

### 6. Aplicar Migraciones

```bash
python manage.py migrate
```

### 7. Cargar Datos Iniciales

```bash
python manage.py loaddata fixtures/initial_data.json
```

### 8. Crear Superusuario

```bash
python manage.py createsuperuser
```

### 9. Compilar Archivos Estáticos (Producción)

```bash
python manage.py collectstatic
```

### 10. Ejecutar Servidor de Desarrollo

```bash
python manage.py runserver
```

El sistema estará disponible en [http://localhost:8000](http://localhost:8000)

## Despliegue en Producción

### Usando Docker

1. Construir la imagen:
```bash
docker-compose build
```

2. Ejecutar los contenedores:
```bash
docker-compose up -d
```

### Configuración Manual

1. Configurar Gunicorn:
```bash
gunicorn sigte.wsgi:application --bind 0.0.0.0:8000
```

2. Configurar Nginx como proxy inverso:
```nginx
server {
    listen 80;
    server_name sigte.example.com;
    
    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        root /ruta/a/sigte;
    }
    
    location /media/ {
        root /ruta/a/sigte;
    }
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

3. Configurar servicio systemd:
```ini
[Unit]
Description=SIGTE Gunicorn Service
After=network.target

[Service]
User=usuario
Group=usuario
WorkingDirectory=/ruta/a/sigte
ExecStart=/ruta/a/sigte/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:8000 sigte.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Uso del Sistema

### Roles de Usuario

El sistema SIGTE implementa tres roles principales de usuario:

1. **Contribuyente**: Empresas o personas que emiten documentos tributarios.
   - Puede emitir y consultar sus propios documentos
   - Gestionar sus establecimientos y sucursales
   - Ver reportes básicos de su actividad

2. **Auditor**: Personal de la administración tributaria.
   - Puede consultar todos los documentos
   - Generar reportes y estadísticas
   - Ver análisis de actividad por contribuyente

3. **Administrador**: Gestión del sistema.
   - Acceso completo a todas las funcionalidades
   - Gestión de usuarios y roles
   - Configuración del sistema

### Flujo Principal

1. **Registro de Contribuyente**:
   - El usuario se registra como contribuyente
   - Proporciona información fiscal (NIT, nombre, dirección)
   - Crea su primer establecimiento comercial

2. **Emisión de Documentos**:
   - El contribuyente crea un nuevo documento
   - Ingresa información del receptor y detalle del documento
   - El sistema calcula automáticamente los impuestos (IVA)
   - Se confirma la emisión del documento

3. **Autorización de Documentos**:
   - El sistema valida automáticamente el documento
   - Verifica NIT de emisor y receptor, cálculos de IVA y total
   - Si es válido, genera un número de autorización único
   - Si hay errores, se rechaza con motivos detallados

4. **Consulta y Reportes**:
   - Los contribuyentes pueden consultar sus documentos emitidos
   - Los auditores pueden generar reportes por fecha, contribuyente, montos
   - Se pueden exportar datos a CSV y PDF
   - Se generan gráficas para análisis visual

## API REST

El sistema expone una API REST completa para integración con otros sistemas:

- Base URL: `/api/v1/`
- Documentación: `/api/docs/`

### Autenticación

```bash
# Obtener token
curl -X POST http://localhost:8000/api/v1/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "usuario@example.com", "password": "contraseña"}'

# Usar token en solicitudes
curl -X GET http://localhost:8000/api/v1/documentos/ \
  -H "Authorization: Bearer eyJ0eXAiO..."
```

### Endpoints Principales

- `GET /api/v1/documentos/`: Listar documentos
- `POST /api/v1/documentos/`: Crear documento
- `GET /api/v1/documentos/{id}/`: Detalle de documento
- `POST /api/v1/documentos/{id}/emitir/`: Emitir documento borrador
- `GET /api/v1/autorizaciones/`: Listar autorizaciones
- `GET /api/v1/estadisticas/`: Obtener estadísticas
- `GET /api/v1/verificar-documento/?numero_autorizacion=X&nit_emisor=Y`: Verificar validez de documento

## Desarrollo

### Pruebas

Para ejecutar las pruebas unitarias:
```bash
python manage.py test
```

Para verificar la cobertura de pruebas:
```bash
coverage run --source='.' manage.py test
coverage report
```

### Linting y Formato

```bash
# Verificar estilo con flake8
flake8 .

# Formatear código con black
black .
```

### Desarrollo Frontend

El proyecto utiliza Bootstrap 5 para los estilos base y Chart.js para las visualizaciones.

Para trabajar con los archivos CSS/JS:
```bash
# Si se usa npm para compilar assets
npm install
npm run dev   # Desarrollo
npm run build # Producción
```

## Características Técnicas Destacadas

### Validación de NIT

El sistema implementa el algoritmo oficial para validación de NIT:
1. Se multiplica cada dígito por su posición (de derecha a izquierda)
2. Se suma los resultados
3. Se calcula el módulo 11 de la suma
4. Se resta de 11
5. Se verifica el dígito verificador (puede ser "K" si el resultado es 10)

### Generación de Números de Autorización

El formato de autorización sigue el patrón `YYYYMMDD########`:
- `YYYY`: Año de emisión
- `MM`: Mes de emisión
- `DD`: Día de emisión
- `########`: Correlativo diario iniciando en 1 (con ceros a la izquierda)

### Arquitectura del Sistema

El sistema sigue una arquitectura de tres capas:
1. **Capa de Presentación**: Templates de Django y JavaScript
2. **Capa de Lógica de Negocio**: Servicios, formularios y vistas de Django
3. **Capa de Datos**: Modelos y ORM de Django

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## Contribuir

1. Haz un fork del repositorio
2. Crea una rama para tu función (`git checkout -b feature/amazing-feature`)
3. Haz commit de tus cambios (`git commit -m 'Add amazing feature'`)
4. Push a la rama (`git push origin feature/amazing-feature`)
5. Abre un Pull Request

## Contacto

- Email: [rival.alex7@gmail.com](mailto:tu-email@example.com)