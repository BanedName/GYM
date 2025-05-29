# gimnasio_mgmt_gui/config.py
# Este archivo contiene las configuraciones globales y constantes para la aplicación GymManager Pro.

import os

# --- INFORMACIÓN GENERAL DE LA APLICACIÓN ---
APP_NAME = "Jose Dojo"
APP_VERSION = "1.0.0"
APP_AUTHOR = "Pedro Miguel González Fernández"

# --- CONFIGURACIÓN DE LA BASE DE DATOS ---
# El archivo de la BD se guardará dentro del directorio de datos de la aplicación.
DATABASE_SUBDIR_NAME = "database"         # Subdirectorio para la BD dentro de APP_DATA_DIR
DATABASE_FILENAME = "gym_pro_data.db" # Nombre del archivo de la base de datos SQLite

# --- CREDENCIALES DEL SUPERUSUARIO INICIAL ---
# Estas se usarán para crear el primer superadministrador si no existe.
# ¡¡CRUCIAL!! Cambiar SUPERUSER_INIT_PASSWORD en un entorno real o pedirla en la primera ejecución.
SUPERUSER_INIT_USERNAME = "root"
SUPERUSER_INIT_PASSWORD = "CaballeroS259" 

# --- ROLES DE USUARIO DEL SISTEMA ---
# Se definen como constantes para consistencia en todo el código.
ROLE_SUPERUSER = "Superadministrador"           # Todos los privilegios. Gestiona Admins del Sistema.
ROLE_SYSTEM_ADMIN = "Administrador del Sistema" # Gestiona usuarios, configuraciones globales de la app.
ROLE_DATA_MANAGER = "Gestor de Datos"           # Gestiona miembros, finanzas, clases, horarios.
ROLE_STAFF_MEMBER = "Miembro del Personal"      # Permisos limitados (ej. check-in, consulta básica).

ALL_DEFINED_ROLES = [ROLE_SUPERUSER, ROLE_SYSTEM_ADMIN, ROLE_DATA_MANAGER, ROLE_STAFF_MEMBER]

# Roles que un SYSTEM_ADMIN puede crear/asignar (no puede afectar a Superusuarios)
ASSIGNABLE_ROLES_BY_SYSTEM_ADMIN = [ROLE_SYSTEM_ADMIN, ROLE_DATA_MANAGER, ROLE_STAFF_MEMBER]

# --- CONFIGURACIONES FINANCIERAS POR DEFECTO ---
# Estos son valores iniciales. Idealmente, la aplicación permitirá modificarlos vía GUI
# y los almacenará en la base de datos (tabla de configuraciones).
CURRENCY_DISPLAY_SYMBOL = "€"
CURRENCY_CODE_ISO_4217 = "EUR" # Útil para integraciones o formatos más estándar

# Estructura para Planes de Membresía por Defecto:
# 'clave_unica_plan': {
#     'nombre_visible_ui': 'Nombre que ve el usuario',
#     'precio_base_decimal': Decimal (o float, pero Decimal es mejor para moneda),
#     'duracion_total_dias': int,
#     'categoria_contable_ingreso': 'Texto para la categoría del ingreso',
#     'descripcion_breve': 'Pequeña descripción del plan'
#     'numero_sesiones_incluidas': int (opcional, para bonos)
# }
DEFAULT_MEMBERSHIP_PLANS = {
    "mensual_basic": {
        "nombre_visible_ui": "Plan Mensual Básico",
        "precio_base_decimal": 35.00, # Usar float por simplicidad aquí, pero Decimal es preferible para dinero
        "duracion_total_dias": 30,
        "categoria_contable_ingreso": "Ingresos por Cuotas Mensuales",
        "descripcion_breve": "Acceso completo al gimnasio, renovación mensual."
    },
    "trimestral_plus": {
        "nombre_visible_ui": "Plan Trimestral Plus",
        "precio_base_decimal": 95.00,
        "duracion_total_dias": 90,
        "categoria_contable_ingreso": "Ingresos por Cuotas Trimestrales",
        "descripcion_breve": "Tres meses de acceso completo con un pequeño descuento."
    },
    "anual_vip": {
        "nombre_visible_ui": "Plan Anual VIP",
        "precio_base_decimal": 330.00,
        "duracion_total_dias": 365,
        "categoria_contable_ingreso": "Ingresos por Cuotas Anuales",
        "descripcion_breve": "Acceso VIP durante un año completo, máximo ahorro."
    },
    "bono_10_flex": {
        "nombre_visible_ui": "Bono 10 Sesiones Flex",
        "precio_base_decimal": 75.00,
        "duracion_total_dias": 180, # Caducidad del bono
        "numero_sesiones_incluidas": 10,
        "categoria_contable_ingreso": "Venta de Bonos de Sesiones",
        "descripcion_breve": "10 accesos flexibles al gimnasio. Caduca en 6 meses."
    },
    "pase_1_dia": {
        "nombre_visible_ui": "Pase de 1 Día",
        "precio_base_decimal": 8.00,
        "duracion_total_dias": 1,
        "numero_sesiones_incluidas": 1,
        "categoria_contable_ingreso": "Ingresos por Pases Diarios",
        "descripcion_breve": "Acceso válido para un solo día de entrenamiento."
    }
}

