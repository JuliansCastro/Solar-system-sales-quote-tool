# ☀️ Solar Quote Tool
By Ing. Julian A. Castro - 2026

Herramienta web para el diseño y cotización de sistemas de energía solar fotovoltaica, desarrollada con Django.

## Características

- **Dimensionamiento On-Grid y Off-Grid** con integración a la API PVGIS v5.3
- **Inventario de equipos** con CRUD completo (paneles, inversores, baterías, etc.)
- **Gestión de clientes y proyectos** con seguimiento por estados
- **Cotizaciones profesionales** con generación de PDF y Excel
- **Dashboard** con estadísticas y alertas de inventario
- **Gráficos interactivos** con Plotly.js (distribución de costos, ROI, comparativa de consumo)
- **Proyecciones financieras** a 25 años con degradación y escalamiento tarifario
- **Interfaz responsive** con Tailwind CSS

## Stack Tecnológico

| Componente       | Tecnología                     |
|------------------|--------------------------------|
| Backend          | Django 5.1, DRF               |
| Base de datos    | PostgreSQL 16                 |
| Frontend         | Tailwind CSS (CDN), Plotly.js |
| Reportes         | ReportLab (PDF), openpyxl (Excel) |
| API externa      | PVGIS v5.3 (radiación solar) |
| Servidor         | Gunicorn + Nginx              |
| Contenedores     | Docker, Docker Compose        |

## Requisitos Previos

- Python 3.11+
- PostgreSQL 14+
- Docker & Docker Compose (para despliegue)

## Instalación Local

```bash
# 1. Clonar el repositorio
git clone <repo-url>
cd "Solar system sales quote tool"

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuración

# 5. Crear base de datos PostgreSQL
# psql: CREATE DATABASE solar_quote_db;

# 6. Ejecutar migraciones
cd solar_app
python manage.py makemigrations core
python manage.py migrate

# 7. Crear superusuario
python manage.py createsuperuser

# 8. Iniciar servidor de desarrollo
python manage.py runserver
```

La aplicación estará en **http://localhost:8000**

## Despliegue con Docker

```bash
# 1. Configurar .env
cp .env.example .env
# Editar .env (SECRET_KEY, ALLOWED_HOSTS, DB_PASSWORD, etc.)

# 2. Construir e iniciar
docker-compose up -d --build

# 3. Crear superusuario
docker-compose exec web python manage.py createsuperuser

# 4. Acceder
# http://localhost (Nginx en puerto 80)
```

## Estructura del Proyecto

```
solar_app/
├── core/                   # App principal
│   ├── models.py           # User, Cliente, Proyecto, Equipo, Cotización, Carga
│   ├── views.py            # CRUD views, dashboard, sizing, reports
│   ├── forms.py            # Formularios con validaciones
│   ├── sizing.py           # Motor de dimensionamiento solar
│   ├── reports.py          # Generación PDF y Excel
│   ├── signals.py          # Señales Django
│   ├── admin.py            # Configuración del admin
│   └── urls.py             # Rutas de la app
├── templates/              # Templates HTML (Tailwind CSS)
│   ├── base.html
│   └── core/
│       ├── auth/
│       ├── dashboard.html
│       ├── clientes/
│       ├── proyectos/
│       ├── equipos/
│       └── cotizaciones/
├── solar_app/              # Configuración del proyecto
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── manage.py
└── requirements.txt
```

## Módulos Principales

### 1. Motor de Dimensionamiento (`sizing.py`)
- **On-Grid**: Calcula potencia, paneles, generación, ahorro y ROI
- **Off-Grid**: Dimensiona banco de baterías, controlador de carga e inversor
- **PVGIS**: Obtiene datos reales de radiación solar por coordenadas
- **Proyección financiera**: 25 años con degradación del 0.5% anual

### 2. Reportes (`reports.py`)
- **PDF**: Cotización profesional con logo, datos del cliente, tabla de ítems, gráfico de distribución de costos, resumen técnico y condiciones comerciales
- **Excel**: Libro con hoja de cotización detallada y hoja de resumen técnico

### 3. Inventario de Equipos
- 10 categorías: Paneles, Inversores, Baterías, Controladores, Estructura, Cable, Protecciones, Medidores, Conectores, Accesorios
- Especificaciones técnicas completas (potencia, voltaje, corriente, eficiencia, dimensiones, peso)
- Control de stock con alertas

## Configuración de Empresa

Todas las variables de empresa se configuran vía `.env`:

```
COMPANY_NAME=Mi Empresa Solar
COMPANY_NIT=900.123.456-7
COMPANY_PHONE=+57 300 123 4567
COMPANY_EMAIL=ventas@miempresa.com
COMPANY_ADDRESS=Bogotá, Colombia
COMPANY_LOGO=static/img/logo.png
```

## API Endpoints

| Endpoint                         | Método | Descripción                    |
|----------------------------------|--------|--------------------------------|
| `/api/pvgis/`                    | POST   | Consulta radiación solar PVGIS |
| `/api/cotizacion/<pk>/charts/`   | GET    | Datos para gráficos de cotización |

## Licencia

Este proyecto es de uso privado. Todos los derechos reservados.
