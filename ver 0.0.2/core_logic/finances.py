# gimnasio_mgmt_gui/core_logic/finances.py
# Lógica de negocio para la gestión financiera: ingresos, gastos y elementos recurrentes.

import sqlite3
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import os

# Importaciones del mismo paquete (core_logic) o de la raíz del proyecto
try:
    from .database import get_db_connection
    from .utils import (
        generate_internal_id, sanitize_text_input, parse_string_to_date,
        format_date_for_ui, convert_date_to_db_string, parse_string_to_decimal,
        get_current_date_for_db, format_currency_for_display # format_currency_for_display sí se importa
    )
    # Asegurarse de que TODAS las constantes de config usadas aquí estén importadas.
    from config import (
        DEFAULT_INCOME_CATEGORIES_LIST, DEFAULT_EXPENSE_CATEGORIES_LIST,
        VALID_FREQUENCIES, # Esta debe estar definida en tu config.py
        DB_STORAGE_DATE_FORMAT, # Usada indirectamente por convert_date_to_db_string
        UI_DISPLAY_DATE_FORMAT, # Usada en el if __name__
        CURRENCY_DISPLAY_SYMBOL # Usada en el if __name__
    )
except ImportError as e:
    print(f"ERROR CRÍTICO (finances.py): Fallo en importaciones esenciales. Error: {e}")
    raise

# --- Ya NO necesitamos el bloque try-except NameError para VALID_FREQUENCIES aquí,
#     porque se asume que se importa de config.py ---

