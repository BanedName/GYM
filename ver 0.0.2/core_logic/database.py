# gimnasio_mgmt_gui/core_logic/database.py
# Este módulo maneja la conexión a la base de datos SQLite y la creación/verificación de tablas.

import sqlite3
import os

# --- Importaciones ---
try:
    from config import APP_DATA_ROOT_DIR, DATABASE_SUBDIR_NAME, DATABASE_FILENAME
    from .utils import ensure_directory_exists 
except ImportError as e:
    print(f"ADVERTENCIA (database.py): No se pudo importar desde 'config' o '.utils'. Error: {e}")
    _fallback_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    APP_DATA_ROOT_DIR = os.path.join(_fallback_project_root, "_gym_app_data_db_fallback")
    DATABASE_SUBDIR_NAME = "db_fb"
    DATABASE_FILENAME = "gym_pro_data_fb.db"
    
    # Firma de fallback corregida para coincidir con utils.ensure_directory_exists
    def ensure_directory_exists(dir_path: str) -> bool:
        """Fallback dummy de ensure_directory_exists con firma corregida."""
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"ADVERTENCIA (database.py - fallback): Directorio creado por fallback: {dir_path}")
                return True
            except OSError as e_fb:
                print(f"ERROR (database.py - fallback): No se pudo crear dir por fallback '{dir_path}'. {e_fb}")
                return False
        return True

# --- CONSTRUCCIÓN DE LA RUTA A LA BASE DE DATOS ---
DB_DIRECTORY = os.path.join(APP_DATA_ROOT_DIR, DATABASE_SUBDIR_NAME)
FULL_DATABASE_PATH = os.path.join(DB_DIRECTORY, DATABASE_FILENAME)


