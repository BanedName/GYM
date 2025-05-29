# config.py
import os

# --- Configuración de la Base de Datos ---
DATABASE_NAME = "gimnasio_app.db"

# --- Configuración de Superusuario ---
SUPERUSER_USERNAME = "root"
SUPERUSER_PASSWORD = "CABALLEROS"

# --- Definición de Roles de Usuario ---
ROLE_SUPERUSER = "superuser"
ROLE_PROGRAM_ADMIN = "program_admin"
ROLE_DATA_ADMIN = "data_admin"
ROLE_STAFF = "staff"

ALL_ROLES = [ROLE_SUPERUSER, ROLE_PROGRAM_ADMIN, ROLE_DATA_ADMIN, ROLE_STAFF]
ASSIGNABLE_ROLES_BY_PROGRAM_ADMIN = [ROLE_PROGRAM_ADMIN, ROLE_DATA_ADMIN, ROLE_STAFF]

# --- Configuraciones Financieras ---
CURRENCY_SYMBOL = "€"
CURRENCY_CODE = "EUR"

DEFAULT_MEMBERSHIP_TYPES = {
    "monthly": {"display_name": "Cuota Mensual", "price": 35.00, "duration_days": 30, "category": "membership_fee", "description": "Acceso ilimitado mensual."},
    "quarterly": {"display_name": "Cuota Trimestral", "price": 95.00, "duration_days": 90, "category": "membership_fee", "description": "Acceso trimestral con descuento."},
    "biannual": {"display_name": "Cuota Semestral", "price": 180.00, "duration_days": 180, "category": "membership_fee", "description": "Acceso semestral con mayor descuento."},
    "annual": {"display_name": "Cuota Anual", "price": 330.00, "duration_days": 365, "category": "membership_fee", "description": "Acceso anual, máximo ahorro."},
    "10_session_pass": {"display_name": "Bono 10 Sesiones", "price": 70.00, "duration_days": 180, "sessions": 10, "category": "session_pass_purchase", "description": "10 accesos, caducidad 6 meses."},
    "single_class": {"display_name": "Clase Suelta / Acceso Diario", "price": 8.00, "duration_days": 1, "sessions": 1, "category": "drop_in_fee", "description": "Acceso único diario o por clase."},
    "student_monthly": {"display_name": "Cuota Mensual Estudiante", "price": 28.00, "duration_days": 30, "requires_proof": True, "category": "membership_fee", "description": "Cuota mensual para estudiantes (con justificante)."}
}

DEFAULT_INCOME_CATEGORIES = [
    "Cuota Mensual", "Cuota Trimestral", "Cuota Anual", "Bono Sesiones", "Clase Suelta",
    "Venta de Productos", "Alquiler de Taquillas", "Otros Ingresos"
]

# Categorías por Defecto para Gastos
# Podríamos añadir un flag o una lista separada para sugerir cuáles son típicamente recurrentes,
# pero la gestión real de "recurrencia" (frecuencia, día de pago) es mejor en una tabla de BD.
TYPICALLY_RECURRING_EXPENSE_CATEGORIES = [
    "Alquiler Local",
    "Suministros (Luz, Agua, Gas)", # A menudo recurrentes, aunque el monto varíe
    "Internet y Teléfono",
    "Nóminas y Seguros Sociales",
    "Limpieza", # Si es un servicio contratado regularmente
    "Software y Licencias", # Suscripciones
    "Seguros", # Primas anuales o mensuales
    "Gestoría / Asesoría"
]

OTHER_EXPENSE_CATEGORIES = [
    "Material Deportivo", # Compras puntuales
    "Mantenimiento y Reparaciones", # Pueden ser puntuales o programadas
    "Marketing y Publicidad", # Campañas puntuales o continuas
    "Impuestos y Tasas", # Anuales, trimestrales
    "Formación del Personal",
    "Eventos y Promociones",
    "Otros Gastos Puntuales"
]

# Unimos todas para el desplegable, la separación es solo conceptual aquí
DEFAULT_EXPENSE_CATEGORIES = sorted(list(set(TYPICALLY_RECURRING_EXPENSE_CATEGORIES + OTHER_EXPENSE_CATEGORIES)))

# --- Configuración de Miembros ---
DEFAULT_MEMBER_STATUS_NEW = "active"
DEFAULT_MEMBER_STATUS_RENEWED = "active"
MEMBER_STATUS_OPTIONS = ["active", "inactive", "pending_payment", "expired", "frozen"]

# --- Rutas ---
BASE_APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_APP_DIR, "app_data")
MEMBER_PHOTOS_DIR = os.path.join(DATA_DIR, "member_photos")
FINANCIAL_REPORTS_DIR = os.path.join(DATA_DIR, "financial_reports")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

# --- Otras Configuraciones del Programa (Defaults) ---
GYM_NAME_DEFAULT = "Gimnasio Evolución Fitness"
DAYS_BEFORE_MEMBERSHIP_EXPIRY_REMINDER_DEFAULT = 7
MAX_LOGIN_ATTEMPTS = 5

# --- Internacionalización y Localización ---
DATE_FORMAT_DISPLAY = "%d/%m/%Y"
DATETIME_FORMAT_DISPLAY = "%d/%m/%Y %H:%M"

# --- Debugging y Desarrollo ---
DEBUG_MODE = True

if __name__ == "__main__":
    print("--- Configuraciones de la Aplicación (config.py) ---")
    print(f"\n=== Base de Datos y Superusuario ===")
    print(f"Nombre de la BD: {DATABASE_NAME}")

    print(f"\n=== Finanzas ===")
    print(f"Símbolo de Moneda: {CURRENCY_SYMBOL}")
    print("\nCategorías de Gastos (incluye sugerencias de recurrentes):")
    for cat in DEFAULT_EXPENSE_CATEGORIES:
        marker = "(*)" if cat in TYPICALLY_RECURRING_EXPENSE_CATEGORIES else ""
        print(f"  - {cat} {marker}")
    print("(*) Categorías que típicamente podrían configurarse como recurrentes.")

    # ... (resto del if __name__ == "__main__": como antes) ...
    print(f"\n=== Rutas (Conceptuales) ===")
    print(f"Directorio de datos: {DATA_DIR}")
    for path_dir in [DATA_DIR, MEMBER_PHOTOS_DIR, FINANCIAL_REPORTS_DIR, BACKUP_DIR]:
        if not os.path.exists(path_dir):
            try:
                os.makedirs(path_dir, exist_ok=True)
                # print(f"Directorio '{path_dir}' verificado/creado.") # Comentado para menos verbosidad
            except OSError as e:
                print(f"Advertencia: No se pudo crear el directorio {path_dir}: {e}")
    print(f"\nModo Debug: {DEBUG_MODE}")