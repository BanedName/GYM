# gimnasio_mgmt_gui/core_logic/utils.py
# Módulo de funciones de utilidad generales para la aplicación GymManager Pro.

import hashlib
import uuid
from datetime import datetime, date, timedelta
import re # Para expresiones regulares (validación de formatos)
import os # Para operaciones del sistema de archivos (ej. asegurar directorios)
from decimal import Decimal, InvalidOperation # Para manejo preciso de moneda

# --- Importación de Configuraciones Globales ---
# utils.py está en core_logic/, config.py está en la raíz (gimnasio_mgmt_gui/).
# Si ejecutamos main_gui.py (desde la raíz), Python añade la raíz al sys.path.
# Así, la importación directa de 'config' debería funcionar.
try:
    from config import (
        UI_DISPLAY_DATE_FORMAT, UI_DISPLAY_DATETIME_FORMAT,
        DB_STORAGE_DATE_FORMAT, DB_STORAGE_DATETIME_FORMAT,
        CURRENCY_DISPLAY_SYMBOL, APP_DATA_ROOT_DIR,
        MEMBER_PHOTOS_SUBDIR_NAME, FINANCIAL_REPORTS_SUBDIR_NAME,
        DATABASE_BACKUPS_SUBDIR_NAME, LOG_FILES_SUBDIR_NAME,
        DATABASE_SUBDIR_NAME # Añadido para crear el subdirectorio de la BD
    )
except ImportError as e:
    # Este bloque es principalmente para pruebas directas de utils.py o si hay problemas de path.
    # En una ejecución normal desde main_gui.py, la importación de config debería funcionar.
    print(f"ADVERTENCIA (utils.py): No se pudo importar 'config'. Usando valores por defecto. Error: {e}")
    # Definir valores de fallback mínimos para que las funciones no fallen catastróficamente
    UI_DISPLAY_DATE_FORMAT = "%d/%m/%Y"
    UI_DISPLAY_DATETIME_FORMAT = "%d/%m/%Y %H:%M"
    DB_STORAGE_DATE_FORMAT = "%Y-%m-%d"
    DB_STORAGE_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    CURRENCY_DISPLAY_SYMBOL = "$" # Fallback genérico
    # Fallback para APP_DATA_ROOT_DIR, etc., si es necesario para funciones de prueba.
    # Podríamos incluso decidir no definir estos fallbacks y dejar que falle si config no se carga,
    # ya que la app no debería funcionar sin su config.
    APP_DATA_ROOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_temp_app_data_utils_fallback")
    MEMBER_PHOTOS_SUBDIR_NAME = "member_photos_fb"
    FINANCIAL_REPORTS_SUBDIR_NAME = "reports_fb"
    DATABASE_BACKUPS_SUBDIR_NAME = "backups_fb"
    LOG_FILES_SUBDIR_NAME = "logs_fb"
    DATABASE_SUBDIR_NAME = "db_fb"


# --- FUNCIONES DE HASHING Y GENERACIÓN DE IDs ---

def hash_secure_password(password: str) -> str:
    """
    Genera un hash SHA-256 para la contraseña.
    ¡¡IMPORTANTE!! En un entorno de producción real, se DEBE usar bcrypt o Argon2
    para una mayor seguridad contra ataques de fuerza bruta y tablas rainbow.
    SHA-256 sin "salting" adecuado y múltiples iteraciones no es suficiente para contraseñas.
    """
    if not password or not isinstance(password, str):
        # Podríamos lanzar un ValueError aquí, o devolver un hash de cadena vacía/predeterminado.
        # Por ahora, para no romper flujos que esperan una cadena, hasheamos una cadena vacía.
        password = ""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_internal_id(prefix: str = "GID", length: int = 12) -> str:
    """
    Genera un ID alfanumérico único para uso interno (ej. ID de miembro, ID de transacción).
    Usa un prefijo y una porción de un UUID4 para asegurar unicidad.
    """
    if not prefix or not isinstance(prefix, str):
        prefix = "ID"
    if not isinstance(length, int) or length <= 0:
        length = 8 # Longitud por defecto para la parte única

    # UUID4.hex es 32 caracteres. Tomamos una porción.
    unique_part = str(uuid.uuid4().hex).upper()[:length]
    return f"{prefix.upper()}-{unique_part}"