def get_db_connection() -> sqlite3.Connection | None:
    if not ensure_directory_exists(DB_DIRECTORY):
        print(f"ERROR CRÍTICO (database.py): No se pudo crear/acceder al directorio de la base de datos: {DB_DIRECTORY}")
        return None
    
    try:
        conn = sqlite3.connect(FULL_DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        print(f"ERROR (database.py): No se pudo conectar a la base de datos '{FULL_DATABASE_PATH}'. Error: {e}")
        return None

def create_or_verify_tables():
    print_prefix = "INFO (database.py - Tablas):"
    conn = get_db_connection()
    if not conn:
        print(f"{print_prefix} No se pudo obtener conexión a la BD. Creación de tablas abortada.")
        return False

    cursor = conn.cursor()
    all_ok = True

    try:
        print(f"{print_prefix} Verificando/Creando tablas en '{FULL_DATABASE_PATH}'...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                last_login_at TIMESTAMP,
                failed_login_attempts INTEGER DEFAULT 0,
                account_locked_until TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # print(f"{print_prefix} Tabla 'system_users' verificada/creada.") # Comentado para menos verbosidad

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                internal_member_id TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                date_of_birth DATE,
                gender TEXT,
                phone_number TEXT,
                address_line1 TEXT,
                address_city TEXT,
                address_postal_code TEXT,
                join_date DATE NOT NULL,
                current_status TEXT NOT NULL,
                notes TEXT,
                photo_filename TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # print(f"{print_prefix} Tabla 'members' verificada/creada.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_memberships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                plan_key TEXT NOT NULL,
                plan_name_at_purchase TEXT NOT NULL,
                price_paid DECIMAL(10, 2) NOT NULL,
                start_date DATE NOT NULL,
                expiry_date DATE NOT NULL,
                sessions_total INTEGER,
                sessions_remaining INTEGER,
                payment_transaction_id INTEGER,
                is_current INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
                FOREIGN KEY (payment_transaction_id) REFERENCES financial_transactions(id) ON DELETE SET NULL
            )
        """)
        # print(f"{print_prefix} Tabla 'member_memberships' verificada/creada.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                membership_id INTEGER,
                check_in_datetime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                check_out_datetime TIMESTAMP,
                attended_activity_name TEXT,
                notes TEXT,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
                FOREIGN KEY (membership_id) REFERENCES member_memberships(id) ON DELETE SET NULL
            )
        """)
        # print(f"{print_prefix} Tabla 'member_attendance' verificada/creada.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                internal_transaction_id TEXT UNIQUE NOT NULL,
                transaction_type TEXT NOT NULL CHECK(transaction_type IN ('income', 'expense')),
                transaction_date DATE NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                payment_method TEXT,
                related_member_id INTEGER,
                recorded_by_user_id INTEGER,
                reference_document_number TEXT,
                notes TEXT,
                is_recurring_source INTEGER DEFAULT 0,
                source_recurring_id INTEGER,      
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (related_member_id) REFERENCES members(id) ON DELETE SET NULL,
                FOREIGN KEY (recorded_by_user_id) REFERENCES system_users(id) ON DELETE SET NULL,
                FOREIGN KEY (source_recurring_id) REFERENCES recurring_financial_items(id) ON DELETE SET NULL 
            )
        """)
        # print(f"{print_prefix} Tabla 'financial_transactions' verificada/creada.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recurring_financial_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL CHECK(item_type IN ('income', 'expense')),
                description TEXT NOT NULL,
                default_amount DECIMAL(10, 2) NOT NULL,
                category TEXT NOT NULL,
                frequency TEXT NOT NULL,
                day_of_month_to_process INTEGER,
                day_of_week_to_process INTEGER,
                start_date DATE NOT NULL,
                end_date DATE,
                next_due_date DATE NOT NULL,
                is_active INTEGER DEFAULT 1,
                auto_generate_transaction INTEGER DEFAULT 0,
                related_member_id INTEGER,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (related_member_id) REFERENCES members(id) ON DELETE SET NULL
            )
        """)
        # print(f"{print_prefix} Tabla 'recurring_financial_items' verificada/creada.")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_settings (
                setting_key TEXT PRIMARY KEY NOT NULL,
                setting_value TEXT,
                value_data_type TEXT DEFAULT 'string' CHECK(value_data_type IN ('string', 'integer', 'float', 'boolean', 'json')),
                description TEXT,
                is_user_configurable INTEGER DEFAULT 1,
                last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # print(f"{print_prefix} Tabla 'application_settings' verificada/creada.")

        tables_with_auto_update_timestamp = {
            "system_users": ("id", "updated_at"),
            "members": ("id", "updated_at"),
            "financial_transactions": ("id", "updated_at"),
            "recurring_financial_items": ("id", "updated_at"),
            "application_settings": ("setting_key", "last_updated_at")
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
        # print(f"{print_prefix} Triggers para timestamps verificados/creados.") # Un solo mensaje
        print(f"{print_prefix} Todas las tablas y triggers definidos han sido procesados.")

        conn.commit()
        print(f"{print_prefix} Cambios comprometidos exitosamente.")

    except sqlite3.Error as e:
        print(f"ERROR (database.py): Ocurrió un error durante creación/verificación de tablas: {e}")
        conn.rollback()
        all_ok = False
    finally:
        if conn:
            conn.close()
    
    return all_ok


if __name__ == "__main__":
    print(f"--- {os.path.basename(__file__)} Self-Check and Initialization ---")
    if not ensure_directory_exists(DB_DIRECTORY):
        print(f"CRÍTICO: Falló creación del dir de BD: {DB_DIRECTORY}. Abortando.")
    else:
        print(f"Directorio de BD verificado/creado: {DB_DIRECTORY}")
        print(f"Ruta completa de BD: {FULL_DATABASE_PATH}")
        print("\nIntentando crear/verificar tablas...")
        success = create_or_verify_tables()
        if success:
            print("\nInicialización de BD completada exitosamente.")
            # Pequeña prueba de verificación
            conn_t = get_db_connection()
            if conn_t:
                try:
                    c_t = conn_t.cursor()
                    c_t.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_users';")
                    if c_t.fetchone(): print("Verificación: Tabla 'system_users' existe.")
                    else: print("ADVERTENCIA: Tabla 'system_users' NO encontrada post-creación.")
                except sqlite3.Error as et: print(f"Error verificando tabla: {et}")
                finally: conn_t.close()
        else:
            print("\nFALLÓ inicialización de la BD.")