# Categorías de Ingresos por Defecto (se puede expandir desde la GUI)
DEFAULT_INCOME_CATEGORIES_LIST = sorted(list(set(
    [plan["categoria_contable_ingreso"] for plan in DEFAULT_MEMBERSHIP_PLANS.values()] +
    ["Venta de Suplementos y Bebidas", "Ropa y Accesorios del Gimnasio", "Servicios de Entrenamiento Personal",
     "Alquiler de Taquillas Personales", "Organización de Eventos Especiales", "Otros Ingresos Diversos"]
)))

# Categorías de Gastos por Defecto (se puede expandir desde la GUI)
# Separadas para indicar cuáles podrían ser recurrentes por naturaleza
TYPICALLY_RECURRING_EXPENSE_CATEGORIES_LIST = [
    "Alquiler/Hipoteca del Local", "Costes de Suministros (Luz, Agua, Gas, Internet)",
    "Nóminas y Seguridad Social del Personal", "Software de Gestión y Licencias SaaS",
    "Servicios de Limpieza Regulares", "Asesoría Fiscal, Laboral y Contable", "Primas de Seguros del Negocio",
    "Mantenimiento Programado de Equipos"
]
OTHER_OPERATIONAL_EXPENSE_CATEGORIES_LIST = [
    "Adquisición de Nuevo Equipamiento", "Reparaciones y Mantenimiento Correctivo",
    "Marketing, Publicidad y Promociones", "Formación Continua del Personal",
    "Material de Oficina y Consumibles", "Impuestos, Tasas y Licencias Municipales",
    "Comisiones Bancarias y Gastos Financieros", "Gastos Imprevistos y Varios"
]
DEFAULT_EXPENSE_CATEGORIES_LIST = sorted(list(set(
    TYPICALLY_RECURRING_EXPENSE_CATEGORIES_LIST + OTHER_OPERATIONAL_EXPENSE_CATEGORIES_LIST
)))

# --- CONFIGURACIONES ESPECÍFICAS DE MIEMBROS ---
DEFAULT_NEW_MEMBER_STATUS_ON_CREATION = "Activo"
MEMBER_STATUS_OPTIONS_LIST = [
    "Activo", "Inactivo", "Pendiente de Pago", "Expirado",
    "Congelado Temporalmente", "Baja Solicitada", "Baja Definitiva"
]

# --- RUTAS Y DIRECTORIOS PRINCIPALES ---
# Directorio raíz del proyecto (donde se encuentra este archivo config.py)
PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# Directorio para todos los datos generados por la aplicación
# Se recomienda que este directorio se cree automáticamente por la aplicación si no existe.
APP_DATA_ROOT_DIR_NAME = "_gym_app_data" # Nombre de la carpeta, el "_" inicial puede ayudar a ordenarlo
APP_DATA_ROOT_DIR = os.path.join(PROJECT_ROOT_DIR, APP_DATA_ROOT_DIR_NAME)

# Subdirectorios específicos dentro de APP_DATA_ROOT_DIR
# Estos también deberían crearse si no existen.
MEMBER_PHOTOS_SUBDIR_NAME = "member_photos"
FINANCIAL_REPORTS_SUBDIR_NAME = "financial_reports"
DATABASE_BACKUPS_SUBDIR_NAME = "db_backups"
LOG_FILES_SUBDIR_NAME = "application_logs"