# --- FUNCIONES DE MANEJO DE FECHAS Y HORAS ---

def get_current_date_for_db() -> date:
    """Devuelve la fecha actual como un objeto date."""
    return date.today()

def get_current_datetime_for_db() -> datetime:
    """Devuelve la fecha y hora actual como un objeto datetime."""
    return datetime.now()

def format_date_for_ui(date_obj: date | datetime | None) -> str:
    """Formatea un objeto date o datetime a una cadena para mostrar en la UI."""
    if date_obj is None:
        return "" # Una cadena vacía es a menudo mejor para la UI que "N/A"
    if isinstance(date_obj, datetime): # Si nos pasan un datetime, tomar solo la parte de fecha
        date_obj = date_obj.date()
    try:
        return date_obj.strftime(UI_DISPLAY_DATE_FORMAT)
    except (AttributeError, ValueError): # Si date_obj no es formateable
        return str(date_obj) # Fallback a representación de cadena

def format_datetime_for_ui(datetime_obj: datetime | None) -> str:
    """Formatea un objeto datetime a una cadena para mostrar en la UI."""
    if datetime_obj is None:
        return ""
    try:
        return datetime_obj.strftime(UI_DISPLAY_DATETIME_FORMAT)
    except (AttributeError, ValueError):
        return str(datetime_obj)

def convert_date_to_db_string(date_obj: date | datetime | None) -> str | None:
    """Convierte un objeto date/datetime a una cadena para almacenar en la BD."""
    if date_obj is None:
        return None
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    try:
        return date_obj.strftime(DB_STORAGE_DATE_FORMAT)
    except (AttributeError, ValueError):
        return None # No se pudo convertir

def convert_datetime_to_db_string(datetime_obj: datetime | None) -> str | None:
    """Convierte un objeto datetime a una cadena para almacenar en la BD."""
    if datetime_obj is None:
        return None
    try:
        return datetime_obj.strftime(DB_STORAGE_DATETIME_FORMAT)
    except (AttributeError, ValueError):
        return None

def parse_string_to_date(date_str: str | None, permissive_formats: bool = True) -> date | None:
    """
    Convierte una cadena de fecha a un objeto date.
    Prueba con el formato de almacenamiento DB y luego con el formato de UI si es permisivo.
    """
    if not date_str or not isinstance(date_str, str):
        return None

    formats_to_attempt = [DB_STORAGE_DATE_FORMAT]
    if permissive_formats:
        formats_to_attempt.append(UI_DISPLAY_DATE_FORMAT)
        # Se podrían añadir más formatos comunes como "%d-%m-%Y" o "%m/%d/%Y"
        # formats_to_attempt.extend(["%d-%m-%Y", "%m/%d/%Y"])

    for fmt in formats_to_attempt:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue # Intentar el siguiente formato
    return None # Ningún formato coincidió

def calculate_member_expiry_date(start_date: date, plan_duration_days: int) -> date:
    """Calcula la fecha de expiración de una membresía."""
    if not isinstance(start_date, date):
        raise TypeError("La fecha de inicio debe ser un objeto 'date'.")
    if not isinstance(plan_duration_days, int) or plan_duration_days <= 0: # Duración debe ser positiva
        raise ValueError("La duración en días debe ser un entero positivo.")
    # Expiración es al final del último día, por lo que sumamos los días y restamos 1 si la lógica es inclusiva,
    # o simplemente sumamos si el inicio es día 1 y dura X días.
    # Por simplicidad, si dura 30 días, el día 30 es el último día válido.
    # Entonces la fecha de "expiración" (cuándo ya no es válido) sería start_date + duration_days.
    return start_date + timedelta(days=plan_duration_days)


