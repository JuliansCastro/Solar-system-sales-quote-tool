# ☀️ Solar Quote Tool
By Ing. Julian A. Castro - 2026

![Coverage Gate](https://img.shields.io/badge/coverage-gate%20%3E%3D%2070%25-brightgreen)

Herramienta web integral para el diseño, dimensionamiento y cotización de sistemas de energía solar fotovoltaica, desarrollada con Django. Sistema modular con selección de equipos en tiempo real, validación de compatibilidad y generación automática de reportes profesionales.

## 📋 Tabla de Contenidos
1. [Características](#características)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Instalación Local](#instalación-local)
4. [Despliegue con Docker](#despliegue-con-docker)
5. [Sistema de Backups](#respaldo-y-recuperación-de-base-de-datos)
6. [Estructura del Proyecto](#estructura-del-proyecto)
7. [Sistema de Selección de Equipos](#-sistema-modular-de-selección-de-equipos)
8. [Guía de Implementación](#-guía-de-implementación-equipment-based-sizing)
9. [API Endpoints](#api-endpoints)

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

## Seguridad API y Observabilidad

### JWT para API externa (v1)

Endpoints:

- `POST /api/v1/auth/token/`
- `POST /api/v1/auth/token/refresh/`
- `POST /api/v1/auth/token/verify/`

Header para endpoints protegidos:

```http
Authorization: Bearer <access_token>
```

### Variables de entorno relevantes

```env
# Feature flags
API_V1_ENABLED=true
LEGACY_API_DEPRECATION_HEADERS_ENABLED=true

# JWT
JWT_ACCESS_MINUTES=30
JWT_REFRESH_DAYS=7
JWT_ROTATE_REFRESH_TOKENS=true

# Observabilidad
METRICS_ENABLED=true
SENTRY_DSN=
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
DJANGO_LOG_LEVEL=INFO
```

### Métricas y logs

- Métricas Prometheus: `GET /metrics`
- Logs estructurados JSON a stdout (listos para agregadores como Loki/ELK)
- Errores a Sentry si `SENTRY_DSN` está configurado

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

## Respaldo y Recuperación de Base de Datos

El proyecto incluye un sistema **100% integrado en la aplicación Django** de backups automáticos con checksums SHA-256 que se ejecuta en segundo plano sin servicios externos.

### 1. Backups Automáticos (Activados en Producción)

Cuando la app corre con `DEBUG=False`, **APScheduler inicia automáticamente** en segundo plano los trabajos de backup.

**Configuración (`.env`):**

```env
# Backups horarios (cada 1 hora, mantiene últimos 7 días)
BACKUP_HOURLY_ENABLED=true
BACKUP_INTERVAL_HOURS=1
BACKUP_RETENTION_HOURS=168

# Backups mensuales (1er día a las 3:30 AM, mantiene últimos 3 meses)
BACKUP_MONTHLY_ENABLED=true
BACKUP_RETENTION_MONTHS=2592
BACKUP_MONTHLY_DAY=1
BACKUP_MONTHLY_HOUR=3
BACKUP_MONTHLY_MINUTE=30

# Simulacro de restauración mensual (DESHABILITADO por defecto)
BACKUP_MONTHLY_DRILL_ENABLED=false
BACKUP_DRILL_DAY=15
BACKUP_DRILL_HOUR=4
BACKUP_DRILL_MINUTE=0

# Ubicación de backups
BACKUP_DIR=./backups
```

### 2. Crear Backup Manual (En Cualquier Momento)

```bash
cd solar_app
python manage.py backup_db --label before-deploy
```

Resultado en `solar_app/backups/`:
```
20260314_120015_sqlite3_before-deploy.sqlite3.gz    # Base de datos comprimida
20260314_120015_sqlite3_before-deploy.sha256        # SHA256 para validar integridad
20260314_120015_sqlite3_before-deploy.json          # Metadata (timestamp, engine, hash)
```

Opciones útiles:

```bash
# Especificar retención (remover backups antiguos después de X horas)
python manage.py backup_db --label monthly --retention-hours 2592

# No eliminar backups antiguos
python manage.py backup_db --label test --skip-purge

# Especificar directorio personalizado
python manage.py backup_db --output-dir C:/solar-backups --label custom
```

### 3. Restaurar desde Backup

```bash
cd solar_app
python manage.py restore_db C:/ruta/backup_20260314_120015_sqlite3_before-deploy.sqlite3.gz --yes-i-know
```

**⚠️ Advertencia importante:** Este comando destruye la base de datos actual y la reemplaza. El flag `--yes-i-know` es **obligatorio**.

### 4. Estado del Scheduler

Ver próximos trabajos programados:

```bash
cd solar_app
python manage.py manage_scheduler status
```

Salida esperada:
```
Backup Scheduler Status
============================================================
Running: True

Scheduled Jobs:
------------------------------------------------------------
  • Hourly Database Backup
    ID: backup_hourly
    Next Run: 2026-03-14T12:00:00+00:00

  • Monthly Database Backup
    ID: backup_monthly
    Next Run: 2026-04-01T03:30:00+00:00
```

### 5. Validar Integridad de Backups

```bash
# Windows PowerShell
cd solar_app/backups
$file = "20260314_120015_sqlite3_before-deploy.sqlite3.gz"
$hash = (Get-FileHash -Path $file -Algorithm SHA256).Hash
(Get-Content "$file.sha256").Trim() -eq $hash

# Linux/macOS
cd solar_app/backups
file="20260314_120015_sqlite3_before-deploy.sqlite3.gz"
stored_hash=$(cat "$file.sha256" | cut -d' ' -f1)
actual_hash=$(sha256sum "$file" | cut -d' ' -f1)
[ "$stored_hash" = "$actual_hash" ] && echo "✅ Backup íntegro" || echo "❌ Backup corrupto"
```

### 6. Arquitectura

```
Django App (DEBUG=False)
    ↓
    apps.py → ready()
    ↓
    APScheduler inicia en background
    ├── Job 1: Hourly Backup (cada 1 hora)
    │   └── call_command('backup_db', label='hourly')
    │
    ├── Job 2: Monthly Backup (1er día 3:30 AM)
    │   └── call_command('backup_db', label='monthly')
    │
    └── Job 3: Monthly Restore Drill (si habilitado)
        ├── Crear guard backup
        ├── Restaurar último backup
        └── Django health check (manage.py check)
```

**Ventajas:**
- ✅ Sin depender de cron, Task Scheduler, o servicios externos
- ✅ Funciona en **Windows, Linux, macOS** sin cambios
- ✅ Logging integrado en Django (`django.log`)
- ✅ APScheduler maneja timezone automáticamente
- ✅ Fácil de testear en desarrollo

### 7. Desarrollo & Testing

**Forzar un backup ahora:**

```bash
python manage.py backup_db --label debug-now --skip-purge
```

**Ejecutar restore drill manual:**

```bash
python manage.py backup_db --label pre-drill-guard --retention-hours 2592
# ... luego restore ...
python manage.py restore_db <backup_path> --yes-i-know
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

---

## 🔧 Sistema Modular de Selección de Equipos

### 📋 Descripción

Implementación completa de un sistema modular para la selección de equipos solares durante el dimensionamiento de proyectos, con recálculo automático de generación, validación de compatibilidad y explicaciones persuasivas para los gráficos.

### 🏗️ Arquitectura

```
Backend
├── models.py
│   ├── SelectedEquipo         # Equipos seleccionados por proyecto
│   ├── EquipoCompatibilidad   # Reglas de validación
│   └── ChartExplanation       # Explicaciones de gráficos
├── equipment_sizing.py        # Motor de cálculo modular
├── api_equipment.py           # Endpoints REST
├── forms.py                   # Formularios (SelectedEquipoForm, etc.)
└── urls.py                    # Rutas API

Frontend
├── static/js/
│   ├── equipment-selector.js  # Selector de equipos (componente reutilizable)
│   ├── chart-updater.js       # Actualización de gráficos en tiempo real
│   └── notifications.js       # Notificaciones y alertas
└── templates/core/proyectos/
    └── proyecto_dimensionamiento.html # Template con tabs integrados
```

### 🔧 Componentes Principales

#### Backend: Modelos (models.py)

**SelectedEquipo**
Registra qué equipos ha seleccionado el usuario para cada proyecto.

```python
SelectedEquipo(
    proyecto=Proyecto,
    equipo=Equipo,
    tipo_equipo='panel'|'inversor'|'estructura'|'regulador'|'bateria',
    cantidad=int,
    notas=str,
    perdidas_estimadas_porcentaje=float,  # Cacheado
    generacion_afectada_kwh=float         # Cacheado
)
```

**EquipoCompatibilidad**
Define reglas de validación entre equipos (voltaje, corriente, potencia, etc.).

```python
EquipoCompatibilidad(
    equipo_base=Equipo,
    equipo_compatible=Equipo,
    tipo_validacion='voltaje'|'corriente'|'potencia'|'tecnologia'|'custom',
    valor_minimo=float,
    valor_maximo=float,
    es_critico=bool,
    mensaje_alerta=str
)
```

**ChartExplanation**
Almacena explicaciones personalizadas para cada gráfico en PDF y UI.

```python
ChartExplanation(
    proyecto=Proyecto,
    tipo_grafico='consumo_generacion'|'roi_acumulado'|...,
    titulo_corto=str,
    explicacion_tecnica=str,
    puntos_clave=str,
    recomendaciones=str,
    es_personalizada=bool
)
```

#### Backend: Motor de Cálculo (equipment_sizing.py)

Implementa cálculos precisos basados en equipos reales seleccionados.

**Funciones Principales**

- **`calculate_generation_with_equipment()`**: Calcula potencia instalada real, estima pérdidas por componente, calcula generación mensual y cobertura, determina retorno de inversión, valida compatibilidad
- **`estimate_system_losses()`**: Pérdidas por panel (eficiencia), inversor (eficiencia), cableado (1.5%), transformador (0.5%), misceláneas (1.0%)
- **`validate_equipment_compatibility()`**: Valida compatibilidad entre equipos, retorna lista de problemas, distingue entre críticos y advertencias
- **`get_equipment_suggestions()`**: Sugiere equipos óptimos basado en resultado de sizing

**Modelo de Pérdidas:**
- Panel: 2-5% (según eficiencia)
- Inversor: 3-8% (según eficiencia)
- Cableado: 1.5%
- Transformador: 0.5%
- Otros: 1.0%

**Fórmula:** Total pérdidas = 100 × (1 - (1-L₁)(1-L₂)...(1-Lₙ))

#### Backend: API REST (api_equipment.py)

Endpoints AJAX para selección y cálculo en tiempo real.

```
GET  /api/equipment/list/
POST /api/proyectos/<id>/equipment/select/
POST /api/proyectos/<id>/equipment/<seleccion_id>/remove/
POST /api/proyectos/<id>/recalculate/
POST /api/proyectos/<id>/check-compatibility/
```

**Respuesta de Ejemplo:**
```json
{
  "success": true,
  "resultado": {
    "potencia_pico_kwp": 6.8,
    "generacion_mensual_kwh": 294,
    "perdidas_totales_porcentaje": 28.4,
    "roi_anos": 7.2,
    "alertas": []
  },
  "validaciones": [
    {
      "tipo": "voltaje",
      "nivel": "critico",
      "mensaje": "Inversor no soporta voltaje del panel"
    }
  ]
}
```

#### Frontend: Componente EquipmentSelector (equipment-selector.js)

Clase reutilizable para seleccionar equipos con interfaz completa.

```javascript
const selector = new EquipmentSelector('#container', proyectoId, {
  autoRecalculate: true,
  showNotifications: true,
});
selector.init();

// Eventos
window.addEventListener('equipmentRecalculated', (e) => {
  console.log(e.detail); // Resultado de cálculo
});
```

**Características:**
- Búsqueda y filtrado en tiempo real
- Validación de cantidad
- Actualización dinámica de lista
- Gestión de estado local

#### Frontend: Actualizador de Gráficos (chart-updater.js)

Actualiza gráficos con explicaciones persuasivas en tiempo real.

```javascript
const chartUpdater = new ChartUpdateSystem(proyectoId);

window.addEventListener('equipmentRecalculated', (e) => {
  chartUpdater.updateAll(e.detail);
});
```

**Gráficos Actualizados:**
1. Consumo vs Generación
2. ROI Acumulado
3. Radiación Solar Mensual
4. Horas Solar Pico

### 📡 Flujo de Datos

```
Usuario selecciona equipo
    ↓
API: /api/proyectos/<id>/equipment/select/ (POST)
    ↓
Backend: SelectedEquipo.objects.create()
    ↓
API: /api/proyectos/<id>/recalculate/ (POST)
    ↓
Backend: calculate_generation_with_equipment()
    ├─ Calcula potencia real
    ├─ Estima pérdidas
    ├─ Valida compatibilidad
    └─ Retorna resultado
    ↓
Frontend: equipmentRecalculated event
    ↓
Frontend: chartUpdater.updateAll(resultado)
    ├─ Actualiza gráficos Plotly
    └─ Muestra explicaciones nuevas
```

### 🔍 Validaciones

**Nivel Modelo**
- Stock suficiente
- Cantidad positiva
- Equipo activo

**Nivel API**
- Autorización de usuario
- Integridad de datos
- Errores HTTP apropiados

**Nivel Compatibilidad**
- Voltaje compatible
- Corriente dentro de rango
- Potencia adecuada
- Tecnología compatible

### 🎨 Interfaz de Usuario

**Panel de Selección**
- Filtros: tipo, categoría, fabricante, rango potencia, stock
- Búsqueda fuzzy
- Cantidad configurable
- Botones de agregar/remover

**Resumen de Equipos**
- Listado dinámico
- Costo subtotal por equipo
- Costo total del sistema
- Alertas de compatibilidad

**Gráficos Actualizados**
- Consumo vs Generación (con % cobertura)
- ROI (puntos clave financieros)
- Radiación (mes mínimo resaltado)
- HSP (línea de promedio)

### 📊 Explicaciones en PDF

Cada gráfico incluye:
- **Título descriptivo**
- **Explicación técnica** (2-3 párrafos)
- **Puntos clave** (bullets)
- **Recomendaciones** (opcional)

---

## 🚀 Guía de Implementación (Equipment-Based Sizing)

### Quick Start

#### 1. Aplicar Migraciones de Base de Datos

```bash
cd solar_app
python manage.py makemigrations core
python manage.py migrate
```

**Modelos afectados:**
- `SelectedEquipo`: Equipos seleccionados por proyecto
- `EquipoCompatibilidad`: Reglas de validación
- `ChartExplanation`: Explicaciones de gráficos

#### 2. Verificar Admin Django

Accede a `/admin/` y verifica:
- **Core > Selected Equipos**
- **Core > Equipo Compatibilidades**
- **Core > Chart Explanations**

#### 3. Cargar Reglas de Compatibilidad Iniciales

```bash
python manage.py shell

from core.models import EquipoCompatibilidad, Equipo
# Agregar tus reglas de compatibilidad aquí
```

### Funciones Principales

#### calculate_generation_with_equipment()

```python
def calculate_generation_with_equipment(
    selected_equipos: List[Dict],
    consumo_mensual_kwh: float,
    hsp: float,
    tarifa_cop_kwh: float
) -> EquipmentSizingResult
```

**Qué hace:**
- Toma lista de equipos seleccionados (paneles, inversores, etc.)
- Calcula capacidad total del sistema (kWp)
- Estima generación mensual contabilizando pérdidas reales de todos los equipos
- Calcula ROI basado en tarifa real
- Retorna resultado detallado con todos los cálculos

**Ejemplo de uso:**
```python
from core.equipment_sizing import calculate_generation_with_equipment

selected_eq = [
    {'tipo': 'panel', 'equipo': panel_obj, 'cantidad': 20},
    {'tipo': 'inversor', 'equipo': inversor_obj, 'cantidad': 1}
]

result = calculate_generation_with_equipment(
    selected_equipos=selected_eq,
    consumo_mensual_kwh=300,
    hsp=4.5,
    tarifa_cop_kwh=750
)

print(f"Capacidad del sistema: {result.potencia_pico_kwp} kWp")
print(f"Generación mensual: {result.generacion_mensual_kwh} kWh")
print(f"Pérdidas totales: {result.perdidas_totales_porcentaje}%")
print(f"ROI: {result.roi_anos} años")
```

### Pruebas

#### Unitarias

```bash
python manage.py test core.tests.test_equipment_sizing
python manage.py test core.tests.test_equipment_compatibility
```

#### Integración

```bash
python manage.py test core.tests.test_api_equipment
```

#### Manual

Checklist de validación:
- [ ] Login en admin y crear al menos una regla de compatibilidad
- [ ] Navegar a "Dimensionamiento" de un proyecto
- [ ] Click en tab "Seleccionar equipos"
- [ ] Buscar y filtrar equipos por tipo, potencia
- [ ] Seleccionar 10 paneles (ej: 400W = 4kWp)
- [ ] Verificar que "Generación mensual" recalcula automáticamente
- [ ] Verificar que gráficos se actualicen en tiempo real
- [ ] Agregar equipo incompatible y verificar mensaje de alerta
- [ ] Remover equipo y verificar recálculo de gráficos
- [ ] Verificar que selección se guarde al refrescar página

### Configuración

#### Variables de Entorno

```python
# settings.py
EQUIPMENT_SELECTION_ENABLED = True
CHART_EXPLANATIONS_ENABLED = True
MAX_EQUIPMENT_PER_PROJECT = 50  # Prevent abuse
```

#### Pérdidas por Defecto

Ajustar en `core/equipment_sizing.py`:

```python
DEFAULT_LOSSES = {
    'panel': 0.025,           # 2.5% si no viene de equipo.eficiencia
    'inversor': 0.05,         # 5%
    'cableado': 0.015,        # 1.5%
    'transformador': 0.005,   # 0.5%
    'otros': 0.01             # 1.0%
}
```

### Problemas Comunes

**Migración falla con "column already exists"**
```bash
python manage.py migrate core --fake
python manage.py migrate
```

**Token CSRF faltante en requests AJAX**
```javascript
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Usar en fetch:
headers: {'X-CSRFToken': getCookie('csrftoken')}
```

**Gráficos no se actualizan tras selección**
1. Verificar que `chart-updater.js` se carga DESPUÉS de Plotly
2. Verificar que event listener esté registrado: `window.addEventListener('equipmentRecalculated', ...)`
3. Revisar consola del browser para errores
4. Verificar que API retorna `resultado` con campos requeridos

**Error "Equipment not in stock"**
- Verificar `Equipo.cantidad_disponible` > 0
- Verificar `Equipo.en_stock` es True
- Agregar validación de cantidad en `api_equipment.py`

### Optimización de Performance

**Índices de Base de Datos**
```python
class Meta:
    indexes = [
        models.Index(fields=['proyecto', 'equipo']),
        models.Index(fields=['tipo_equipo']),
    ]
    unique_together = [['proyecto', 'equipo', 'tipo_equipo']]
```

**Caché de API**
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 60)
def api_equipment_list(request):
    # ...
```

**Debouncing en Frontend**
```javascript
handleFilterChange = debounce(() => {
    this.loadEquipment();
}, 300);  // Esperar 300ms después de escribir
```

### Mejoras Futuras

**Fase 2: Filtrado Avanzado**
- Filtro por rango de presupuesto
- Preferencia por fabricante
- Guardar combinaciones de equipos favoritas
- Sugerir equipos alternativos

**Fase 3: Historial y Undo/Redo**
- Rastrear historial de selecciones
- Permitir revertir a selecciones previas
- Mostrar timestamps de cambios
- Vista comparativa: Antes/Después

**Fase 4: Integración PDF**
- Incluir explicaciones en PDF de cotización
- Generar texto persuasivo desde specs de equipos
- Agregar tabla de especificaciones a PDF
- Incluir análisis de ROI y payback

**Fase 5: Operaciones en Lote**
- Importar lista de equipos desde CSV
- Clonar selección a múltiples proyectos
- Actualizar reglas de compatibilidad desde spreadsheet

---

## API Endpoints

## API v1 y OpenAPI

Nuevos endpoints versionados:

- `GET /api/v1/equipment/`
- `POST /api/v1/projects/{id}/equipment/select/`
- `POST /api/v1/projects/{id}/equipment/{selection_id}/remove/`
- `POST /api/v1/projects/{id}/equipment/{selection_id}/update/`
- `POST /api/v1/projects/{id}/recalculate/`
- `POST /api/v1/projects/{id}/check-compatibility/`

Documentación:

- Schema OpenAPI: `/api/schema/`
- Swagger UI: `/api/docs/`

Compatibilidad hacia atrás:

- Los endpoints legacy `/api/...` siguen activos.
- Se emiten headers de deprecación (`Deprecation`, `Sunset`, `Link`) para migración gradual.

Ejemplo de request (selección de equipo):

```bash
curl -X POST http://localhost:8000/api/v1/projects/1/equipment/select/ \
    -H "Content-Type: application/json" \
    -d '{"equipo_id": 1, "tipo_equipo": "panel", "cantidad": 2}'
```

Ejemplo de respuesta:

```json
{
    "success": true,
    "created": true,
    "message": "Equipo agregado exitosamente",
    "selected_equipo": {
        "id": 10,
        "equipo_id": 1,
        "nombre": "SolarTech PS-450",
        "tipo": "panel",
        "cantidad": 2,
        "precio_unitario": 520000.0,
        "subtotal": 1040000.0
    }
}
```

## Calidad y pruebas

```bash
cd solar_app
C:/ProgramData/radioconda/python.exe manage.py check
C:/ProgramData/radioconda/python.exe manage.py showmigrations
C:/ProgramData/radioconda/python.exe -m pytest -q
C:/ProgramData/radioconda/python.exe manage.py spectacular --file schema.yml
```

Objetivo de cobertura recomendado para CI: **70%** mínimo en API y servicios críticos.

## Scripts operativos (post-refactor)

Los scripts de carga manual fueron fusionados en comandos de Django y servicios reutilizables:

```bash
cd solar_app
C:/ProgramData/radioconda/python.exe manage.py load_equipment_catalog
C:/ProgramData/radioconda/python.exe manage.py setup_demo_data
```

Esto reemplaza los scripts sueltos movidos a `deprecated/`.

## Benchmark básico

```bash
C:/ProgramData/radioconda/python.exe scripts/benchmark_api.py --url http://localhost:8000/api/v1/equipment/ --iterations 100
```

## Deprecated scripts

- Carpeta: `deprecated/`
- Fecha de deprecación: 2026-03-15
- Fecha objetivo de eliminación final: 2026-06-30

Scripts movidos:

- `deprecated/scripts/run_load_equipment.py`
- `deprecated/scripts/setup_test_data.py`
- `deprecated/scripts/0012_load_departamentos_municipios.py`
- `deprecated/solar_app/load_equipment.py`
- `deprecated/solar_app/add_equipment_list.py`

### Endpoints Principales

| Endpoint                         | Método | Descripción                    |
|----------------------------------|--------|--------------------------------|
| `/api/pvgis/`                    | POST   | Consulta radiación solar PVGIS |
| `/api/cotizacion/<pk>/charts/`   | GET    | Datos para gráficos de cotización |

### Endpoints de Equipos

| Endpoint                                    | Método | Descripción                        |
|---------------------------------------------|--------|----------------------------------|
| `/api/equipment/list/`                      | GET    | Listar equipos con filtros         |
| `/api/proyectos/<id>/equipment/select/`     | POST   | Agregar equipo a proyecto          |
| `/api/proyectos/<id>/equipment/<id>/remove/`| POST   | Remover equipo de proyecto         |
| `/api/proyectos/<id>/recalculate/`          | POST   | Recalcular dimensionamiento        |
| `/api/proyectos/<id>/check-compatibility/`  | POST   | Validar compatibilidad de equipos  |



---

Tabla de consumos por uso:

# Tabla 22. Ficha base de consumos por uso y energético

| Equipo                                 | Potencia (W) | Servicio (h/día o ciclos) |
|----------------------------------------|--------------|---------------------------|
| Iluminación Incandescente              | 60           | 4 h/día                   |
| Iluminación LFC                        | 25           | 4 h/día                   |
| Iluminación LED                        | 12           | 4 h/día                   |
| Iluminación Tubo fluorescente lineal   | 36           | 4 h/día                   |
| Iluminación Incandescente halógena     | 60           | 4 h/día                   |
| Ventilador                             | 100          | 8,5 h/día                 |
| Aire acondicionado 12000BTU            | 3250         | 5,5 h/día                 |
| TV 50"                                 | 145          | 7 h/día                   |
| Nevera                                 | 250          | 12 h/día                  |
| Plancha                                | 1200         | 1 h/día                   |
| Lavadora                               | 400          | 0,27 ciclos/día           |
| Ducha eléctrica                        | 3800         | 0,38 h/día                |
| Computador portátil                    | 50           | 3,2 h/día                 |
| Computador                             | 80           | 4,4 h/día                 |
| Celular                                | 20           | 1 h/día                   |
| Equipo de sonido                       | 30           | 3,1 h/día                 |
| Horno microondas                       | 1200         | 0,4 h/día                 |
| Horno Tostador                         | 1750         | 0,4 h/día                 |
| Air Fryer                              | 1500         | 0,33 h/día                |
| Estufa                                 | 1500         | 2,5 h/día                 |
| Reproductor de música                  | 15           | 3 h/día                   |
| Reproductor de video                   | 15           | 4 h/día                   |
| Cámara de seguridad                    | 12           | 24 h/día                  |
| Hidrolavadora                          | 1400         | 0,4 h/día                 |
| Congelador                             | 280          | 12 h/día                  |
| Máquina de soldadura 200A              | 820          | 0,5 h/día                 |
| Bomba 1 HP                             | 750          | 1,5 h/día                 |
| Bomba 1/2 HP                           | 375          | 1,5 h/día                 |
| Bomba 1/3 HP                           | 250          | 1,5 h/día                 |
| Bomba 1/4 HP                           | 188          | 1,5 h/día                 |
| Otros electrodomésticos                | -            | -                         |


---

## Licencia

Este proyecto es de uso privado. Todos los derechos reservados.