# --- CONFIGURACIONES DE LA INTERFAZ GRÁFICA (Valores por defecto para ttk) ---
# La aplicación intentará usar estos, pero la disponibilidad de temas depende del sistema.
UI_DEFAULT_THEME = "clam"  # Opciones: "clam", "alt", "default", "classic", "vista" (Win), "aqua" (macOS)
UI_MAIN_WINDOW_TITLE = f"{"Jose Dojo"} v{"0,5"}"
MAIN_WINDOW_TITLE = f"{"Jose Dojo"} v{"0,5"}"
UI_DEFAULT_FONT_FAMILY = "Arial" # Considerar "Segoe UI" para Windows
UI_DEFAULT_FONT_SIZE_NORMAL = 10
UI_DEFAULT_FONT_SIZE_MEDIUM = 12
UI_DEFAULT_FONT_SIZE_LARGE = 14
UI_DEFAULT_FONT_SIZE_HEADER = 18
UI_DEFAULT_WIDGET_PADDING = 5 # Padding interno y externo para widgets

# --- FORMATOS DE FECHA Y HORA ---
# Para mostrar en la interfaz de usuario
UI_DISPLAY_DATE_FORMAT = "%d/%m/%Y"
UI_DISPLAY_DATETIME_FORMAT = "%d/%m/%Y %H:%M"
# Para almacenamiento en la base de datos (ISO 8601 es estándar y recomendable)
DB_STORAGE_DATE_FORMAT = "%Y-%m-%d"
DB_STORAGE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- PARÁMETROS DE SEGURIDAD Y OPERACIÓN ---
# (Algunos son conceptuales para una app de escritorio, más relevantes en entornos cliente-servidor)
MAX_FAILED_LOGIN_ATTEMPTS_BEFORE_LOCKOUT = 5
ACCOUNT_LOCKOUT_DURATION_SECONDS = 15 * 60  # 15 minutos en segundos

# --- MODO DE DEPURACIÓN ---
# Cambiar a False para despliegues en producción.
# Puede usarse para controlar logs, mensajes de error detallados, etc.
APPLICATION_DEBUG_MODE = True

VALID_FREQUENCIES = ['daily', 'weekly', 'bi-weekly', 'monthly', 'quarterly', 'semi-annually', 'annually']

# --- Script de autocomprobación para este archivo (ejecutar `python config.py`) ---
if __name__ == "__main__":
    print(f"--- {APP_NAME} Configuration File Self-Check ---")
    print(f"Application Version: {APP_VERSION}")
    print(f"Project Root Directory: {PROJECT_ROOT_DIR}")
    print(f"Application Data Directory: {APP_DATA_ROOT_DIR}")

    db_full_path = os.path.join(APP_DATA_ROOT_DIR, DATABASE_SUBDIR_NAME, DATABASE_FILENAME)
    print(f"  Expected Database Full Path: {db_full_path}")

    print(f"\nInitial Superuser Username: {SUPERUSER_INIT_USERNAME}")
    print(f"Default UI Theme for Tkinter/ttk: {UI_DEFAULT_THEME}")

    print("\nDefault Membership Plans:")
    for key, plan_details in DEFAULT_MEMBERSHIP_PLANS.items():
        print(f"  - Plan '{plan_details['nombre_visible_ui']}': {plan_details['precio_base_decimal']:.2f}{CURRENCY_DISPLAY_SYMBOL}")

    print(f"\nTotal Default Income Categories: {len(DEFAULT_INCOME_CATEGORIES_LIST)}")
    print(f"Total Default Expense Categories: {len(DEFAULT_EXPENSE_CATEGORIES_LIST)}")

    if APPLICATION_DEBUG_MODE:
        print("\n*** APPLICATION IS CURRENTLY IN DEBUG MODE ***")
    else:
        print("\nApplication is in Production Mode.")

    # Opcional: verificar/crear el directorio APP_DATA_ROOT_DIR si se ejecuta config.py directamente
    # Esto es más para testing de este archivo. La app principal se encargaría de asegurar los directorios.
    if not os.path.exists(APP_DATA_ROOT_DIR):
        try:
            os.makedirs(APP_DATA_ROOT_DIR)
            print(f"\nNOTICE: Created application data directory: {APP_DATA_ROOT_DIR}")
        except OSError as e:
            print(f"\nERROR: Could not create application data directory '{APP_DATA_ROOT_DIR}': {e}")