def calculate_age(birth_date: date | str | None) -> int | None:
    """Calcula la edad a partir de una fecha de nacimiento (objeto date o cadena)."""
    if birth_date is None:
        return None

    if isinstance(birth_date, str):
        dob = parse_string_to_date(birth_date, permissive_formats=True)
    elif isinstance(birth_date, date):
        dob = birth_date
    elif isinstance(birth_date, datetime): # Si es datetime, convertir a date
        dob = birth_date.date()
    else:
        return None # Tipo no soportado

    if dob is None: # Si el parseo de la cadena falló
        return None

    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age if age >= 0 else None # No debería dar edad negativa con fechas válidas


# --- FUNCIONES DE VALIDACIÓN DE CADENAS Y FORMATOS ---

def sanitize_text_input(text: str | None, allow_empty: bool = False) -> str | None:
    """Limpia una cadena de texto (strip). Devuelve None si es vacío y no se permite."""
    if text is None:
        return None if not allow_empty else ""
    
    cleaned_text = str(text).strip()
    if not cleaned_text and not allow_empty:
        return None
    return cleaned_text

def is_valid_system_username(username: str) -> bool:
    """Valida formato de nombre de usuario del sistema (longitud, caracteres)."""
    if not username or not isinstance(username, str):
        return False
    # Ejemplo: 3-25 caracteres, alfanuméricos, opcionalmente con guiones bajos o puntos (no al inicio/final ni seguidos).
    pattern = r"^[a-zA-Z0-9](?:[a-zA-Z0-9._-]{1,23}[a-zA-Z0-9])?$"
    if not (3 <= len(username) <= 25 and re.fullmatch(pattern, username)):
        return False
    # Evitar nombres problemáticos (podrías añadir más)
    if username.lower() in ["admin", "root", "superuser"]: # Quizá no permitir estos para usuarios normales
         pass # O retornar False si no quieres que se usen.
    return True

def check_password_strength(password: str) -> tuple[bool, str]:
    """
    Verifica la fortaleza de una contraseña.
    Devuelve: (es_suficientemente_fuerte, mensaje_de_retroalimentación).
    """
    if not password or not isinstance(password, str):
        return False, "La contraseña no puede estar vacía."

    if len(password) < 8:
        return False, "Mínimo 8 caracteres."
    if not re.search(r"[A-Z]", password):
        return False, "Debe incluir al menos una mayúscula (A-Z)."
    if not re.search(r"[a-z]", password):
        return False, "Debe incluir al menos una minúscula (a-z)."
    if not re.search(r"[0-9]", password):
        return False, "Debe incluir al menos un número (0-9)."
    # Opcional: Requerir un símbolo especial
    # if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
    #     return False, "Debe incluir al menos un símbolo especial."
    return True, "Contraseña válida."

# --- FUNCIONES FINANCIERAS Y DE FORMATO DE MONEDA ---

def format_currency_for_display(amount: float | int | Decimal | None) -> str:
    """Formatea un valor numérico como moneda para la UI."""
    if amount is None:
        # Podrías querer mostrar "0.00 €" o simplemente ""
        return f"0.00 {CURRENCY_DISPLAY_SYMBOL}"
    try:
        # Usar Decimal para precisión si es posible, sino float
        if not isinstance(amount, Decimal):
            amount_decimal = Decimal(str(amount)) # Convertir float a Decimal vía string para precisión
        else:
            amount_decimal = amount
        # :.2f para dos decimales, {} para el símbolo de moneda
        return f"{amount_decimal:.2f} {CURRENCY_DISPLAY_SYMBOL}"
    except (InvalidOperation, ValueError, TypeError): # InvalidOperation para Decimal
        return f"Valor Inválido {CURRENCY_DISPLAY_SYMBOL}"