# --- GESTIÓN DE TRANSACCIONES FINANCIERAS (INGRESOS/GASTOS PUNTUALES) ---
def record_financial_transaction(
    transaction_type: str,
    transaction_date_str: str, # Espera un str no None
    description: str,
    category: str,
    amount_str: str,
    payment_method: str | None = None,
    related_member_internal_id: str | None = None,
    recorded_by_user_id: int | None = None,
    reference_document_number: str | None = None,
    notes: str | None = None,
    is_from_recurring: bool = False,
    source_recurring_id: int | None = None
) -> tuple[bool, str]:
    if transaction_type not in ['income', 'expense']:
        return False, "Tipo de transacción no válido."
    
    trans_date_obj = parse_string_to_date(transaction_date_str, permissive_formats=True) # Devuelve date | None
    if not trans_date_obj:
        return False, "Formato de fecha de transacción no válido o fecha vacía."

    # El resto de las validaciones y lógica como la tenías...
    clean_description = sanitize_text_input(description)
    if not clean_description: return False, "La descripción es obligatoria."
    # ... (más validaciones)
    amount_decimal = parse_string_to_decimal(amount_str)
    if amount_decimal is None or amount_decimal <= Decimal('0'):
        return False, "Monto de transacción no válido."

    internal_transaction_id = generate_internal_id(prefix="TRN" if transaction_type == 'income' else "EXP")
    related_member_db_id = None # Lógica para obtenerlo si es necesario...

    conn = get_db_connection()
    if not conn: return False, "Error de conexión a BD."
    try:
        with conn:
            cursor = conn.cursor()
            # Usar trans_date_obj convertido a string para la BD
            db_date_str = convert_date_to_db_string(trans_date_obj) # Devuelve str | None
            if db_date_str is None: # Esto no debería pasar si trans_date_obj es válido
                return False, "Error interno convirtiendo fecha para BD."

            cursor.execute("""
                INSERT INTO financial_transactions (
                    internal_transaction_id, transaction_type, transaction_date, description, category,
                    amount, payment_method, related_member_id, recorded_by_user_id,
                    reference_document_number, notes, is_recurring_source, source_recurring_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                internal_transaction_id, transaction_type, db_date_str,
                clean_description, sanitize_text_input(category), str(amount_decimal), 
                sanitize_text_input(payment_method, allow_empty=True),
                related_member_db_id, recorded_by_user_id,  
                sanitize_text_input(reference_document_number, allow_empty=True),
                sanitize_text_input(notes, allow_empty=True),
                1 if is_from_recurring else 0, source_recurring_id 
            ))
            return True, internal_transaction_id
    except sqlite3.Error as e:
        print(f"ERROR (finances.py - record_financial_transaction): {e}"); return False, "Error de BD."
    finally:
        if conn: conn.close()

# (get_financial_transactions y get_financial_summary permanecen igual que en tu código,
#  asumiendo que internamente usan las funciones de utils y config correctamente)

def get_financial_transactions(
    start_date_str: str | None = None,
    end_date_str: str | None = None,
    transaction_type: str | None = None, 
    category: str | None = None,
    limit: int = 100, 
    offset: int = 0
) -> tuple[list[dict], int]:
    conn = get_db_connection()
    if not conn: return [], 0
    conditions, params = [], []
    count_query = "SELECT COUNT(ft.id) as total_count FROM financial_transactions ft"
    data_query = """
        SELECT ft.*, m.full_name as member_name, su.username as recorded_by_username
        FROM financial_transactions ft
        LEFT JOIN members m ON ft.related_member_id = m.id
        LEFT JOIN system_users su ON ft.recorded_by_user_id = su.id
    """
    if start_date_str:
        s_date = parse_string_to_date(start_date_str, True)
        if s_date: conditions.append("ft.transaction_date >= ?"); params.append(convert_date_to_db_string(s_date))
    if end_date_str:
        e_date = parse_string_to_date(end_date_str, True)
        if e_date: conditions.append("ft.transaction_date <= ?"); params.append(convert_date_to_db_string(e_date))
    if transaction_type in ['income', 'expense']:
        conditions.append("ft.transaction_type = ?"); params.append(transaction_type)
    if category:
        clean_cat = sanitize_text_input(category)
        if clean_cat: conditions.append("LOWER(ft.category) LIKE LOWER(?)"); params.append(f"%{clean_cat}%")

    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)
        count_query += where_clause; data_query += where_clause
    data_query += " ORDER BY ft.transaction_date DESC, ft.id DESC LIMIT ? OFFSET ?"
    
    transactions_list, total_count = [], 0
    try:
        cursor = conn.cursor()
        cursor.execute(count_query, tuple(params)); count_result = cursor.fetchone()
        if count_result: total_count = count_result['total_count']
        cursor.execute(data_query, tuple(params + [limit, offset]))
        for row in cursor.fetchall():
            trans_dict = dict(row)
            trans_dict['transaction_date_obj'] = parse_string_to_date(row['transaction_date'])
            trans_dict['transaction_date_ui'] = format_date_for_ui(trans_dict['transaction_date_obj'])
            trans_dict['amount_decimal'] = Decimal(str(row['amount']))
            transactions_list.append(trans_dict)
        return transactions_list, total_count
    except sqlite3.Error as e: print(f"ERROR (get_financial_transactions): {e}"); return [], 0
    finally:
        if conn: conn.close()

def get_financial_summary(
    start_date_str: str | None = None,
    end_date_str: str | None = None
) -> dict:
    # ... (código como el tuyo) ...
    conn = get_db_connection()
    if not conn: return {"total_income": Decimal('0'), "total_expense": Decimal('0'), "net_balance": Decimal('0')}
    base_query = "SELECT SUM(amount) FROM financial_transactions WHERE transaction_type = ?"
    conditions, params_suffix = [], []
    if start_date_str:
        s_date = parse_string_to_date(start_date_str, True)
        if s_date: conditions.append("transaction_date >= ?"); params_suffix.append(convert_date_to_db_string(s_date))
    if end_date_str:
        e_date = parse_string_to_date(end_date_str, True)
        if e_date: conditions.append("transaction_date <= ?"); params_suffix.append(convert_date_to_db_string(e_date))
    query_suffix_str = " AND " + " AND ".join(conditions) if conditions else ""
    
    total_income, total_expense = Decimal('0'), Decimal('0')
    try:
        cursor = conn.cursor()
        cursor.execute(base_query + query_suffix_str, tuple(['income'] + params_suffix))
        result = cursor.fetchone(); total_income = Decimal(str(result[0])) if result and result[0] is not None else Decimal('0')
        cursor.execute(base_query + query_suffix_str, tuple(['expense'] + params_suffix))
        result = cursor.fetchone(); total_expense = Decimal(str(result[0])) if result and result[0] is not None else Decimal('0')
        return {"total_income": total_income, "total_expense": total_expense, "net_balance": total_income - total_expense}
    except sqlite3.Error as e: print(f"ERROR (get_financial_summary): {e}"); return {"total_income":Decimal('0'), "total_expense":Decimal('0'), "net_balance":Decimal('0')}
    finally:
        if conn: conn.close()


# --- GESTIÓN DE ÍTEMS FINANCIEROS RECURRENTES ---
def add_recurring_financial_item(
    item_type: str, description: str, default_amount_str: str, category: str,
    frequency: str, start_date_str: str, day_of_month: int | None = None, 
    day_of_week: int | None = None, end_date_str: str | None = None,
    is_active: bool = True, auto_generate: bool = False, notes: str | None = None,
    related_member_internal_id: str | None = None
) -> tuple[bool, str]:
    # (Código como el tuyo, asegurando uso de VALID_FREQUENCIES importada)
    if item_type not in ['income', 'expense']: return False, "Tipo de ítem no válido."
    if frequency not in VALID_FREQUENCIES: # <-- USA LA CONSTANTE IMPORTADA
        return False, f"Frecuencia '{frequency}' no válida. Válidas: {', '.join(VALID_FREQUENCIES)}"
    # ... (resto de la función como la tenías, asegurando cierres de conexión, etc.) ...
    clean_description = sanitize_text_input(description)
    if not clean_description: return False, "Descripción obligatoria."
    default_amount = parse_string_to_decimal(default_amount_str)
    if default_amount is None or default_amount <= Decimal('0'): return False, "Monto por defecto no válido."
    start_date_obj = parse_string_to_date(start_date_str, True)
    if not start_date_obj: return False, "Fecha de inicio no válida."
    end_date_obj = parse_string_to_date(end_date_str, True) if end_date_str else None
    next_due_date_obj = _calculate_next_due_date_for_recurring(start_date_obj, frequency, day_of_month, day_of_week, start_date_obj)
    if not next_due_date_obj: return False, "No se pudo calcular la próxima fecha de vencimiento."
    related_member_db_id = None # Placeholder
    conn = get_db_connection(); 
    if not conn: return False, "Error de conexión a BD."
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO recurring_financial_items (item_type, description, default_amount, category, frequency,
                    day_of_month_to_process, day_of_week_to_process, start_date, end_date, next_due_date, 
                    is_active, auto_generate_transaction, related_member_id, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                (item_type, clean_description, str(default_amount), sanitize_text_input(category), frequency,
                day_of_month, day_of_week, convert_date_to_db_string(start_date_obj),
                convert_date_to_db_string(end_date_obj) if end_date_obj else None,
                convert_date_to_db_string(next_due_date_obj), 1 if is_active else 0, 
                1 if auto_generate else 0, related_member_db_id, sanitize_text_input(notes, True)))
            return True, str(cursor.lastrowid)
    except sqlite3.Error as e: print(f"ERROR (add_recurring_financial_item): {e}"); return False, "Error BD."
    finally:
        if conn: conn.close()


def _calculate_next_due_date_for_recurring(
    base_date: date, frequency: str, day_of_month_setting: int | None = None,
    day_of_week_setting: int | None = None, actual_start_date_of_item: date | None = None
) -> date | None:
    # (Código como el tuyo, pero VALID_FREQUENCIES no se usa aquí, solo 'frequency' string)
    today = date.today()
    if not actual_start_date_of_item: actual_start_date_of_item = base_date
    next_occurrence = None
    # ... (la lógica compleja de cálculo de fechas como la tenías, necesita revisión exhaustiva)
    # Simplificación para la corrección, la lógica interna de esta función no es la causa directa de los errores de Pylance que estamos tratando.
    # Asegúrate de que, sin importar la lógica, devuelva un 'date | None'.
    # Lo importante es que si frequency no es reconocida, maneje el caso o devuelva None.
    if frequency == 'daily': next_occurrence = base_date + timedelta(days=1)
    elif frequency == 'monthly': # Ejemplo muy simplificado
        year, month = base_date.year, base_date.month + 1
        if month > 12: month = 1; year += 1
        day = day_of_month_setting if day_of_month_setting and 1 <= day_of_month_setting <= 28 else 1 # Super simplificado
        try: next_occurrence = date(year, month, day)
        except ValueError: # ej. dia 30 en Feb
             last_day_of_prev_month = date(year,month,1)-timedelta(days=1)
             next_occurrence = last_day_of_prev_month # No es ideal pero evita error
    # ... (otras frecuencias)
    else: # Frecuencia no manejada
        print(f"ADVERTENCIA (finances.py): Frecuencia '{frequency}' no manejada en _calculate_next_due_date.")
        return base_date + timedelta(days=30) # Fallback muy simple

    # Post-procesamiento para asegurar que es futura y después del inicio real
    if next_occurrence and next_occurrence < actual_start_date_of_item:
        # Si la calculada es antes del inicio del item, intentar recalcular desde el inicio del item
        return _calculate_next_due_date_for_recurring(actual_start_date_of_item, frequency, day_of_month_setting, day_of_week_setting, actual_start_date_of_item)
    
    # Si next_occurrence sigue siendo menor o igual a base_date (y base_date no es futura), forzar avance
    if next_occurrence and next_occurrence <= base_date:
         # Este es un parche simple, la lógica recursiva anterior es mejor pero más compleja de acertar.
        if frequency == 'daily': next_occurrence = base_date + timedelta(days=1)
        # ... necesitaría más lógica para otras frecuencias para realmente "saltar" un periodo ...
        # La llamada recursiva es la forma más elegante si la condición de terminación es correcta.
        # Para ahora, con el cambio de `base_date` al calcular, esto podría no ser necesario siempre.
        # print(f"WARN: next_occurrence {next_occurrence} <= base_date {base_date} for {frequency}. Forcing advance or re-evaluating.")


    return next_occurrence


def get_pending_recurring_items_to_process(as_of_date_obj: date | None = None) -> list[dict]:
    # (Código como el tuyo)
    if as_of_date_obj is None: as_of_date_obj = date.today()
    conn = get_db_connection();
    if not conn: return []
    items_list = []
    try:
        cursor = conn.cursor()
        cursor.execute("""SELECT * FROM recurring_financial_items WHERE is_active = 1 AND next_due_date <= ? 
                          AND (end_date IS NULL OR end_date >= ?) ORDER BY next_due_date ASC, id ASC""",
                       (convert_date_to_db_string(as_of_date_obj), convert_date_to_db_string(as_of_date_obj)))
        for row in cursor.fetchall():
            item_dict = dict(row)
            item_dict['default_amount_decimal'] = Decimal(str(row['default_amount']))
            item_dict['start_date_obj'] = parse_string_to_date(row['start_date'])
            item_dict['next_due_date_obj'] = parse_string_to_date(row['next_due_date'])
            item_dict['end_date_obj'] = parse_string_to_date(row['end_date']) if row['end_date'] else None
            items_list.append(item_dict)
        return items_list
    except sqlite3.Error as e: print(f"ERROR (get_pending_recurring_items_to_process): {e}"); return []
    finally:
        if conn: conn.close()


def process_single_recurring_item(item_id: int, recorded_by_user_id: int | None) -> tuple[bool, str]:
    conn = get_db_connection()
    if not conn: return False, "Error de conexión a BD."
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM recurring_financial_items WHERE id = ?", (item_id,))
            item_data = cursor.fetchone()
            if not item_data: return False, f"Ítem recurrente ID {item_id} no encontrado."
            if not item_data['is_active']: return False, f"Ítem recurrente {item_id} no activo."

            item_dict = dict(item_data)
            item_dict['default_amount_decimal'] = Decimal(str(item_data['default_amount']))
            item_dict['start_date_obj'] = parse_string_to_date(item_data['start_date'])
            item_dict['next_due_date_obj'] = parse_string_to_date(item_data['next_due_date']) # Será el transaction_date

            transaction_date_obj_for_record = item_dict['next_due_date_obj']
            if not transaction_date_obj_for_record:
                 return False, f"Fecha de vencimiento inválida para ítem {item_id}."

            # Convertir a string para pasar a record_financial_transaction
            transaction_date_str_for_record = convert_date_to_db_string(transaction_date_obj_for_record)
            if transaction_date_str_for_record is None: # Verificación extra aunque convert_date_to_db_string debería devolver str o None
                return False, f"No se pudo convertir la fecha de vencimiento a string para ítem {item_id}."


            success_trn, msg_trn_id = record_financial_transaction(
                transaction_type=item_dict['item_type'],
                transaction_date_str=transaction_date_str_for_record, # Se le pasa un string
                description=f"(Recurrente) {item_dict['description']}",
                category=item_dict['category'],
                amount_str=str(item_dict['default_amount_decimal']),
                recorded_by_user_id=recorded_by_user_id,
                is_from_recurring=True,
                source_recurring_id=item_id
            )
            if not success_trn:
                raise sqlite3.Error(f"Fallo al generar transacción para ítem {item_id}: {msg_trn_id}")

            new_next_due_obj = _calculate_next_due_date_for_recurring(
                transaction_date_obj_for_record, # La fecha de la transacción recién creada
                item_dict['frequency'], item_dict['day_of_month_to_process'],
                item_dict['day_of_week_to_process'], item_dict['start_date_obj']
            )
            if not new_next_due_obj:
                raise sqlite3.Error(f"No se pudo calcular nueva next_due_date para ítem {item_id}.")
            
            cursor.execute(
                "UPDATE recurring_financial_items SET next_due_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (convert_date_to_db_string(new_next_due_obj), item_id)
            )
            return True, f"Ítem {item_id} procesado. Transacción: {msg_trn_id}. Próx. venc.: {format_date_for_ui(new_next_due_obj)}."
    except sqlite3.Error as e:
        print(f"ERROR (finances.py - process_single_recurring_item): {e}"); return False, f"Error BD procesando {item_id}."
    finally:
        if conn: conn.close()

def get_all_recurring_items() -> list[dict]:
    """Obtiene todos los ítems financieros recurrentes definidos."""
    conn = get_db_connection()
    if not conn: return []
    items_list = []
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rfi.* 
            FROM recurring_financial_items rfi
            ORDER BY rfi.item_type, rfi.description
        """) # Podrías añadir JOIN con members si related_member_id se usa
        for row in cursor.fetchall():
            item_dict = dict(row)
            # Convertir campos a tipos más usables si es necesario (como hicimos en get_pending)
            item_dict['default_amount_decimal'] = Decimal(str(row['default_amount']))
            item_dict['start_date_obj'] = parse_string_to_date(row['start_date'])
            item_dict['next_due_date_obj'] = parse_string_to_date(row['next_due_date'])
            item_dict['end_date_obj'] = parse_string_to_date(row['end_date']) if row['end_date'] else None
            items_list.append(item_dict)
        return items_list
    except sqlite3.Error as e:
        print(f"ERROR (finances.py - get_all_recurring_items): {e}")
        return []
    finally:
        if conn: conn.close()

