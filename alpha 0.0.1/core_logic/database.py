# gimnasio_mgmt_gui/core_logic/database.py
# Este módulo maneja la conexión a la base de datos SQLite y la creación/verificación de tablas.

import sqlite3
import os

# --- Importaciones ---
# Para acceder a APP_DATA_ROOT_DIR, DATABASE_SUBDIR_NAME, DATABASE_FILENAME desde config.py
# y a ensure_directory_exists desde utils.py (dentro del mismo paquete core_logic)
try:
    from config import APP_DATA_ROOT_DIR, DATABASE_SUBDIR_NAME, DATABASE_FILENAME
    from .utils import ensure_directory_exists # Importación relativa dentro del paquete core_logic
except ImportError as e:
    # Fallback para situaciones donde el path no está configurado correctamente (ej. pruebas directas del módulo)
    print(f"ADVERTENCIA (database.py): No se pudo importar desde 'config' o '.utils'. Error: {e}")
    # Valores de fallback mínimos para que el módulo no falle completamente al cargarse
    # (aunque su funcionalidad estaría severamente limitada)
    _fallback_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    APP_DATA_ROOT_DIR = os.path.join(_fallback_project_root, "_gym_app_data_db_fallback")
    DATABASE_SUBDIR_NAME = "db_fb"
    DATABASE_FILENAME = "gym_pro_data_fb.db"
    # Definición dummy de ensure_directory_exists si no se pudo importar
    def ensure_directory_exists(path_str):
        if not os.path.exists(path_str): os.makedirs(path_str, exist_ok=True); return True
        return True

# --- CONSTRUCCIÓN DE LA RUTA A LA BASE DE DATOS ---
DB_DIRECTORY = os.path.join(APP_DATA_ROOT_DIR, DATABASE_SUBDIR_NAME)
FULL_DATABASE_PATH = os.path.join(DB_DIRECTORY, DATABASE_FILENAME)