def parse_string_to_decimal(value_str: str | None, default_if_error: Decimal | None = None) -> Decimal | None:
    """
    Convierte una cadena a un objeto Decimal para manejo monetario preciso.
    Acepta '.' y ',' como separadores decimales.
    """
    if value_str is None or not isinstance(value_str, str) or not value_str.strip():
        return default_if_error

    cleaned_str = value_str.strip().replace(CURRENCY_DISPLAY_SYMBOL, "").replace(" ", "") # Quitar símbolo y espacios
    
    # Primero intentar reemplazar coma por punto si es el único separador no numérico
    # (para manejar "1,234.56" y "1234,56")
    if cleaned_str.count(',') == 1 and cleaned_str.count('.') == 0:
        cleaned_str = cleaned_str.replace(',', '.')
    elif cleaned_str.count('.') == 1 and cleaned_str.count(',') > 1 : # ej 1,234.56
        cleaned_str = cleaned_str.replace(',', '')
    # Si hay múltiples comas y puntos de forma incorrecta, la conversión fallará igualmente

    try:
        return Decimal(cleaned_str)
    except InvalidOperation:
        return default_if_error


# --- FUNCIONES DE GESTIÓN DE DIRECTORIOS ---

def ensure_directory_exists(dir_path: str) -> bool:
    """
    Asegura que un directorio exista. Si no, intenta crearlo.
    Devuelve True si el directorio existe o fue creado, False en caso de error.
    """
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True) # exist_ok=True evita error si se crea entre el check y el makedirs (concurrencia)
            # print(f"Directorio creado: {dir_path}") # Para depuración
            return True
        except OSError as e:
            print(f"ERROR (utils.py): No se pudo crear el directorio '{dir_path}'. Error: {e}")
            return False
    return True

def setup_app_data_directories():
    """
    Crea todos los directorios de datos necesarios para la aplicación si no existen.
    Se llama una vez al inicio de la aplicación.
    """
    print_prefix = "INFO (utils.py - Directorios):"
    base_created = ensure_directory_exists(APP_DATA_ROOT_DIR)
    if not base_created:
        # Si el directorio base no se puede crear, los demás tampoco.
        # Se podría lanzar una excepción crítica aquí si es necesario.
        print(f"CRÍTICO: No se pudo crear el directorio base de datos: {APP_DATA_ROOT_DIR}. La aplicación podría no funcionar.")
        return False

    # Crear subdirectorios (esta lista debe coincidir con lo definido en config.py)
    subdirs_to_create = [
        DATABASE_SUBDIR_NAME,
        MEMBER_PHOTOS_SUBDIR_NAME,
        FINANCIAL_REPORTS_SUBDIR_NAME,
        DATABASE_BACKUPS_SUBDIR_NAME,
        LOG_FILES_SUBDIR_NAME
    ]
    all_ok = True
    for subdir_name in subdirs_to_create:
        full_path = os.path.join(APP_DATA_ROOT_DIR, subdir_name)
        if not ensure_directory_exists(full_path):
            print(f"{print_prefix} Falló la creación del subdirectorio: {full_path}")
            all_ok = False # Marcar que algo falló, pero continuar intentando crear los demás
    
    if all_ok:
        print(f"{print_prefix} Todos los directorios de datos de la aplicación han sido verificados/creados en '{APP_DATA_ROOT_DIR}'.")
    else:
        print(f"{print_prefix} Algunos directorios de datos no pudieron ser creados. Revisa los mensajes de error.")
    return all_ok


