# gimnasio_mgmt_gui/core_logic/members.py
# Lógica de negocio para la gestión de miembros (socios) del gimnasio.

import sqlite3
from datetime import date, datetime # datetime no se usa directamente aquí pero es bueno tenerlo si se parsean datetimes
from decimal import Decimal # Para manejar precios con precisión
import os # <-- Añadido para usar os.path.basename en el if __name__

# Importaciones del mismo paquete (core_logic) o de la raíz del proyecto
try:
    from .database import get_db_connection
    from .utils import (
        generate_internal_id, sanitize_text_input, parse_string_to_date,
        calculate_member_expiry_date, format_date_for_ui, convert_date_to_db_string,
        parse_string_to_decimal # <-- CORRECCIÓN 1: Importar parse_string_to_decimal
    )
    from config import (
        DEFAULT_NEW_MEMBER_STATUS_ON_CREATION, MEMBER_STATUS_OPTIONS_LIST,
        DEFAULT_MEMBERSHIP_PLANS, MEMBER_PHOTOS_SUBDIR_NAME, APP_DATA_ROOT_DIR,
        UI_DISPLAY_DATE_FORMAT # <-- CORRECCIÓN 2: Importar UI_DISPLAY_DATE_FORMAT
    )
except ImportError as e:
    print(f"ERROR CRÍTICO (members.py): Fallo en importaciones esenciales. Error: {e}")
    raise

# --- FUNCIONES CRUD PARA MIEMBROS ---
def add_new_member(
    full_name: str,
    date_of_birth_str: str | None = None,
    gender: str | None = None,
    phone_number: str | None = None,
    address_line1: str | None = None,
    address_city: str | None = None,
    address_postal_code: str | None = None,
    join_date_str: str | None = None, 
    initial_status: str = DEFAULT_NEW_MEMBER_STATUS_ON_CREATION,
    notes: str | None = None,
    photo_filename: str | None = None
) -> tuple[bool, str]:
    # (Código de add_new_member sin cambios funcionales, pero ahora parse_string_to_date
    #  debería funcionar si se usa correctamente para date_of_birth_str y join_date_str)
    clean_full_name = sanitize_text_input(full_name)
    if not clean_full_name:
        return False, "El nombre completo del miembro es obligatorio."

    dob = parse_string_to_date(date_of_birth_str, permissive_formats=True) if date_of_birth_str else None
    
    actual_join_date = parse_string_to_date(join_date_str, permissive_formats=True) if join_date_str else date.today()
    if not actual_join_date:
        return False, "Formato de fecha de inscripción no válido."

    if initial_status not in MEMBER_STATUS_OPTIONS_LIST:
        return False, f"Estado inicial '{initial_status}' no es válido."

    internal_member_id = generate_internal_id(prefix="MBR")

    conn = get_db_connection()
    if not conn:
        return False, "Error de conexión a la base de datos."

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO members (
                    internal_member_id, full_name, date_of_birth, gender, phone_number,
                    address_line1, address_city, address_postal_code, join_date,
                    current_status, notes, photo_filename, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                internal_member_id, clean_full_name,
                convert_date_to_db_string(dob),
                sanitize_text_input(gender, allow_empty=True),
                sanitize_text_input(phone_number, allow_empty=True),
                sanitize_text_input(address_line1, allow_empty=True),
                sanitize_text_input(address_city, allow_empty=True),
                sanitize_text_input(address_postal_code, allow_empty=True),
                convert_date_to_db_string(actual_join_date),
                initial_status,
                sanitize_text_input(notes, allow_empty=True),
                sanitize_text_input(photo_filename, allow_empty=True)
            ))
            return True, internal_member_id
    except sqlite3.IntegrityError:
        return False, f"Conflicto de ID interno. Intente de nuevo."
    except sqlite3.Error as e:
        print(f"ERROR (members.py - add_new_member): {e}")
        return False, "Error de base de datos al añadir miembro."
    finally:
        if conn: conn.close()


