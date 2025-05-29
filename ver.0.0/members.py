# members.py
import sqlite3
from datetime import date, datetime

from database import get_db_connection
from utils import (
    generate_gym_id,
    calculate_expiry_date,
    format_date,
    parse_date_string,
    clean_string_input,
    is_valid_email,
    is_valid_phone
)
from config import (
    DEFAULT_MEMBER_STATUS_NEW,
    DEFAULT_MEMBERSHIP_TYPES, # Usaremos esto para obtener precio, duración, etc.
    CURRENCY_SYMBOL,
    DATE_FORMAT_DISPLAY # Para la presentación de fechas
)

# Nota: Para registrar el pago de la membresía, este módulo podría interactuar
# con `finances.py` o señalar que se debe realizar un pago.
# Por simplicidad inicial, asumiremos que el pago se maneja y aquí solo se registra el miembro
# con su tipo de membresía.

def add_member(
    full_name: str,
    membership_type_key: str, # Clave interna del diccionario DEFAULT_MEMBERSHIP_TYPES
    join_date_str: str = None, # YYYY-MM-DD, si es None, se usa hoy
    date_of_birth_str: str = None, # YYYY-MM-DD
    email: str = None,
    phone: str = None,
    address: str = None,
    photo_path: str = None, # Ruta a la foto
    notes: str = None,
    emergency_contact_name: str = None,
    emergency_contact_phone: str = None,
    gender: str = None
) -> dict | None:
    """
    Añade un nuevo miembro a la base de datos.
    Calcula la fecha de expiración de la membresía basada en el tipo.
    Devuelve un diccionario con los datos del miembro creado o None si falla.
    """
    full_name = clean_string_input(full_name)
    if not full_name:
        print("Error: El nombre completo es obligatorio.")
        return None

    if membership_type_key not in DEFAULT_MEMBERSHIP_TYPES:
        print(f"Error: Tipo de membresía '{membership_type_key}' no válido.")
        print(f"Tipos válidos: {', '.join(DEFAULT_MEMBERSHIP_TYPES.keys())}")
        return None

    membership_info = DEFAULT_MEMBERSHIP_TYPES[membership_type_key]
    
    parsed_join_date = parse_date_string(join_date_str) if join_date_str else date.today()
    if not parsed_join_date:
        print("Error: Formato de fecha de inscripción inválido. Use YYYY-MM-DD o deje en blanco para hoy.")
        return None

    parsed_dob = parse_date_string(date_of_birth_str) if date_of_birth_str else None
    if date_of_birth_str and not parsed_dob: # Si se proveyó y no se pudo parsear
         print("Advertencia: Formato de fecha de nacimiento inválido. Se guardará como NULL.")


    # Validaciones opcionales
    if email and not is_valid_email(email):
        print(f"Advertencia: Email '{email}' parece inválido, pero se guardará.")
        # Podrías decidir hacerlo un error y retornar None si la validación es estricta.
    if phone and not is_valid_phone(phone):
        print(f"Advertencia: Teléfono '{phone}' parece inválido, pero se guardará.")

    gym_id = generate_gym_id() # Generar ID único para el miembro
    
    membership_start_date = parsed_join_date # La membresía empieza el día de la inscripción
    
    # Calcular fecha de expiración
    duration_days = membership_info.get('duration_days')
    if duration_days is None or duration_days <= 0 : # Para tipos sin duración fija o pases de sesión
        # Para pases de sesión, la expiración podría ser una fecha lejana o NULL si se controla por sesiones restantes.
        # Aquí, si duration_days no es > 0, lo ponemos NULL o una fecha muy lejana.
        # Para este ejemplo, si es un bono o clase suelta con duración de 1 día o más, se calcula.
        # Si es un tipo de membresía sin 'duration_days' explícita o 0, podríamos manejarlo diferente.
        # Para simplicidad ahora: si tiene 'duration_days' > 0, la calculamos.
        # Sino, la fecha de expiración será la misma que la de inicio (ej. pase diario) o se podría dejar NULL.
        # Vamos a asumir que si 'duration_days' existe y es >0, se calcula.
        if duration_days and duration_days > 0 :
             membership_expiry_date = calculate_expiry_date(membership_start_date, duration_days)
        else:
             membership_expiry_date = None # O manejarlo como un pase que no "expira" por tiempo sino por uso
             print(f"Advertencia: El tipo de membresía '{membership_info['display_name']}' no tiene una duración en días estándar para calcular expiración por tiempo.")

    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()

    try:
        sql = """
            INSERT INTO members (
                gym_id, full_name, date_of_birth, gender, email, phone, address,
                join_date, membership_type, membership_start_date, membership_expiry_date,
                status, photo_path, emergency_contact_name, emergency_contact_phone, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            gym_id, full_name, parsed_dob, gender,
            clean_string_input(email), clean_string_input(phone), clean_string_input(address),
            parsed_join_date, membership_info['display_name'], # Guardar el display_name
            membership_start_date, membership_expiry_date,
            DEFAULT_MEMBER_STATUS_NEW, # Estado inicial
            photo_path, # Podría ser validado o procesado
            clean_string_input(emergency_contact_name),
            clean_string_input(emergency_contact_phone),
            clean_string_input(notes)
        )
        cursor.execute(sql, params)
        member_db_id = cursor.lastrowid # ID de la fila en la BD
        conn.commit()

        print(f"Miembro '{full_name}' (ID: {gym_id}) añadido con membresía '{membership_info['display_name']}'.")
        print(f"Fecha de expiración de membresía: {format_date(membership_expiry_date) if membership_expiry_date else 'N/A'}")
        
        # Idealmente, aquí se registraría la transacción financiera del pago de esta membresía
        # llamando a una función de `finances.py`. Ej:
        # from finances import record_membership_payment
        # record_membership_payment(member_db_id, membership_info['price'], membership_info['display_name'])
        
        # Devolver los datos del miembro creado, incluyendo el ID de la BD y el gym_id
        return get_member_by_gym_id(gym_id)

    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: members.gym_id" in str(e): # Muy improbable si generate_gym_id es bueno
            print("Error: Conflicto de GYM_ID. Inténtelo de nuevo.")
        elif email and "UNIQUE constraint failed: members.email" in str(e):
            print(f"Error: El email '{email}' ya está registrado para otro miembro.")
        else:
            print(f"Error de base de datos al añadir miembro: {e}")
        return None
    except Exception as e:
        print(f"Error inesperado al añadir miembro: {e}")
        return None
    finally:
        conn.close()

def get_member_by_gym_id(gym_id: str) -> dict | None:
    """Busca y devuelve los datos de un miembro por su GYM_ID."""
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM members WHERE gym_id = ?", (gym_id,))
        member_data = cursor.fetchone()
        return dict(member_data) if member_data else None
    finally:
        conn.close()

def get_member_by_db_id(db_id: int) -> dict | None:
    """Busca y devuelve los datos de un miembro por su ID de base de datos."""
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM members WHERE id = ?", (db_id,))
        member_data = cursor.fetchone()
        return dict(member_data) if member_data else None
    finally:
        conn.close()


def get_all_members(active_only: bool = False, sort_by: str = "full_name", order: str = "ASC") -> list[dict]:
    """
    Devuelve una lista de todos los miembros.
    Puede filtrar por miembros activos y ordenar por diferentes campos.
    """
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor()

    # Validar sort_by y order para evitar SQL Injection si vinieran de input directo (no es el caso aquí)
    allowed_sort_columns = ["full_name", "gym_id", "join_date", "membership_expiry_date", "status"]
    if sort_by not in allowed_sort_columns:
        sort_by = "full_name"
    if order.upper() not in ["ASC", "DESC"]:
        order = "ASC"

    query = f"SELECT id, gym_id, full_name, email, phone, membership_type, status, membership_expiry_date FROM members"
    params = []

    if active_only:
        query += " WHERE status = ?"
        params.append("active") # O cualquier otro estado que se considere "activo"

    query += f" ORDER BY {sort_by} {order.upper()}"

    try:
        cursor.execute(query, tuple(params))
        members = [dict(row) for row in cursor.fetchall()]
        return members
    except Exception as e:
        print(f"Error al obtener todos los miembros: {e}")
        return []
    finally:
        conn.close()

def update_member_details(gym_id: str, updates: dict) -> bool:
    """
    Actualiza los detalles de un miembro existente.
    'updates' es un diccionario con {campo_a_actualizar: nuevo_valor}.
    No actualiza membresía aquí; eso sería una función de "renovar membresía".
    """
    member = get_member_by_gym_id(gym_id)
    if not member:
        print(f"Error: Miembro con GYM_ID '{gym_id}' no encontrado para actualizar.")
        return False

    allowed_fields_to_update = [
        "full_name", "date_of_birth", "gender", "email", "phone",
        "address", "photo_path", "emergency_contact_name",
        "emergency_contact_phone", "notes", "status"
    ]
    
    fields_to_set = []
    params = []

    for field, value in updates.items():
        if field in allowed_fields_to_update:
            # Validaciones antes de añadir
            if field == "email" and value and not is_valid_email(value):
                print(f"Advertencia: Nuevo email '{value}' parece inválido. Se guardará.")
            if field == "phone" and value and not is_valid_phone(value):
                 print(f"Advertencia: Nuevo teléfono '{value}' parece inválido. Se guardará.")
            if field == "date_of_birth" and value:
                parsed_value = parse_date_string(str(value)) # Asegurarse que es string para parsear
                if not parsed_value:
                    print(f"Advertencia: Fecha de nacimiento '{value}' inválida. No se actualizará.")
                    continue # Saltar este campo
                value = parsed_value

            fields_to_set.append(f"{field} = ?")
            params.append(clean_string_input(str(value)) if isinstance(value, str) else value) # Limpiar strings
        else:
            print(f"Advertencia: Campo '{field}' no permitido para actualización o no existe.")

    if not fields_to_set:
        print("No hay campos válidos para actualizar.")
        return True # O False si se considera un error

    params.append(gym_id) # Para la cláusula WHERE

    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()

    try:
        sql_query = f"UPDATE members SET {', '.join(fields_to_set)} WHERE gym_id = ?"
        cursor.execute(sql_query, tuple(params))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Detalles del miembro '{gym_id}' actualizados.")
            return True
        else:
            # Podría ser que los valores ya fueran los mismos
            print(f"No se realizaron cambios en el miembro '{gym_id}' (posiblemente los datos ya eran iguales).")
            return True # Consideramos que no es un error
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: members.email" in str(e):
            print(f"Error: El email '{updates.get('email')}' ya está registrado para otro miembro.")
        else:
             print(f"Error de base de datos al actualizar miembro: {e}")
        return False
    except Exception as e:
        print(f"Error inesperado al actualizar miembro: {e}")
        return False
    finally:
        conn.close()

def renew_member_membership(gym_id: str, new_membership_type_key: str, renewal_date_str: str = None) -> bool:
    """
    Renueva la membresía de un miembro.
    Actualiza tipo, fecha de inicio y expiración. Actualiza estado a activo.
    """
    member = get_member_by_gym_id(gym_id)
    if not member:
        print(f"Error: Miembro con GYM_ID '{gym_id}' no encontrado para renovar.")
        return False

    if new_membership_type_key not in DEFAULT_MEMBERSHIP_TYPES:
        print(f"Error: Nuevo tipo de membresía '{new_membership_type_key}' no válido.")
        return False
    
    new_membership_info = DEFAULT_MEMBERSHIP_TYPES[new_membership_type_key]
    
    parsed_renewal_date = parse_date_string(renewal_date_str) if renewal_date_str else date.today()
    if not parsed_renewal_date:
        print("Error: Formato de fecha de renovación inválido. Use YYYY-MM-DD o deje en blanco para hoy.")
        return False

    new_start_date = parsed_renewal_date
    new_expiry_date = None
    if new_membership_info.get('duration_days') and new_membership_info['duration_days'] > 0:
        new_expiry_date = calculate_expiry_date(new_start_date, new_membership_info['duration_days'])

    updates_for_db = {
        "membership_type": new_membership_info['display_name'],
        "membership_start_date": new_start_date,
        "membership_expiry_date": new_expiry_date,
        "status": "active" # Asumimos que al renovar se activa
    }

    # Llama a la función de actualización general
    success = update_member_details(gym_id, updates_for_db)
    if success:
        print(f"Membresía para '{gym_id}' renovada a '{new_membership_info['display_name']}'.")
        print(f"Nueva fecha de expiración: {format_date(new_expiry_date) if new_expiry_date else 'N/A'}")
        # Aquí también se registraría el pago correspondiente en finances.py
    return success

def delete_member(gym_id: str) -> bool:
    """
    Elimina un miembro de la base de datos.
    Esto también eliminará registros de asistencia asociados debido a ON DELETE CASCADE.
    """
    member = get_member_by_gym_id(gym_id)
    if not member:
        print(f"Error: Miembro con GYM_ID '{gym_id}' no encontrado para eliminar.")
        return False

    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM members WHERE gym_id = ?", (gym_id,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Miembro '{gym_id}' ({member['full_name']}) eliminado permanentemente.")
            # Considerar qué pasa con sus transacciones financieras (están ON DELETE SET NULL member_id)
            return True
        else:
            # No debería pasar si member fue encontrado antes
            print(f"No se pudo eliminar al miembro '{gym_id}'.")
            return False
    except Exception as e:
        print(f"Error al eliminar miembro: {e}")
        return False
    finally:
        conn.close()

# --- Funciones de Asistencia ---
def record_attendance(gym_id: str, activity_id: int = None) -> bool:
    """
    Registra una entrada (check-in) para un miembro.
    """
    member = get_member_by_gym_id(gym_id)
    if not member:
        print(f"Error: Miembro con GYM_ID '{gym_id}' no encontrado para registrar asistencia.")
        return False

    # Opcional: Verificar si la membresía está activa y vigente
    if member['status'] != 'active':
        print(f"Advertencia: El miembro '{gym_id}' ({member['full_name']}) no tiene estado 'activo' (Estado actual: {member['status']}).")
        # Podrías retornar False aquí o permitir el registro con advertencia.
    
    current_date = date.today()
    if member['membership_expiry_date'] and parse_date_string(member['membership_expiry_date']) < current_date : # Convertir de string a date si es necesario
        print(f"Advertencia: La membresía del miembro '{gym_id}' ({member['full_name']}) ha expirado el {format_date(parse_date_string(member['membership_expiry_date']))}.")
        # Podrías retornar False aquí.

    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        # member['id'] es el db_id
        cursor.execute(
            "INSERT INTO attendance (member_id, activity_id) VALUES (?, ?)",
            (member['id'], activity_id)
        )
        conn.commit()
        print(f"Asistencia registrada para: {member['full_name']} (ID: {gym_id}) a las {format_date(datetime.now(), '%d/%m/%Y %H:%M:%S')}.")
        return True
    except Exception as e:
        print(f"Error al registrar asistencia para '{gym_id}': {e}")
        return False
    finally:
        conn.close()

def get_member_attendance_history(gym_id: str, limit: int = 20) -> list[dict]:
    """Obtiene el historial de asistencia de un miembro."""
    member = get_member_by_gym_id(gym_id)
    if not member:
        print(f"Error: Miembro '{gym_id}' no encontrado.")
        return []

    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor()
    try:
        # Podríamos unir con la tabla activities si activity_id está presente
        cursor.execute(
            """SELECT a.id, a.check_in_time, a.check_out_time, act.name as activity_name
               FROM attendance a
               LEFT JOIN activities act ON a.activity_id = act.id
               WHERE a.member_id = ?
               ORDER BY a.check_in_time DESC
               LIMIT ?""",
            (member['id'], limit)
        )
        history = [dict(row) for row in cursor.fetchall()]
        return history
    finally:
        conn.close()

# --- Simulación de Carné ---
def generate_member_card_info(gym_id: str) -> str:
    """
    Genera una cadena de texto con la información para un carné simulado.
    En una aplicación real, esto podría generar un PDF, una imagen, o datos para una app móvil.
    """
    member = get_member_by_gym_id(gym_id)
    if not member:
        return "Miembro no encontrado."

    card_lines = [
        "--- CARNÉ DEL GIMNASIO ---",
        f" Gimnasio: {member.get('gym_name_from_settings', 'Gimnasio Evolución Fitness')}", # Suponiendo que se podría obtener de config
        " ****************************",
        f" Nombre: {member.get('full_name', 'N/A')}",
        f" ID Socio: {member.get('gym_id', 'N/A')}",
        f" Tipo Memb.: {member.get('membership_type', 'N/A')}",
        f" Válido hasta: {format_date(parse_date_string(member.get('membership_expiry_date')) if member.get('membership_expiry_date') else None)}",
        " ****************************",
        "        Presentar al entrar",
        "--- Gracias por ser miembro ---"
    ]
    return "\n".join(card_lines)


if __name__ == "__main__":
    print("--- Probando el módulo members.py ---")
    # Asumir que database.py ya se ejecutó y las tablas existen.

    # --- Añadir Miembros de Prueba ---
    print("\n[TEST] Añadiendo miembros...")
    miembro1_data = {
        "full_name": "Ana Pérez García", "membership_type_key": "monthly",
        "join_date_str": "2023-01-10", "date_of_birth_str": "1990-05-15",
        "email": "ana.perez@example.com", "phone": "600111222",
        "address": "Calle Falsa 123, Ciudad"
    }
    miembro1 = add_member(**miembro1_data)
    if miembro1: print(f"Creado miembro1 GYM_ID: {miembro1['gym_id']}")

    miembro2 = add_member("Luis Rodríguez Sol", "annual", email="luis.ro@example.net", phone="600333444")
    if miembro2: print(f"Creado miembro2 GYM_ID: {miembro2['gym_id']}")

    miembro3_data = {
        "full_name": "Carlos López Ruiz", "membership_type_key": "10_session_pass",
        "email": "carlos.lopez@example.com"
    }
    miembro3 = add_member(**miembro3_data)
    if miembro3: print(f"Creado miembro3 GYM_ID: {miembro3['gym_id']}")


    # --- Ver todos los miembros ---
    print("\n[TEST] Todos los miembros:")
    all_m = get_all_members()
    if all_m:
        for m in all_m:
            print(f"  - {m['gym_id']}: {m['full_name']} ({m['membership_type']}), Expira: {format_date(parse_date_string(m['membership_expiry_date'])) if m['membership_expiry_date'] else 'N/A'}")
    else:
        print("  No hay miembros o error al obtenerlos.")

    # --- Obtener y mostrar ficha de un miembro y su carné ---
    if miembro1:
        print(f"\n[TEST] Ficha de miembro {miembro1['gym_id']}:")
        ficha_m1 = get_member_by_gym_id(miembro1['gym_id'])
        if ficha_m1:
            for key, val in ficha_m1.items():
                # Formatear fechas para mejor visualización si son objetos date/datetime
                if isinstance(val, (date, datetime)): val = format_date(val)
                print(f"  {key.replace('_', ' ').capitalize()}: {val}")
            print("\n[TEST] Carné simulado:")
            print(generate_member_card_info(miembro1['gym_id']))
        else:
            print(f"  No se encontró a {miembro1['gym_id']}")

    # --- Actualizar detalles ---
    if miembro2:
        print(f"\n[TEST] Actualizando teléfono de {miembro2['gym_id']}...")
        update_member_details(miembro2['gym_id'], {"phone": "600555666", "notes": "Prefiere entrenar por la mañana."})
        m2_updated = get_member_by_gym_id(miembro2['gym_id'])
        if m2_updated: print(f"  Nuevo teléfono: {m2_updated.get('phone')}, Notas: {m2_updated.get('notes')}")

    # --- Renovar membresía ---
    if miembro1:
        print(f"\n[TEST] Renovando membresía de {miembro1['gym_id']} a trimestral...")
        # Asumamos que hoy es 2023-02-10 para que la renovación tenga sentido con la expiración original
        # En una prueba real, se podría mockear date.today()
        renew_member_membership(miembro1['gym_id'], "quarterly", renewal_date_str="2023-02-08") # Un poco antes de expirar

    # --- Registrar Asistencia ---
    if miembro1:
        print(f"\n[TEST] Registrando asistencia para {miembro1['gym_id']}...")
        record_attendance(miembro1['gym_id'])
        record_attendance(miembro1['gym_id']) # Segunda asistencia
    if miembro2:
        record_attendance(miembro2['gym_id'])


    # --- Historial de Asistencia ---
    if miembro1:
        print(f"\n[TEST] Historial de asistencia para {miembro1['gym_id']}:")
        history = get_member_attendance_history(miembro1['gym_id'])
        if history:
            for entry in history:
                print(f"  - Check-in: {format_date(parse_datetime_string(entry['check_in_time']), DATETIME_FORMAT_DISPLAY)} {('Actividad: '+entry['activity_name']) if entry['activity_name'] else ''}")
        else:
            print("  Sin registros de asistencia.")
            
    # --- Eliminar un miembro (con cuidado) ---
    # if miembro3:
    #     print(f"\n[TEST] Eliminando a {miembro3['gym_id']}...")
    #     delete_member(miembro3['gym_id'])
    #     if not get_member_by_gym_id(miembro3['gym_id']):
    #         print(f"  {miembro3['gym_id']} eliminado correctamente.")
    #     else:
    #         print(f"  Error al eliminar {miembro3['gym_id']}.")

    print("\n--- Fin de pruebas de members.py ---")