# --- Script de autocomprobación para este archivo (ejecutar `python gimnasio_mgmt_gui/core_logic/utils.py`) ---
#if __name__ == "__main__":
#    print(f"--- {__name__} Self-Check ---") # Usar __name__ para el nombre del módulo actual
#    print(f"Probando funciones de utilidad de {os.path.basename(__file__)}:")
#
#    print("\n--- Pruebas de Directorios ---")
#    # NOTA: APP_DATA_ROOT_DIR aquí usará el valor de config o el fallback.
    # La creación de directorios de prueba puede ser útil aquí.
#    if APP_DATA_ROOT_DIR: # Asegurarse de que la variable está definida
#        print(f"Directorio de datos de la app configurado: {APP_DATA_ROOT_DIR}")
#        if "fallback" in APP_DATA_ROOT_DIR.lower():
#             print("  (Usando ruta de fallback porque config.py no se cargó o no definió APP_DATA_ROOT_DIR)")
        # setup_app_data_directories() # Descomentar para probar la creación de directorios

#    print("\n--- Pruebas de Hashing y IDs ---")
#    print(f"Hash de 'TestPass123': {hash_secure_password('TestPass123')}")
#    print(f"ID Interno generado (prefijo ENT): {generate_internal_id(prefix='ENT', length=8)}")

#    print("\n--- Pruebas de Fechas y Horas ---")
#    today_obj = date.today()
#    now_obj = datetime.now()
#    print(f"Fecha DB actual: {get_current_date_for_db()} (objeto)")
#    print(f"Fecha UI formateada para hoy: {format_date_for_ui(today_obj)}")
#    print(f"Fecha-Hora UI formateada para ahora: {format_datetime_for_ui(now_obj)}")
#    test_date_str_db = "2024-07-15"
#    test_date_str_ui = "15/07/2024"
#    print(f"Parsear '{test_date_str_db}': {parse_string_to_date(test_date_str_db)}")
#    print(f"Parsear '{test_date_str_ui}' (permisivo): {parse_string_to_date(test_date_str_ui, permissive_formats=True)}")
#    expiry = calculate_member_expiry_date(parse_string_to_date(test_date_str_db), 30)
#    print(f"Expiración para {test_date_str_db} + 30 días: {format_date_for_ui(expiry)}")
#    print(f"Edad para '01/01/1990': {calculate_age('01/01/1990')} años")

#    print("\n--- Pruebas de Validación ---")
#    print(f"Username 'john.doe_123' válido? {is_valid_system_username('john.doe_123')}")
#    print(f"Username '.john' válido? {is_valid_system_username('.john')}") # Debería ser False
#    pw_test_strong = "StrongPass123"
#    pw_test_weak = "weak"
#    valid_strong, msg_strong = check_password_strength(pw_test_strong)
#    valid_weak, msg_weak = check_password_strength(pw_test_weak)
#    print(f"Fortaleza de '{pw_test_strong}': {valid_strong} ({msg_strong})")
#    print(f"Fortaleza de '{pw_test_weak}': {valid_weak} ({msg_weak})")
#    print(f"Sanitizar '  texto con espacios  ': '{sanitize_text_input('  texto con espacios  ')}'")

#    print("\n--- Pruebas de Moneda ---")
#    print(f"Formato de 1234.56: {format_currency_for_display(Decimal('1234.56'))}")
#    print(f"Formato de 99: {format_currency_for_display(99)}")
#    print(f"Parsear '1.234,56' a Decimal: {parse_string_to_decimal('1.234,56')}")
#    print(f"Parsear '1234.56' a Decimal: {parse_string_to_decimal('1234.56')}")
#    print(f"Parsear '1234,56' a Decimal: {parse_string_to_decimal('1234,56')}")
#    print(f"Parsear 'texto inválido' a Decimal: {parse_string_to_decimal('texto inválido', default_if_error=Decimal('0.0'))}")

#    print(f"\n--- Fin de pruebas de {os.path.basename(__file__)} ---")