def get_db_connection() -> sqlite3.Connection | None:
    """
    Establece y devuelve una conexión a la base de datos SQLite.
    Asegura que el directorio de la base de datos exista antes de intentar conectar.
    Devuelve None si no se puede establecer la conexión.
    """
    if not ensure_directory_exists(DB_DIRECTORY):
        print(f"ERROR CRÍTICO (database.py): No se pudo crear/acceder al directorio de la base de datos: {DB_DIRECTORY}")
        return None
    
    try:
        conn = sqlite3.connect(FULL_DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Permite acceso a columnas por nombre
        conn.execute("PRAGMA foreign_keys = ON;") # Habilitar claves foráneas es crucial
        # print(f"INFO (database.py): Conexión a BD establecida: {FULL_DATABASE_PATH}") # Para depuración
        return conn
    except sqlite3.Error as e:
        print(f"ERROR (database.py): No se pudo conectar a la base de datos '{FULL_DATABASE_PATH}'. Error: {e}")
        return None

def create_or_verify_tables():
    """
    Crea todas las tablas necesarias en la base de datos si no existen.
    Verifica también la existencia de triggers importantes.
    Se llama una vez al inicio de la aplicación.
    """
    print_prefix = "INFO (database.py - Tablas):"
    conn = get_db_connection()
    if not conn:
        print(f"{print_prefix} No se pudo obtener conexión a la BD. Creación de tablas abortada.")
        return False # Indica fallo

    cursor = conn.cursor()
    all_ok = True

    try:
        print(f"{print_prefix} Verificando/Creando tablas en '{FULL_DATABASE_PATH}'...")

        # --- Tabla de Usuarios del Sistema ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL, -- Verificado contra ALL_DEFINED_ROLES en la lógica de auth.py
                is_active INTEGER DEFAULT 1, -- 1 para activo, 0 para inactivo/bloqueado
                last_login_at TIMESTAMP,
                failed_login_attempts INTEGER DEFAULT 0,
                account_locked_until TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print(f"{print_prefix} Tabla 'system_users' verificada/creada.")

        # --- Tabla de Miembros del Gimnasio ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                internal_member_id TEXT UNIQUE NOT NULL, -- ID legible generado por la app (ej. MBR-XYZ123)
                full_name TEXT NOT NULL,
                date_of_birth DATE,
                gender TEXT, -- Ej: 'Masculino', 'Femenino', 'Otro', 'Prefiero no decirlo'
                phone_number TEXT,
                address_line1 TEXT,
                address_city TEXT,
                address_postal_code TEXT,
                join_date DATE NOT NULL,
                current_status TEXT NOT NULL, -- Ej: 'Activo', 'Inactivo', 'Expirado', 'Congelado'
                notes TEXT,
                photo_filename TEXT, -- Nombre del archivo de la foto, guardado en MEMBER_PHOTOS_SUBDIR_NAME
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print(f"{print_prefix} Tabla 'members' verificada/creada.")

        # --- Tabla de Membresías de los Miembros ---
        # Un miembro puede tener múltiples registros de membresía a lo largo del tiempo.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                plan_key TEXT NOT NULL, -- Clave del plan de DEFAULT_MEMBERSHIP_PLANS o gestionado
                plan_name_at_purchase TEXT NOT NULL, -- Nombre del plan al momento de la compra
                price_paid DECIMAL(10, 2) NOT NULL, -- Precio final pagado (puede tener descuentos)
                start_date DATE NOT NULL,
                expiry_date DATE NOT NULL,
                sessions_total INTEGER, -- Para bonos de sesiones
                sessions_remaining INTEGER, -- Para bonos de sesiones
                payment_transaction_id INTEGER, -- Vinculado a una transacción de ingreso
                is_current INTEGER DEFAULT 0, -- 1 si es la membresía activa/actual del socio, 0 si es histórica/futura
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
                FOREIGN KEY (payment_transaction_id) REFERENCES financial_transactions(id) ON DELETE SET NULL
            )
        """)
        print(f"{print_prefix} Tabla 'member_memberships' verificada/creada.")

        # --- Tabla de Asistencia de Miembros ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                membership_id INTEGER, -- Opcional: membresía con la que se registró la asistencia
                check_in_datetime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                check_out_datetime TIMESTAMP,
                attended_activity_name TEXT, -- Nombre de la clase o 'Acceso General'
                notes TEXT,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
                FOREIGN KEY (membership_id) REFERENCES member_memberships(id) ON DELETE SET NULL
            )
        """)
        print(f"{print_prefix} Tabla 'member_attendance' verificada/creada.")

        # --- Tabla de Transacciones Financieras ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                internal_transaction_id TEXT UNIQUE NOT NULL, -- ID legible generado por la app
                transaction_type TEXT NOT NULL CHECK(transaction_type IN ('income', 'expense')),
                transaction_date DATE NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL, -- Categoría (de DEFAULT_INCOME/EXPENSE_CATEGORIES o personalizada)
                amount DECIMAL(10, 2) NOT NULL, -- Usar DECIMAL para dinero si la BD lo soporta bien (SQLite lo trata como NUMERIC)
                payment_method TEXT, -- Ej: 'Efectivo', 'Tarjeta', 'Transferencia'
                related_member_id INTEGER, -- Para ingresos/gastos asociados a un miembro
                recorded_by_user_id INTEGER, -- ID del usuario del sistema que registró la transacción
                reference_document_number TEXT, -- Ej. Nº de factura, ticket
                notes TEXT,
                is_recurring_source INTEGER DEFAULT 0, -- 1 si esta transacción fue generada por un gasto/ingreso recurrente
                source_recurring_id INTEGER,       -- ID del gasto/ingreso recurrente que la originó
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (related_member_id) REFERENCES members(id) ON DELETE SET NULL,
                FOREIGN KEY (recorded_by_user_id) REFERENCES system_users(id) ON DELETE SET NULL
                -- FOREIGN KEY (source_recurring_id) REFERENCES recurring_financial_items(id) ON DELETE SET NULL (si tenemos esa tabla)
            )
        """)
        print(f"{print_prefix} Tabla 'financial_transactions' verificada/creada.")

        # --- Tabla de Gastos/Ingresos Recurrentes ---
        # Para la funcionalidad "gastos recurrentes que se aplican mes a mes"
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recurring_financial_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL CHECK(item_type IN ('income', 'expense')), -- 'income' o 'expense'
                description TEXT NOT NULL,
                default_amount DECIMAL(10, 2) NOT NULL,
                category TEXT NOT NULL,
                frequency TEXT NOT NULL, -- Ej: 'monthly', 'quarterly', 'annually', 'weekly'
                day_of_month_to_process INTEGER, -- Para 'monthly', 'quarterly', 'annually' (1-31, o -1 para último día)
                day_of_week_to_process INTEGER, -- Para 'weekly' (0=Lunes, 6=Domingo)
                start_date DATE NOT NULL,
                end_date DATE, -- Opcional: si el item recurrente tiene fecha de fin
                next_due_date DATE NOT NULL, -- Próxima fecha en la que se debe generar la transacción
                is_active INTEGER DEFAULT 1, -- 1 para activo, 0 para inactivo
                auto_generate_transaction INTEGER DEFAULT 0, -- 1 si se genera automáticamente, 0 si requiere confirmación manual
                related_member_id INTEGER, -- Si el recurrente está ligado a un miembro específico
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (related_member_id) REFERENCES members(id) ON DELETE SET NULL
            )
        """)
        print(f"{print_prefix} Tabla 'recurring_financial_items' verificada/creada.")


        # --- Tabla de Configuraciones de la Aplicación (Opcional, gestionada por Admin Sistema) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_settings (
                setting_key TEXT PRIMARY KEY NOT NULL, -- Ej: 'gym_name', 'default_currency', 'membership_prices_json'
                setting_value TEXT,
                value_data_type TEXT DEFAULT 'string' CHECK(value_data_type IN ('string', 'integer', 'float', 'boolean', 'json')),
                description TEXT,
                is_user_configurable INTEGER DEFAULT 1, -- 1 si el admin puede cambiarlo desde la UI
                last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print(f"{print_prefix} Tabla 'application_settings' verificada/creada.")

        # --- Triggers para actualizar campos 'updated_at' / 'last_updated_at' ---
        # SQLite no actualiza estos campos automáticamente en UPDATE como otros SGBD.
        tables_with_auto_update_timestamp = {
            "system_users": ("id", "updated_at"),
            "members": ("id", "updated_at"),
            "financial_transactions": ("id", "updated_at"),
            "recurring_financial_items": ("id", "updated_at"),
            "application_settings": ("setting_key", "last_updated_at") # PK es 'setting_key', ts es 'last_updated_at'
        }

        for table, (pk_col, ts_col) in tables_with_auto_update_timestamp.items():
            trigger_name = f"trigger_update_{table}_{ts_col}"
            cursor.execute(f"""
                CREATE TRIGGER IF NOT EXISTS {trigger_name}
                AFTER UPDATE ON {table}
                FOR EACH ROW
                BEGIN
                    UPDATE {table}
                    SET {ts_col} = CURRENT_TIMESTAMP
                    WHERE {pk_col} = OLD.{pk_col};
                END;
            """)
        print(f"{print_prefix} Triggers para timestamps de actualización verificados/creados.")

        conn.commit()
        print(f"{print_prefix} Todas las tablas y triggers han sido comprometidos exitosamente.")

    except sqlite3.Error as e:
        print(f"ERROR (database.py): Ocurrió un error durante la creación/verificación de tablas: {e}")
        conn.rollback() # Revertir cambios si algo falló
        all_ok = False
    finally:
        conn.close()
        # print(f"{print_prefix} Conexión a BD cerrada.")
    
    return all_ok


