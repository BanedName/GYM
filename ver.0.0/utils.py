# utils.py
import hashlib
import uuid
from datetime import datetime, timedelta, date
import re # Para expresiones regulares (validación de email)
from config import DATE_FORMAT_DISPLAY, DATETIME_FORMAT_DISPLAY # Importar formatos de fecha

def hash_password(password: str) -> str:
    """
    Genera un hash SHA-256 para la contraseña proporcionada.
    En un entorno de producción, se recomendaría usar algoritmos más robustos
    como bcrypt o Argon2, que incluyen "salting" y son más resistentes
    a ataques de fuerza bruta y rainbow tables.
    """
    if not password: # Evitar error si la contraseña es None o vacía
        return ""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def generate_gym_id(prefix: str = "GYM") -> str:
    """
    Genera un ID de gimnasio único y relativamente corto.
    Ejemplo: GYM-A1B2C
    Usa los primeros 6 caracteres de un UUID4 y los convierte a mayúsculas.
    """
    # UUID4 genera un identificador único aleatorio. Tomamos una porción para hacerlo más corto.
    unique_part = str(uuid.uuid4().hex)[:6].upper()
    return f"{prefix}-{unique_part}"

def generate_invoice_number(prefix: str = "INV") -> str:
    """
    Genera un número de factura/recibo único basado en la fecha y una parte aleatoria.
    Ejemplo: INV-20231027-D4E5F6
    """
    timestamp_part = datetime.now().strftime("%Y%m%d")
    random_part = str(uuid.uuid4().hex)[:6].upper()
    return f"{prefix}-{timestamp_part}-{random_part}"

def format_date(date_obj: date | datetime | None, default_format: str = DATE_FORMAT_DISPLAY) -> str:
    """
    Formatea un objeto date o datetime a una cadena usando el formato de config.py.
    Si el objeto es None, devuelve una cadena vacía o un placeholder.
    """
    if date_obj is None:
        return "N/A" # o ""
    try:
        return date_obj.strftime(default_format)
    except AttributeError: # Si no es un objeto date/datetime válido
        return str(date_obj) # Devolver como string si falla el formato

def format_datetime(datetime_obj: datetime | None, default_format: str = DATETIME_FORMAT_DISPLAY) -> str:
    """
    Formatea un objeto datetime a una cadena usando el formato de config.py.
    Si el objeto es None, devuelve una cadena vacía o un placeholder.
    """
    if datetime_obj is None:
        return "N/A" # o ""
    try:
        return datetime_obj.strftime(default_format)
    except AttributeError:
        return str(datetime_obj)