if __name__ == "__main__":
    print(f"--- {__name__} Self-Check ---")
    print(f"Probando funciones de utilidad de {os.path.basename(__file__)}:")

    # ... (Otras pruebas como antes) ...

    print("\n--- Pruebas de Fechas y Horas ---")
    today_obj = date.today()
    now_obj = datetime.now()
    print(f"Fecha DB actual: {get_current_date_for_db()} (objeto)") # get_current_date_for_db devuelve 'date'
    print(f"Fecha UI formateada para hoy: {format_date_for_ui(today_obj)}")
    print(f"Fecha-Hora UI formateada para ahora: {format_datetime_for_ui(now_obj)}")
    
    test_date_str_db = "2024-07-15"
    test_date_str_ui = "15/07/2024"
    
    parsed_date_from_db_str = parse_string_to_date(test_date_str_db)
    print(f"Parsear '{test_date_str_db}': {parsed_date_from_db_str}")
    
    parsed_date_from_ui_str = parse_string_to_date(test_date_str_ui, permissive_formats=True)
    print(f"Parsear '{test_date_str_ui}' (permisivo): {parsed_date_from_ui_str}")

    # --- CORRECCIÓN AQUÍ (Línea ~349 del original) ---
    # Manejar el caso en que parsed_date_from_db_str pueda ser None
    if parsed_date_from_db_str is not None:
        expiry = calculate_member_expiry_date(parsed_date_from_db_str, 30)
        print(f"Expiración para {test_date_str_db} + 30 días: {format_date_for_ui(expiry)}")
    else:
        print(f"No se pudo calcular la expiración para '{test_date_str_db}' porque el parseo falló.")
    # --- FIN DE LA CORRECCIÓN ---
        
    birth_date_str_1 = "01/01/1990"
    birth_date_obj_2 = date(1985, 5, 20) # Para probar con objeto date directamente
    
    print(f"Edad para '{birth_date_str_1}': {calculate_age(birth_date_str_1)} años")
    print(f"Edad para objeto date ({format_date_for_ui(birth_date_obj_2)}): {calculate_age(birth_date_obj_2)} años")
    print(f"Edad para None: {calculate_age(None)}")
    print(f"Edad para 'texto_invalido': {calculate_age('texto_invalido')}")


    print("\n--- Pruebas de Validación ---")
    # ... (pruebas de validación como antes) ...
    print(f"Username 'john.doe_123' válido? {is_valid_system_username('john.doe_123')}")
    print(f"Username '.john' válido? {is_valid_system_username('.john')}")
    pw_test_strong = "StrongPass123"
    pw_test_weak = "weak"
    valid_strong, msg_strong = check_password_strength(pw_test_strong)
    valid_weak, msg_weak = check_password_strength(pw_test_weak)
    print(f"Fortaleza de '{pw_test_strong}': {valid_strong} ({msg_strong})")
    print(f"Fortaleza de '{pw_test_weak}': {valid_weak} ({msg_weak})")
    print(f"Sanitizar '  texto con espacios  ': '{sanitize_text_input('  texto con espacios  ')}'")


    print("\n--- Pruebas de Moneda ---")
    # ... (pruebas de moneda como antes) ...
    print(f"Formato de 1234.56: {format_currency_for_display(Decimal('1234.56'))}")
    print(f"Formato de 99: {format_currency_for_display(99)}") # Probar con int también
    print(f"Parsear '1.234,56' a Decimal: {parse_string_to_decimal('1.234,56')}")
    print(f"Parsear '1234.56' a Decimal: {parse_string_to_decimal('1234.56')}")
    print(f"Parsear '1234,56' a Decimal: {parse_string_to_decimal('1234,56')}")
    print(f"Parsear 'texto inválido' a Decimal (con default): {parse_string_to_decimal('texto inválido', default_if_error=Decimal('0.00'))}")
    print(f"Parsear None a Decimal: {parse_string_to_decimal(None)}")


    print(f"\n--- Fin de pruebas de {os.path.basename(__file__)} ---")