# --- Script de autocomprobación (ejecutar `python gimnasio_mgmt_gui/core_logic/database.py`) ---
if __name__ == "__main__":
    print(f"--- {os.path.basename(__file__)} Self-Check and Initialization ---")
    
    # 1. Verificar que el directorio de datos y el de la BD existen o se pueden crear
    # (get_db_connection ya lo hace, pero podemos ser explícitos aquí para la prueba)
    if not ensure_directory_exists(DB_DIRECTORY):
        print(f"CRÍTICO: Falló la creación del directorio de base de datos: {DB_DIRECTORY}. Abortando.")
    else:
        print(f"Directorio de base de datos verificado/creado: {DB_DIRECTORY}")
        print(f"Ruta completa de la BD esperada: {FULL_DATABASE_PATH}")
        
        # 2. Intentar crear/verificar las tablas
        print("\nIntentando crear/verificar tablas...")
        success = create_or_verify_tables()
        if success:
            print("\nProceso de inicialización de base de datos completado exitosamente.")
            # Se podría añadir una pequeña consulta para verificar que una tabla existe
            conn_test = get_db_connection()
            if conn_test:
                try:
                    c = conn_test.cursor()
                    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_users';")
                    if c.fetchone():
                        print("Prueba de verificación: La tabla 'system_users' existe.")
                    else:
                        print("ADVERTENCIA: La tabla 'system_users' no se encontró después de la creación.")
                except sqlite3.Error as err_test:
                    print(f"Error al verificar tabla: {err_test}")
                finally:
                    conn_test.close()
        else:
            print("\nFALLÓ el proceso de inicialización de la base de datos.")