def parse_date_string(date_str: str, date_format: str = "%Y-%m-%d") -> date | None:
    """
    Convierte una cadena de fecha (formato YYYY-MM-DD por defecto) a un objeto date.
    Devuelve None si la cadena no es válida.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), date_format).date()
    except ValueError:
        return None

def parse_datetime_string(datetime_str: str, date_format: str = "%Y-%m-%d %H:%M:%S") -> datetime | None:
    """
    Convierte una cadena de fecha y hora a un objeto datetime.
    Devuelve None si la cadena no es válida.
    """
    if not datetime_str:
        return None
    try:
        return datetime.strptime(datetime_str.strip(), date_format)
    except ValueError:
        return None

def calculate_expiry_date(start_date: date, duration_days: int) -> date:
    """
    Calcula la fecha de expiración sumando N días a una fecha de inicio.
    """
    if not isinstance(start_date, date):
        raise ValueError("start_date debe ser un objeto date.")
    if not isinstance(duration_days, int) or duration_days < 0:
        raise ValueError("duration_days debe ser un entero no negativo.")
    return start_date + timedelta(days=duration_days)

def is_valid_email(email: str) -> bool:
    """
    Valida si una cadena tiene un formato de email básico.
    Esta es una validación simple, para producción se podrían usar librerías más completas.
    """
    if not email:
        return False
    # Expresión regular simple para validación de email
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None

def is_valid_phone(phone: str) -> bool:
    """
    Valida si una cadena parece un número de teléfono (muy básico).
    Permite números, espacios, guiones y el símbolo +.
    Debe tener al menos N dígitos (ej. 7).
    """
    if not phone:
        return False # O True si es opcional
    cleaned_phone = re.sub(r"[^0-9]", "", phone) # Elimina todo excepto dígitos
    # Asume una longitud mínima para un teléfono, ej. 7 dígitos. Ajusta según necesidad.
    return len(cleaned_phone) >= 7 and phone.replace('+', '', 1).replace('-', '').replace(' ', '').isdigit()

def clean_string_input(input_str: str | None) -> str:
    """
    Limpia una cadena de entrada eliminando espacios al principio y al final.
    Devuelve una cadena vacía si la entrada es None.
    """
    if input_str is None:
        return ""
    return input_str.strip()

def format_currency(amount: float | int | None, currency_symbol: str = "€") -> str:
    """
    Formatea un número como moneda.
    """
    if amount is None:
        return f"0.00 {currency_symbol}"
    try:
        # Formatea a dos decimales
        return f"{float(amount):.2f} {currency_symbol}"
    except (ValueError, TypeError):
        return f"Inválido {currency_symbol}"

# Podrías añadir más funciones de utilidad según las necesites:
# - Funciones para limpiar nombres (capitalizar, etc.)
# - Funciones para convertir unidades
# - Generadores de slugs para URLs (si fuera una app web)
# - Validadores más específicos (ej. DNI/NIE si aplica para tu región)

if __name__ == "__main__":
    print("--- Pruebas de funciones de utils.py ---")

    # Hashing de contraseña
    print("\nHash de 'password123':", hash_password("password123"))
    print("Hash de contraseña vacía:", hash_password(""))

    # Generación de IDs
    print("\nID de Gimnasio generado:", generate_gym_id())
    print("ID de Gimnasio con prefijo 'CLUB':", generate_gym_id(prefix="CLUB"))
    print("Número de Factura generado:", generate_invoice_number())

    # Formateo de fechas
    today = date.today()
    now = datetime.now()
    print(f"\nFecha de hoy ({DATE_FORMAT_DISPLAY}):", format_date(today))
    print(f"Fecha y hora ahora ({DATETIME_FORMAT_DISPLAY}):", format_datetime(now))
    print("Fecha None:", format_date(None))

    # Parseo de fechas
    print("\nParseo de '2023-12-25':", parse_date_string("2023-12-25"))
    print("Parseo de '25/12/2023' con formato:", parse_date_string("25/12/2023", "%d/%m/%Y"))
    print("Parseo de fecha inválida:", parse_date_string("esto no es una fecha"))

    # Cálculo de expiración
    start = date(2023, 1, 15)
    print(f"\nExpiración de membresía desde {format_date(start)} + 30 días:", format_date(calculate_expiry_date(start, 30)))
    print(f"Expiración de membresía desde {format_date(start)} + 365 días:", format_date(calculate_expiry_date(start, 365)))

    # Validación de email
    print("\nValidación de 'test@example.com':", is_valid_email("test@example.com"))
    print("Validación de 'test@example':", is_valid_email("test@example"))
    print("Validación de email vacío:", is_valid_email(""))

    # Validación de teléfono
    print("\nValidación de '600123123':", is_valid_phone("600123123"))
    print("Validación de '+34 600-123-123':", is_valid_phone("+34 600-123-123"))
    print("Validación de '123':", is_valid_phone("123")) # Probablemente False
    print("Validación de teléfono vacío:", is_valid_phone(""))

    # Limpieza de cadena
    print("\nLimpieza de '  texto con espacios  ':", f"'{clean_string_input('  texto con espacios  ')}'")
    print("Limpieza de None:", f"'{clean_string_input(None)}'")

    # Formateo de moneda
    from config import CURRENCY_SYMBOL # Para usar el de config.py
    print("\nFormateo de 123.456:", format_currency(123.456, CURRENCY_SYMBOL))
    print("Formateo de 50:", format_currency(50, CURRENCY_SYMBOL))
    print("Formateo de None:", format_currency(None, CURRENCY_SYMBOL))