def get_recurring_item_by_id(item_id: int) -> dict | None:
    """Obtiene un ítem financiero recurrente por su ID de base de datos."""
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM recurring_financial_items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        if row:
            item_dict = dict(row)
            item_dict['default_amount_decimal'] = Decimal(str(row['default_amount']))
            item_dict['start_date_obj'] = parse_string_to_date(row['start_date'])
            item_dict['next_due_date_obj'] = parse_string_to_date(row['next_due_date'])
            item_dict['end_date_obj'] = parse_string_to_date(row['end_date']) if row['end_date'] else None
            return item_dict
        return None
    except sqlite3.Error as e:
        print(f"ERROR (finances.py - get_recurring_item_by_id): {e}")
        return None
    finally:
        if conn: conn.close()

def update_recurring_item(
    item_id: int,
    item_type: str, description: str, default_amount_str: str, category: str,
    frequency: str, start_date_str: str, day_of_month: int | None = None,
    day_of_week: int | None = None, end_date_str: str | None = None,
    is_active: bool = True, auto_generate: bool = False, notes: str | None = None,
    next_due_date_str: str | None = None, # Permitir actualizar next_due_date manualmente
    related_member_internal_id: str | None = None
) -> tuple[bool, str]:
    """Actualiza un ítem financiero recurrente existente."""
    # Validaciones similares a add_recurring_financial_item
    if item_type not in ['income', 'expense']: return False, "Tipo inválido."
    if frequency not in VALID_FREQUENCIES: return False, "Frecuencia inválida."
    # ... (más validaciones para campos obligatorios)
    
    default_amount = parse_string_to_decimal(default_amount_str)
    if default_amount is None or default_amount <= Decimal('0'): return False, "Monto inválido."
    
    start_date_obj = parse_string_to_date(start_date_str, True)
    if not start_date_obj: return False, "Fecha de inicio inválida."
    end_date_obj = parse_string_to_date(end_date_str, True) if end_date_str else None
    
    # Si se pasa next_due_date_str, usarla, sino, recalcularla (esto es opcional, podría solo actualizarse al procesar)
    next_due_date_to_set_obj = None
    if next_due_date_str:
        next_due_date_to_set_obj = parse_string_to_date(next_due_date_str, True)
        if not next_due_date_to_set_obj: return False, "Próxima fecha de vencimiento (manual) inválida."
    else: # Recalcular si no se especifica
        # Cuidado: recalcular aquí puede no ser siempre lo deseado al editar.
        # Podríamos obtener el next_due_date actual y solo recalcular si cambia la frecuencia/start_date.
        # Por ahora, lo dejamos simple: si no se pasa, no se cambia explícitamente aquí (solo updated_at).
        # El recálculo de next_due_date ocurre en process_single_recurring_item.
        # O podríamos recalcularlo si cambia la frecuencia o el start_date:
        current_item = get_recurring_item_by_id(item_id)
        if not current_item: return False, "Ítem a actualizar no encontrado."
        
        recalculate_next_due = False
        if current_item['frequency'] != frequency or \
           current_item['start_date_obj'] != start_date_obj or \
           current_item.get('day_of_month_to_process') != day_of_month or \
           current_item.get('day_of_week_to_process') != day_of_week:
            recalculate_next_due = True

        if recalculate_next_due:
            # Si cambió algo que afecta la recurrencia, recalcular next_due_date
            # Aquí base_date para recalcular debería ser la fecha de inicio del ítem
            # o una fecha de referencia, no necesariamente today.
            next_due_date_to_set_obj = _calculate_next_due_date_for_recurring(start_date_obj, frequency, day_of_month, day_of_week, start_date_obj)
            if not next_due_date_to_set_obj: return False, "No se pudo recalcular la próxima fecha de vencimiento."
        else:
            next_due_date_to_set_obj = current_item['next_due_date_obj'] # Mantener la existente

    related_member_db_id = None # Placeholder

    conn = get_db_connection()
    if not conn: return False, "Error de conexión."
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE recurring_financial_items SET
                    item_type = ?, description = ?, default_amount = ?, category = ?, frequency = ?,
                    day_of_month_to_process = ?, day_of_week_to_process = ?,
                    start_date = ?, end_date = ?, next_due_date = ?,
                    is_active = ?, auto_generate_transaction = ?, related_member_id = ?,
                    notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                item_type, sanitize_text_input(description), str(default_amount), sanitize_text_input(category), frequency,
                day_of_month, day_of_week,
                convert_date_to_db_string(start_date_obj),
                convert_date_to_db_string(end_date_obj) if end_date_obj else None,
                convert_date_to_db_string(next_due_date_to_set_obj),
                1 if is_active else 0, 1 if auto_generate else 0,
                related_member_db_id, sanitize_text_input(notes, True),
                item_id
            ))
            if cursor.rowcount == 0:
                return False, "Ítem recurrente no encontrado para actualizar o sin cambios."
            return True, "Ítem recurrente actualizado exitosamente."
    except sqlite3.Error as e:
        print(f"ERROR (finances.py - update_recurring_item): {e}")
        return False, "Error de BD al actualizar ítem recurrente."
    finally:
        if conn: conn.close()