def get_member_by_internal_id(member_internal_id: str) -> dict | None:
    # (Código sin cambios, pero asegurarse que la conexión se cierra)
    if not member_internal_id: return None
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM members WHERE internal_member_id = ?",
            (member_internal_id,)
        )
        member_data = cursor.fetchone()
        if member_data:
            member_dict = dict(member_data)
            # Convertir fechas almacenadas a objetos date para la lógica
            member_dict['date_of_birth_obj'] = parse_string_to_date(member_dict.get('date_of_birth'))
            member_dict['join_date_obj'] = parse_string_to_date(member_dict.get('join_date'))
            return member_dict
        return None
    except sqlite3.Error as e:
        print(f"ERROR (members.py - get_member_by_internal_id): {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_members_summary(active_only: bool = False, search_term: str | None = None) -> list[dict]:
    # (Código sin cambios, pero asegurarse que la conexión se cierra)
    conn = get_db_connection()
    if not conn: return []
    
    members_list = []
    query = "SELECT id, internal_member_id, full_name, current_status, join_date FROM members"
    conditions = []
    params = []

    if active_only:
        conditions.append("current_status = ?")
        params.append("Activo")

    if search_term:
        clean_search = f"%{sanitize_text_input(search_term)}%"
        # Asegurarse que la tabla no necesita alias si no hay JOINS directos en ESTA query base
        conditions.append("(full_name LIKE ? OR internal_member_id LIKE ?)")
        params.extend([clean_search, clean_search])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY full_name"

    try:
        cursor = conn.cursor()
        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            member_dict = dict(row)
            join_date_obj = parse_string_to_date(row['join_date'])
            member_dict['join_date_ui'] = format_date_for_ui(join_date_obj) # Usar función de utils
            member_dict['join_date_obj'] = join_date_obj
            members_list.append(member_dict)
        return members_list
    except sqlite3.Error as e:
        print(f"ERROR (members.py - get_all_members_summary): {e}")
        return []
    finally:
        if conn: conn.close()

def update_member_details(
    member_internal_id: str,
    full_name: str | None = None,
    date_of_birth_str: str | None = None,
    gender: str | None = None,
    phone_number: str | None = None,
    address_line1: str | None = None,
    address_city: str | None = None,
    address_postal_code: str | None = None,
    current_status: str | None = None, 
    notes: str | None = None,
    photo_filename: str | None = None
) -> tuple[bool, str]:
    # (Código sin cambios funcionales, pero revisar manejo de conexión y conversiones)
    if not member_internal_id:
        return False, "ID de miembro no proporcionado."

    current_member_data = get_member_by_internal_id(member_internal_id) # Esta función ya cierra su propia conexión
    if not current_member_data:
        return False, f"Miembro con ID '{member_internal_id}' no encontrado."

    updates = []
    params = []

    # Validar y añadir solo campos que realmente cambian
    if full_name is not None:
        clean_name = sanitize_text_input(full_name)
        if not clean_name: return False, "El nombre completo no puede estar vacío."
        if clean_name != current_member_data.get('full_name'):
            updates.append("full_name = ?")
            params.append(clean_name)

    if date_of_birth_str is not None: # Se pasa un string (de UI o test)
        dob_obj = parse_string_to_date(date_of_birth_str, permissive_formats=True) # convierte a objeto date
        current_dob_obj = current_member_data.get('date_of_birth_obj') # objeto date o None
        if dob_obj != current_dob_obj: # Comparar objetos date
            updates.append("date_of_birth = ?")
            params.append(convert_date_to_db_string(dob_obj)) # guardar string en formato BD
            
    # ... (Añadir lógica para gender, phone_number, address_*, photo_filename) ...
    # Ejemplo para status:
    if current_status is not None and current_status != current_member_data.get('current_status'):
        if current_status not in MEMBER_STATUS_OPTIONS_LIST:
            return False, f"Estado '{current_status}' no válido."
        updates.append("current_status = ?")
        params.append(current_status)
    
    # Ejemplo para notes:
    if notes is not None : # Permitir poner notes a vacío
        clean_notes = sanitize_text_input(notes, allow_empty=True)
        if clean_notes != (current_member_data.get('notes') or ""):
            updates.append("notes = ?")
            params.append(clean_notes)
            
    # Ejemplo para photo_filename:
    if photo_filename is not None: # Si se pasa, se asume que se quiere cambiar (incluso a None)
        clean_photo_fn = sanitize_text_input(photo_filename, allow_empty=True)
        # Para poner a None, se pasa una cadena vacía que se convierte en NULL en la BD si el campo lo permite.
        # O pasar un valor especial tipo "DELETE_PHOTO" para manejarlo explícitamente.
        # Si photo_filename es para un NUEVO archivo, solo actualizar si es diferente al existente.
        if clean_photo_fn != (current_member_data.get('photo_filename') or ""):
            updates.append("photo_filename = ?")
            params.append(clean_photo_fn if clean_photo_fn else None) # None se traduce a NULL

    if not updates:
        return True, "No se realizaron cambios en los detalles del miembro."

    updates.append("updated_at = CURRENT_TIMESTAMP")

    conn = get_db_connection() # Nueva conexión para la operación de UPDATE
    if not conn: return False, "Error de conexión a BD."

    try:
        with conn:
            cursor = conn.cursor()
            query = f"UPDATE members SET {', '.join(updates)} WHERE internal_member_id = ?"
            final_params = tuple(params + [member_internal_id])
            cursor.execute(query, final_params)
            if cursor.rowcount == 0:
                return False, "No se actualizó ninguna fila (ID o sin cambios)."
            return True, "Detalles del miembro actualizados."
    except sqlite3.Error as e:
        print(f"ERROR (members.py - update_member_details): {e}")
        return False, "Error de BD al actualizar miembro."
    finally:
        if conn: conn.close()


# --- FUNCIONES DE GESTIÓN DE MEMBRESÍAS DEL MIEMBRO ---
def add_membership_to_member(
    member_internal_id: str,
    plan_key: str,
    purchase_date_str: str | None = None,
    custom_price_paid_str: str | None = None,
    payment_transaction_id: int | None = None, # Ahora int directamente (ID de la tabla financial_transactions)
    notes: str | None = None
) -> tuple[bool, str]:
    # (Revisar la obtención de member_db_id y el manejo de decimales)
    member_data = get_member_by_internal_id(member_internal_id) # Esta función cierra su conexión
    if not member_data:
        return False, f"Miembro con ID '{member_internal_id}' no encontrado."
    
    member_db_id = member_data['id']

    if plan_key not in DEFAULT_MEMBERSHIP_PLANS:
        return False, f"Plan de membresía con clave '{plan_key}' no reconocido."
    
    plan_info = DEFAULT_MEMBERSHIP_PLANS[plan_key]
    plan_name_at_purchase = plan_info['nombre_visible_ui']
    duration_days = plan_info['duracion_total_dias']
    sessions_total = plan_info.get('numero_sesiones_incluidas')
    sessions_remaining = sessions_total

    start_date_obj = parse_string_to_date(purchase_date_str, permissive_formats=True) if purchase_date_str else date.today()
    if not start_date_obj:
        return False, "Formato de fecha de inicio/compra no válido."
    
    expiry_date_obj = calculate_member_expiry_date(start_date_obj, duration_days)

    if custom_price_paid_str:
        price_paid_decimal = parse_string_to_decimal(custom_price_paid_str) # Usar la función de utils
        if price_paid_decimal is None or price_paid_decimal < Decimal('0'):
            return False, "Precio pagado personalizado no válido."
    else:
        price_paid_decimal = Decimal(str(plan_info['precio_base_decimal']))

    conn = get_db_connection() # Nueva conexión
    if not conn: return False, "Error de conexión a BD."

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE member_memberships SET is_current = 0 WHERE member_id = ?", (member_db_id,))

            cursor.execute("""
                INSERT INTO member_memberships (
                    member_id, plan_key, plan_name_at_purchase, price_paid, start_date, expiry_date,
                    sessions_total, sessions_remaining, payment_transaction_id, is_current, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, CURRENT_TIMESTAMP)
            """, (
                member_db_id, plan_key, plan_name_at_purchase, str(price_paid_decimal), 
                convert_date_to_db_string(start_date_obj),
                convert_date_to_db_string(expiry_date_obj),
                sessions_total, sessions_remaining,
                payment_transaction_id, # Ya es int o None
                sanitize_text_input(notes, allow_empty=True)
            ))
            new_membership_id = cursor.lastrowid
            
            # Actualizar estado general del miembro si es necesario (y la nueva membresía es válida hoy)
            if expiry_date_obj >= date.today() and start_date_obj <= date.today():
                if member_data['current_status'] != "Activo": # Solo actualizar si no está ya activo
                    # Llamar a update_member_details para esto asegura que updated_at se actualice
                    # y se usen las validaciones correctas
                    update_success, _ = update_member_details(member_internal_id, current_status="Activo")
                    if not update_success:
                        print(f"ADVERTENCIA (members.py): No se pudo actualizar el estado general del miembro {member_internal_id} a Activo.")

            return True, str(new_membership_id)
    except sqlite3.Error as e:
        print(f"ERROR (members.py - add_membership_to_member): {e}")
        return False, "Error de BD al añadir membresía."
    finally:
        if conn: conn.close()


def get_member_active_membership(member_internal_id: str) -> dict | None:
    # (Código sin cambios funcionales, pero asegurarse que la conexión se cierra)
    member_data = get_member_by_internal_id(member_internal_id)
    if not member_data: return None
    member_db_id = member_data['id']

    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor()
        # Prioridad a la marcada como is_current = 1 y vigente
        cursor.execute("""
            SELECT * FROM member_memberships
            WHERE member_id = ? AND is_current = 1 AND expiry_date >= date('now', '-1 day') -- Permite que hoy sea el ultimo dia
            ORDER BY start_date DESC LIMIT 1 
        """, (member_db_id,)) # Ajustar 'now' si se quiere precisión de tiempo
        active_mem = cursor.fetchone()
        
        if not active_mem: # Fallback: si ninguna está marcada como is_current, buscar la más reciente vigente
            cursor.execute("""
                SELECT * FROM member_memberships
                WHERE member_id = ? AND expiry_date >= date('now', '-1 day') 
                ORDER BY start_date DESC LIMIT 1 
            """, (member_db_id,))
            active_mem = cursor.fetchone()

        if active_mem:
            mem_dict = dict(active_mem)
            # Convertir a objetos date para la lógica
            mem_dict['start_date_obj'] = parse_string_to_date(mem_dict['start_date'])
            mem_dict['expiry_date_obj'] = parse_string_to_date(mem_dict['expiry_date'])
            mem_dict['price_paid_decimal'] = Decimal(str(mem_dict['price_paid']))
            return mem_dict
        return None
    except sqlite3.Error as e:
        print(f"ERROR (members.py - get_member_active_membership): {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_memberships_for_member(member_internal_id: str) -> list[dict]:
    # (Código sin cambios funcionales, pero asegurarse que la conexión se cierra)
    member_data = get_member_by_internal_id(member_internal_id)
    if not member_data: return []
    member_db_id = member_data['id']

    conn = get_db_connection()
    if not conn: return []
    memberships_list = []
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM member_memberships WHERE member_id = ? ORDER BY start_date DESC, id DESC",
            (member_db_id,)
        )
        for row in cursor.fetchall():
            mem_dict = dict(row)
            mem_dict['start_date_obj'] = parse_string_to_date(mem_dict['start_date'])
            mem_dict['expiry_date_obj'] = parse_string_to_date(mem_dict['expiry_date'])
            mem_dict['price_paid_decimal'] = Decimal(str(mem_dict['price_paid']))
            memberships_list.append(mem_dict)
        return memberships_list
    except sqlite3.Error as e:
        print(f"ERROR (members.py - get_all_memberships_for_member): {e}")
        return []
    finally:
        if conn: conn.close()

# --- Script de autocomprobación ---
if __name__ == "__main__":
    # --- CORRECCIÓN: Usar __name__ ---
    print(f"--- {__name__} (Módulo members.py) Self-Check ---")

    print("\n1. Añadiendo miembro 'Laura Gómez'...")
    # --- CORRECCIÓN: Usar la constante UI_DISPLAY_DATE_FORMAT importada ---
    success_add, msg_add = add_new_member(
        full_name="  Laura Gómez ",
        date_of_birth_str="20/08/1995", # formato UI
        join_date_str=date.today().strftime(UI_DISPLAY_DATE_FORMAT) # Hoy en formato UI
    )
    member_laura_id = None
    if success_add:
        member_laura_id = msg_add
        print(f"  Miembro 'Laura Gómez' añadido ID: {member_laura_id}")
    else:
        print(f"  Fallo al añadir 'Laura Gómez': {msg_add}")

    if member_laura_id:
        print(f"\n2. Obteniendo detalles de '{member_laura_id}'...")
        laura_details = get_member_by_internal_id(member_laura_id)
        if laura_details:
            join_date_disp = format_date_for_ui(laura_details.get('join_date_obj'))
            print(f"  Nombre: {laura_details['full_name']}, Estado: {laura_details['current_status']}, Ingreso: {join_date_disp}")

        print(f"\n3. Añadiendo membresía 'Plan Anual VIP' a '{member_laura_id}'...")
        # Suponemos que "anual_vip" es una clave válida en DEFAULT_MEMBERSHIP_PLANS
        if "anual_vip" in DEFAULT_MEMBERSHIP_PLANS:
            success_mem, msg_mem = add_membership_to_member(
                member_internal_id=member_laura_id,
                plan_key="anual_vip",
                # custom_price_paid_str="300.00" # Probar con precio personalizado
            )
            if success_mem:
                print(f"  Membresía añadida a '{member_laura_id}'. ID Memb. BD: {msg_mem}")
                laura_after_mem = get_member_by_internal_id(member_laura_id)
                if laura_after_mem: print(f"    Estado de Laura después de membresía: {laura_after_mem['current_status']}")

                active_mem = get_member_active_membership(member_laura_id)
                if active_mem:
                    print(f"    Membresía activa: {active_mem['plan_name_at_purchase']}, Expira: {format_date_for_ui(active_mem['expiry_date_obj'])}")

            else:
                print(f"  Fallo al añadir membresía a '{member_laura_id}': {msg_mem}")
        else:
            print("  ADVERTENCIA: Clave de plan 'anual_vip' no encontrada en config para la prueba.")
            
    # ... (más pruebas)
    print(f"\n--- Fin de pruebas de {__name__} (members.py) ---")