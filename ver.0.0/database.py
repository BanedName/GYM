import sqlite3
import os
from config import DATABASE_NAME # Asegúrate de que config.py define DATABASE_NAME

# Obtener la ruta absoluta del directorio del script actual
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Crear la ruta absoluta para el archivo de la base de datos
DATABASE_PATH = os.path.join(BASE_DIR, DATABASE_NAME)


def get_db_connection():
    """
    Establece una conexión con la base de datos SQLite.
    La base de datos se creará si no existe en la ruta especificada.
    Devuelve un objeto de conexión.
    """
    try:
        # print(f"Intentando conectar/crear base de datos en: {DATABASE_PATH}")
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Permite acceder a las columnas por nombre
        conn.execute("PRAGMA foreign_keys = ON;") # Habilitar el soporte de claves foráneas
        # print("Conexión a la base de datos establecida.")
        return conn
    except sqlite3.Error as e:
        print(f"Error al conectar con la base de datos: {e}")
        return None

def create_tables():
    """
    Crea las tablas necesarias en la base de datos si no existen.
    """
    conn = get_db_connection()
    if not conn:
        print("No se pudo establecer conexión con la base de datos para crear tablas.")
        return

    cursor = conn.cursor()

    try:
        # --- Tabla de Usuarios (para login y roles) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('superuser', 'program_admin', 'data_admin', 'staff')),
                email TEXT UNIQUE, -- Opcional, pero útil para recuperación de contraseña, etc.
                is_active INTEGER DEFAULT 1, -- 1 para activo, 0 para inactivo
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Tabla 'users' verificada/creada.")

        # --- Tabla de Miembros (alumnos) ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gym_id TEXT UNIQUE NOT NULL,      -- Número identificativo del gimnasio (ej. GYM-0001)
                full_name TEXT NOT NULL,
                date_of_birth DATE,
                gender TEXT CHECK(gender IN ('male', 'female', 'other', NULL)), -- NULL si no se especifica
                email TEXT UNIQUE,
                phone TEXT,
                address TEXT,
                join_date DATE DEFAULT (date('now')),
                membership_type TEXT,             -- Ej: Mensual, Anual, Pack 10 clases
                membership_start_date DATE,
                membership_expiry_date DATE,
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'pending_payment', 'expired')),
                photo_path TEXT,                  -- Ruta a la foto para el carné (si se implementa)
                emergency_contact_name TEXT,
                emergency_contact_phone TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Tabla 'members' verificada/creada.")

        # --- Tabla de Asistencia ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id INTEGER NOT NULL,
                check_in_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                check_out_time TIMESTAMP,           -- Opcional, puede ser NULL si solo se registra entrada
                activity_id INTEGER,              -- Opcional: para registrar a qué clase o actividad asistió
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE, -- Si se borra un miembro, se borran sus asistencias
                FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE SET NULL -- Si se define una tabla 'activities'
            )
        """)
        # NOTA: Para la FK activity_id, necesitaríamos una tabla 'activities'
        # CREATE TABLE IF NOT EXISTS activities (id INTEGER PRIMARY KEY, name TEXT UNIQUE, description TEXT);
        print("Tabla 'attendance' verificada/creada.")


        # --- Tabla de Transacciones Financieras ---
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS financial_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')), -- 'income' o 'expense'
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                transaction_date DATE DEFAULT (date('now')),
                category TEXT,                    -- Ej: 'membership_fee', 'utilities', 'salary', 'equipment_purchase'
                payment_method TEXT CHECK(payment_method IN ('cash', 'card', 'transfer', 'direct_debit', NULL)),
                member_id INTEGER,                -- Para ingresos relacionados con un miembro (ej. cuota)
                user_id INTEGER,                  -- Usuario que registró la transacción (personal del gimnasio)
                reference_id TEXT,                -- ID de factura, recibo externo, etc.
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE SET NULL, -- Si se borra un miembro, no borrar la transacción
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL    -- Si se borra un usuario, no borrar la transacción
            )
        """)
        print("Tabla 'financial_transactions' verificada/creada.")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recurring_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                default_amount REAL NOT NULL,
                category TEXT NOT NULL,
                frequency TEXT NOT NULL CHECK(frequency IN ('daily', 'weekly', 'monthly', 'quarterly', 'biannual', 'annual')),
                start_date DATE NOT NULL,
                day_of_month_to_apply INTEGER, -- Para 'monthly', ej. 1 para el día 1, NULL si no aplica
                day_of_week_to_apply INTEGER, -- Para 'weekly' (0=Lunes, 6=Domingo), NULL si no aplica
                next_due_date DATE NOT NULL,  -- La próxima fecha en que este gasto debe registrarse
                end_date DATE,                -- Opcional, si el gasto recurrente tiene una fecha de fin
                is_active INTEGER DEFAULT 1,  -- 0 para inactivo, 1 para activo
                auto_apply INTEGER DEFAULT 0, -- 0 para confirmación manual, 1 para aplicación automática (con cuidado)
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Tabla 'recurring_expenses' verificada/creada.")

        # Asegúrate de añadir 'recurring_expenses' a la lista para los triggers de updated_at si es necesario
        # tables_with_timestamps = { ... 'recurring_expenses': ('id', 'updated_at'), ... }
        # (Esta línea ya está genérica y debería cubrirlo si añades la tabla al diccionario `tables_with_timestamps`
        #  dentro de database.py)

        # --- Tabla de Configuración del Programa (para el program_admin) ---
        # Esta tabla es más avanzada y para "configurar opciones del programa".
        # Podría usarse para almacenar cosas como: nombre del gimnasio, moneda, recordatorios automáticos, etc.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS program_settings (
                key TEXT PRIMARY KEY,             -- Ej: 'gym_name', 'currency_symbol', 'reminder_days_before_expiry'
                value TEXT,
                description TEXT,
                data_type TEXT DEFAULT 'string' CHECK(data_type IN ('string', 'integer', 'float', 'boolean', 'json')), -- Para interpretar el 'value' correctamente
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Tabla 'program_settings' verificada/creada.")


        # --- (Opcional) Tabla de Clases/Actividades ---
        # Si queremos que el "activity_id" en la tabla attendance tenga sentido.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,        -- Ej: 'Yoga', 'Spinning', 'Zumba', 'Sala de Pesas'
                description TEXT,
                instructor_id INTEGER,            -- Si tienes una tabla de instructores o usas la de users
                max_capacity INTEGER,
                duration_minutes INTEGER,
                schedule_info TEXT,               -- Podría ser un JSON o texto describiendo el horario
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (instructor_id) REFERENCES users(id) ON DELETE SET NULL -- Asumiendo que los instructores son usuarios
            )
        """)
        print("Tabla 'activities' (opcional) verificada/creada.")


        # --- (Opcional) Triggers para 'updated_at' ---
        # SQLite no tiene ON UPDATE CURRENT_TIMESTAMP directamente en la definición de la columna
        # como MySQL, así que se usan triggers.
        tables_with_updated_at = ['users', 'members', 'financial_transactions', 'program_settings', 'activities']
        for table_name in tables_with_updated_at:
            trigger_name = f"update_{table_name}_updated_at"
            cursor.execute(f"""
                CREATE TRIGGER IF NOT EXISTS {trigger_name}
                AFTER UPDATE ON {table_name}
                FOR EACH ROW
                BEGIN
                    UPDATE {table_name}
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = OLD.id;  -- O el PK correspondiente si no es 'id' (ej. 'key' para program_settings)
                END;
            """)
        print("Triggers para 'updated_at' verificados/creados (si aplica y son soportados).")


        conn.commit()
        print("--- Todas las tablas y triggers han sido verificados/creados exitosamente. ---")

    except sqlite3.Error as e:
        print(f"Error durante la creación de tablas: {e}")
        conn.rollback() # Revertir cambios si hubo un error
    finally:
        conn.close()
        # print("Conexión a la base de datos cerrada.")

if __name__ == '__main__':
    # Este bloque permite ejecutar `python database.py` directamente para crear/verificar las tablas.
    print(f"Inicializando base de datos '{DATABASE_NAME}'...")
    # Primero, asegurar que config.py existe y define DATABASE_NAME
    try:
        from config import DATABASE_NAME # Solo para check
    except ImportError:
        print("ERROR: No se pudo importar 'DATABASE_NAME' desde 'config.py'.")
        print("Asegúrate de que 'config.py' existe en el mismo directorio y define esta variable.")
        print("Ejemplo: DATABASE_NAME = 'gimnasio_app.db'")
        exit()
    except AttributeError:
        print("ERROR: La variable 'DATABASE_NAME' no está definida en 'config.py'.")
        exit()

    create_tables()
    print(f"Proceso de inicialización de base de datos para '{DATABASE_NAME}' completado.") 