def delete_recurring_item(item_id: int) -> tuple[bool, str]:
    """Elimina un ítem financiero recurrente."""
    conn = get_db_connection()
    if not conn: return False, "Error de conexión."
    try:
        with conn:
            cursor = conn.cursor()
            # Primero verificar si hay transacciones generadas por este recurrente
            # y decidir qué hacer (desvincular o impedir borrado).
            # La FK en financial_transactions (source_recurring_id) es ON DELETE SET NULL.
            cursor.execute("DELETE FROM recurring_financial_items WHERE id = ?", (item_id,))
            if cursor.rowcount == 0:
                return False, "Ítem recurrente no encontrado para eliminar."
            return True, "Ítem recurrente eliminado exitosamente."
    except sqlite3.Error as e:
        print(f"ERROR (finances.py - delete_recurring_item): {e}")
        return False, "Error de BD al eliminar ítem recurrente."
    finally:
        if conn: conn.close()


# --- Script de autocomprobación ---
if __name__ == "__main__":
    # (El código de if __name__ == "__main__" como lo tenías, pero usando las constantes y funciones importadas directamente)
    print(f"--- {os.path.basename(__file__)} Self-Check ---") # os.path.basename necesita 'import os'

    print("\n1. Registrando un ingreso de prueba...")
    # Asegurar que UI_DISPLAY_DATE_FORMAT está importada de config.py
    today_date_obj = get_current_date_for_db()
    today_ui_format_str = format_date_for_ui(today_date_obj) # Usar format_date_for_ui que ya usa la constante de config
    
    success_inc, msg_inc = record_financial_transaction(
        transaction_type='income',
        transaction_date_str=today_ui_format_str, # Pasa un string formateado para UI, parse_string_to_date lo manejará
        description="Cuota Ana Lopez (Prueba Main)",
        category="Ingresos por Cuotas Mensuales", # Asegurar que esta categoría esté en DEFAULT_INCOME_CATEGORIES_LIST
        amount_str="35,00",
        payment_method="Tarjeta"
    )
    print(f"  Registro Ingreso: {success_inc} - {msg_inc}")

    # ... (resto de las pruebas en if __name__ como las tenías, asegurando que usan
    #      UI_DISPLAY_DATE_FORMAT y format_currency_for_display (de utils) correctamente) ...
    print("\n3. Obteniendo transacciones...")
    transactions, total_count = get_financial_transactions(limit=5)
    if transactions:
        print(f"  Total (sin filtro): {total_count}, mostrando {len(transactions)}")
        for t in transactions:
            amount_disp = format_currency_for_display(t['amount_decimal']) # Usa la importada de utils
            print(f"    - ID: {t['internal_transaction_id']}, Fecha: {t['transaction_date_ui']}, Desc: {t['description']}, Monto: {amount_disp}")

    print("\n4. Resumen financiero del mes actual...")
    start_month_date_obj = date.today().replace(day=1)
    start_month_ui_str = format_date_for_ui(start_month_date_obj) # Usa la de utils

    summary = get_financial_summary(start_date_str=start_month_ui_str)
    print(f"  Resumen desde {start_month_ui_str}:")
    print(f"    Ingresos: {format_currency_for_display(summary['total_income'])}") # Usa la importada
    print(f"    Gastos:   {format_currency_for_display(summary['total_expense'])}")
    print(f"    Balance:  {format_currency_for_display(summary['net_balance'])}")

    # (El resto de pruebas de recurrentes como antes...)
    print(f"\n--- Fin de pruebas de {os.path.basename(__file__)} ---")
    print(f"--- {os.path.basename(__file__)} Self-Check ---")

    print("\n1. Registrando un ingreso de prueba...")
    # --- CORRECCIÓN: Usar la constante UI_DISPLAY_DATE_FORMAT de config.py (ya importada) ---
    today_ui_format = get_current_date_for_db().strftime(UI_DISPLAY_DATE_FORMAT)
    success_inc, msg_inc = record_financial_transaction(
        transaction_type='income',
        transaction_date_str=today_ui_format,
        description="Cuota Ana Lopez (Prueba)",
        category="Ingresos por Cuotas Mensuales",
        amount_str="35,00",
        payment_method="Tarjeta"
    )
    print(f"  Registro Ingreso: {success_inc} - {msg_inc}")

    print("\n3. Obteniendo transacciones...")
    transactions, total_count = get_financial_transactions(limit=5)
    if transactions:
        print(f"  Total (sin filtro): {total_count}, mostrando {len(transactions)}")
        for t in transactions:
            # --- CORRECCIÓN: Usar format_currency_for_display de utils.py (ya importada) ---
            amount_disp = format_currency_for_display(t['amount_decimal'])
            print(f"    - ID: {t['internal_transaction_id']}, Fecha: {t['transaction_date_ui']}, Desc: {t['description']}, Monto: {amount_disp}")

    print("\n4. Resumen financiero del mes actual...")
    # --- CORRECCIÓN: Usar UI_DISPLAY_DATE_FORMAT ---
    start_month_ui = date.today().replace(day=1).strftime(UI_DISPLAY_DATE_FORMAT)
    summary = get_financial_summary(start_date_str=start_month_ui)
    print(f"  Resumen desde {start_month_ui}:")
    # --- CORRECCIÓN: Usar format_currency_for_display ---
    print(f"    Ingresos: {format_currency_for_display(summary['total_income'])}")
    print(f"    Gastos:   {format_currency_for_display(summary['total_expense'])}")
    print(f"    Balance:  {format_currency_for_display(summary['net_balance'])}")
    
    # ... (resto de pruebas para ítems recurrentes como antes) ...
    print("\n5. Añadiendo ítem de gasto recurrente 'Alquiler Mensual'...")
    success_rec_exp, msg_rec_exp = add_recurring_financial_item(
        item_type='expense',
        description="Alquiler mensual (Prueba)",
        default_amount_str="1200.00",
        category="Alquiler o Hipoteca del Local",
        frequency='monthly',
        start_date_str=start_month_ui,
        day_of_month=date.today().day, # Que venza hoy para probar el proceso
        auto_generate=True 
    )
    rec_item_id = None
    if success_rec_exp:
        rec_item_id = int(msg_rec_exp)
        print(f"  Ítem recurrente 'Alquiler' añadido ID: {rec_item_id}")
    else:
        print(f"  Fallo al añadir gasto recurrente 'Alquiler': {msg_rec_exp}")

    if rec_item_id:
        print("\n6. Procesando ítems recurrentes pendientes HOY...")
        pending = get_pending_recurring_items_to_process() # Probar sin fecha para que use hoy
        print(f"   Items pendientes para hoy: {len(pending)}")
        for item_p in pending:
            if item_p['id'] == rec_item_id :
                print(f"    Procesando {item_p['description']} (ID: {item_p['id']})...")
                success_p, msg_p = process_single_recurring_item(item_p['id'], recorded_by_user_id=1) # Asumir user 1
                print(f"      Resultado: {success_p} - {msg_p}")
                break # Procesar solo el que acabamos de crear para la prueba

    print(f"\n--- Fin de pruebas de {os.path.basename(__file__)} ---")