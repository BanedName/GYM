# gimnasio_mgmt_gui/core_logic/finances.py
# Lógica de negocio para la gestión financiera: ingresos, gastos y elementos recurrentes.

import sqlite3
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import os # <-- Añadido para usar os.path.basename en el if __name__

# Importaciones del mismo paquete (core_logic) o de la raíz del proyecto
try:
    from .database import get_db_connection
    from .utils import ( # <-- CORRECCIÓN 2: Importar format_currency_for_display
        generate_internal_id, sanitize_text_input, parse_string_to_date,
        format_date_for_ui, convert_date_to_db_string, parse_string_to_decimal,
        get_current_date_for_db, format_currency_for_display # <-- Añadida aquí
    )
    from config import (
        DEFAULT_INCOME_CATEGORIES_LIST, DEFAULT_EXPENSE_CATEGORIES_LIST,
        VALID_FREQUENCIES, DB_STORAGE_DATE_FORMAT,
        UI_DISPLAY_DATE_FORMAT # <-- CORRECCIÓN 1: Importar UI_DISPLAY_DATE_FORMAT
    )
except ImportError as e:
    print(f"ERROR CRÍTICO (finances.py): Fallo en importaciones esenciales. Error: {e}")
    raise

# --- CONSTANTES PARA FRECUENCIAS (Podrían estar en config.py si se usan en más sitios) ---
# VALID_FREQUENCIES ya se importa de config.py si está definida allí, si no, la defino aquí.
# Si VALID_FREQUENCIES ya está en config.py, esta línea de abajo no es necesaria o se puede quitar.
# Pero dado que config.py está largo, lo dejo por si acaso como un array local si no se importó.
try:
    VALID_FREQUENCIES # Comprobar si ya está importada
except NameError:
    VALID_FREQUENCIES = ['daily', 'weekly', 'bi-weekly', 'monthly', 'quarterly', 'semi-annually', 'annually']


# --- GESTIÓN DE TRANSACCIONES FINANCIERAS (INGRESOS/GASTOS PUNTUALES) ---

def record_financial_transaction(
    transaction_type: str,
    transaction_date_str: str,
    description: str,
    category: str,
    amount_str: str,
    payment_method: str | None = None,
    related_member_internal_id: str | None = None, # Podríamos necesitar el ID de la DB del miembro
    recorded_by_user_id: int | None = None,
    reference_document_number: str | None = None,
    notes: str | None = None,
    is_from_recurring: bool = False,
    source_recurring_id: int | None = None
) -> tuple[bool, str]:
    # (Código de record_financial_transaction sin cambios)
    # ... (revisar que las validaciones y conversiones usen las funciones de utils.py) ...
    if transaction_type not in ['income', 'expense']:
        return False, "Tipo de transacción no válido."
    trans_date = parse_string_to_date(transaction_date_str, permissive_formats=True)
    if not trans_date:
        return False, "Formato de fecha no válido."
    clean_description = sanitize_text_input(description)
    if not clean_description:
        return False, "Descripción obligatoria."
    clean_category = sanitize_text_input(category)
    if not clean_category:
        return False, "Categoría obligatoria."
    amount = parse_string_to_decimal(amount_str)
    if amount is None or amount <= Decimal('0'):
        return False, "Monto no válido."

    internal_transaction_id = generate_internal_id(prefix="TRN" if transaction_type == 'income' else "EXP")
    
    related_member_db_id = None
    if related_member_internal_id:
        # Esta parte sigue siendo conceptual hasta que tengamos members.py bien conectado
        # desde el módulo members, necesitaríamos una función como:
        # from .members import get_member_db_id_from_internal_id
        # related_member_db_id = get_member_db_id_from_internal_id(related_member_internal_id)
        # Por ahora, no se setea.
        pass

    conn = get_db_connection()
    if not conn: return False, "Error de conexión a BD."

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO financial_transactions (
                    internal_transaction_id, transaction_type, transaction_date, description, category,
                    amount, payment_method, related_member_id, recorded_by_user_id,
                    reference_document_number, notes, is_recurring_source, source_recurring_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                internal_transaction_id, transaction_type, convert_date_to_db_string(trans_date),
                clean_description, clean_category, str(amount), 
                sanitize_text_input(payment_method, allow_empty=True),
                related_member_db_id, 
                recorded_by_user_id,  
                sanitize_text_input(reference_document_number, allow_empty=True),
                sanitize_text_input(notes, allow_empty=True),
                1 if is_from_recurring else 0,
                source_recurring_id 
            ))
            return True, internal_transaction_id
    except sqlite3.Error as e:
        print(f"ERROR (finances.py - record_financial_transaction): {e}")
        return False, "Error de base de datos al registrar transacción."
    finally:
        if conn: conn.close()


def get_financial_transactions(
    start_date_str: str | None = None,
    end_date_str: str | None = None,
    transaction_type: str | None = None, 
    category: str | None = None,
    limit: int = 100, 
    offset: int = 0
) -> tuple[list[dict], int]:
    # (Código de get_financial_transactions sin cambios significativos aquí...)
    conn = get_db_connection()
    if not conn: return [], 0

    conditions = []
    params = []
    
    count_query = "SELECT COUNT(id) as total_count FROM financial_transactions ft" # alias a la tabla ft
    data_query = """
        SELECT ft.*, m.full_name as member_name, su.username as recorded_by_username
        FROM financial_transactions ft
        LEFT JOIN members m ON ft.related_member_id = m.id
        LEFT JOIN system_users su ON ft.recorded_by_user_id = su.id
    """

    if start_date_str:
        s_date = parse_string_to_date(start_date_str, permissive_formats=True)
        if s_date:
            conditions.append("ft.transaction_date >= ?") # usar alias ft
            params.append(convert_date_to_db_string(s_date))
    
    if end_date_str:
        e_date = parse_string_to_date(end_date_str, permissive_formats=True)
        if e_date:
            conditions.append("ft.transaction_date <= ?") # usar alias ft
            params.append(convert_date_to_db_string(e_date))

    if transaction_type and transaction_type in ['income', 'expense']:
        conditions.append("ft.transaction_type = ?") # usar alias ft
        params.append(transaction_type)

    if category:
        clean_cat = sanitize_text_input(category)
        if clean_cat: # Solo añadir si no está vacío
            conditions.append("ft.category LIKE ?") # usar alias ft
            params.append(f"%{clean_cat}%")


    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)
        count_query += where_clause
        data_query += where_clause

    data_query += " ORDER BY ft.transaction_date DESC, ft.id DESC LIMIT ? OFFSET ?" # Ordenar por ID como secundario para consistencia
    data_params = tuple(params + [limit, offset])
    
    transactions_list = []
    total_count = 0

    try:
        cursor = conn.cursor()
        cursor.execute(count_query, tuple(params))
        count_result = cursor.fetchone()
        if count_result:
            total_count = count_result['total_count']

        cursor.execute(data_query, data_params)
        for row in cursor.fetchall():
            trans_dict = dict(row)
            trans_dict['transaction_date_obj'] = parse_string_to_date(row['transaction_date']) # Añadir objeto date
            trans_dict['transaction_date_ui'] = format_date_for_ui(trans_dict['transaction_date_obj'])
            trans_dict['amount_decimal'] = Decimal(str(row['amount']))
            transactions_list.append(trans_dict)
        
        return transactions_list, total_count
    except sqlite3.Error as e:
        print(f"ERROR (finances.py - get_financial_transactions): {e}")
        return [], 0
    finally:
        if conn: conn.close()


def get_financial_summary(
    start_date_str: str | None = None,
    end_date_str: str | None = None
) -> dict:
    # (Código de get_financial_summary sin cambios significativos aquí...)
    conn = get_db_connection()
    if not conn: return {"total_income": Decimal('0'), "total_expense": Decimal('0'), "net_balance": Decimal('0')}

    base_query = "SELECT SUM(amount) FROM financial_transactions WHERE transaction_type = ?"
    conditions = []
    params_suffix = [] # Params para la parte del WHERE clause

    if start_date_str:
        s_date = parse_string_to_date(start_date_str, permissive_formats=True)
        if s_date:
            conditions.append("transaction_date >= ?")
            params_suffix.append(convert_date_to_db_string(s_date))
    
    if end_date_str:
        e_date = parse_string_to_date(end_date_str, permissive_formats=True)
        if e_date:
            conditions.append("transaction_date <= ?")
            params_suffix.append(convert_date_to_db_string(e_date))

    query_suffix_str = ""
    if conditions:
        query_suffix_str = " AND " + " AND ".join(conditions)
    
    total_income = Decimal('0')
    total_expense = Decimal('0')

    try:
        cursor = conn.cursor()
        
        # Ingresos
        params_inc = ['income'] + params_suffix
        cursor.execute(base_query + query_suffix_str, tuple(params_inc))
        result_inc = cursor.fetchone()
        if result_inc and result_inc[0] is not None:
            total_income = Decimal(str(result_inc[0]))

        # Gastos
        params_exp = ['expense'] + params_suffix
        cursor.execute(base_query + query_suffix_str, tuple(params_exp))
        result_exp = cursor.fetchone()
        if result_exp and result_exp[0] is not None:
            total_expense = Decimal(str(result_exp[0]))

        net_balance = total_income - total_expense
        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_balance": net_balance
        }
    except sqlite3.Error as e:
        print(f"ERROR (finances.py - get_financial_summary): {e}")
        return {"total_income": Decimal('0'), "total_expense": Decimal('0'), "net_balance": Decimal('0')}
    finally:
        if conn: conn.close()


# --- GESTIÓN DE ÍTEMS FINANCIEROS RECURRENTES ---
# (Las funciones add_recurring_financial_item, _calculate_next_due_date_for_recurring,
#  get_pending_recurring_items_to_process, process_single_recurring_item
#  permanecen estructuralmente como estaban. Asegúrate que todas las dependencias
#  (parse_string_to_decimal, convert_date_to_db_string, etc.) están bien usadas y
#  las conexiones a BD se manejan y cierran correctamente.)
# ... (CÓDIGO DE ÍTEMS RECURRENTES VA AQUÍ - Asumimos que es el mismo que antes, con cierres de conexión si aplica)
def add_recurring_financial_item(
    item_type: str,
    description: str,
    default_amount_str: str,
    category: str,
    frequency: str, 
    start_date_str: str,
    day_of_month: int | None = None, 
    day_of_week: int | None = None, 
    end_date_str: str | None = None,
    is_active: bool = True,
    auto_generate: bool = False,
    notes: str | None = None,
    related_member_internal_id: str | None = None # Para asociar con un miembro
) -> tuple[bool, str]:
    if item_type not in ['income', 'expense']:
        return False, "Tipo de ítem no válido."
    if frequency not in VALID_FREQUENCIES: # VALID_FREQUENCIES debe estar definida o importada
        return False, f"Frecuencia '{frequency}' no válida."
    
    clean_description = sanitize_text_input(description)
    if not clean_description: return False, "Descripción obligatoria."
    
    default_amount = parse_string_to_decimal(default_amount_str)
    if default_amount is None or default_amount <= Decimal('0'):
        return False, "Monto por defecto no válido."

    start_date_obj = parse_string_to_date(start_date_str, permissive_formats=True)
    if not start_date_obj: return False, "Fecha de inicio no válida."
    
    end_date_obj = parse_string_to_date(end_date_str, permissive_formats=True) if end_date_str else None

    next_due_date_obj = _calculate_next_due_date_for_recurring(start_date_obj, frequency, day_of_month, day_of_week, start_date_obj)
    if not next_due_date_obj:
        return False, "No se pudo calcular la próxima fecha de vencimiento."

    related_member_db_id = None
    if related_member_internal_id:
        # Similar a record_financial_transaction, necesitaría lógica para obtener db_id.
        pass

    conn = get_db_connection()
    if not conn: return False, "Error de conexión a BD."

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO recurring_financial_items (
                    item_type, description, default_amount, category, frequency,
                    day_of_month_to_process, day_of_week_to_process,
                    start_date, end_date, next_due_date, is_active, auto_generate_transaction,
                    related_member_id, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                item_type, clean_description, str(default_amount), sanitize_text_input(category), frequency,
                day_of_month, day_of_week,
                convert_date_to_db_string(start_date_obj),
                convert_date_to_db_string(end_date_obj) if end_date_obj else None,
                convert_date_to_db_string(next_due_date_obj),
                1 if is_active else 0, 1 if auto_generate else 0,
                related_member_db_id, sanitize_text_input(notes, allow_empty=True)
            ))
            item_id = cursor.lastrowid
            return True, str(item_id)
    except sqlite3.Error as e:
        print(f"ERROR (finances.py - add_recurring_financial_item): {e}")
        return False, "Error de base de datos al añadir ítem recurrente."
    finally:
        if conn: conn.close()


def _calculate_next_due_date_for_recurring(
    base_date: date, # La fecha a partir de la cual calcular (puede ser la de inicio o la última procesada)
    frequency: str,
    day_of_month_setting: int | None = None,
    day_of_week_setting: int | None = None,
    actual_start_date_of_item: date | None = None # Fecha original de inicio del recurrente
) -> date | None:
    """
    Calcula la próxima fecha de vencimiento para un ítem recurrente.
    'base_date' es la última fecha procesada o la fecha de inicio del ítem si nunca se procesó.
    'actual_start_date_of_item' es para asegurar que la primera ocurrencia no sea antes del inicio.
    """
    today = date.today()
    if not actual_start_date_of_item: # Si no se pasa, usar base_date como referencia
        actual_start_date_of_item = base_date
        
    next_occurrence = None

    if frequency == 'daily':
        next_occurrence = base_date + timedelta(days=1)
    
    elif frequency == 'weekly':
        if day_of_week_setting is None or not (0 <= day_of_week_setting <= 6):
            day_of_week_setting = actual_start_date_of_item.weekday() # Usar día de la semana de inicio si no se especifica
        
        days_to_add = (day_of_week_setting - base_date.weekday() + 7) % 7
        if days_to_add == 0 and base_date >= today: # Si hoy es el día, y ya pasó hoy, la próxima semana
             # O si base_date es el día correcto, pero es futura
            pass
        elif days_to_add == 0: # Si hoy es el día y base_date es pasada
             days_to_add = 7

        next_occurrence = base_date + timedelta(days=days_to_add)
        if next_occurrence <= base_date : # Asegurar que siempre avanzamos si la base_date es la de hoy y ya pasó
             next_occurrence += timedelta(weeks=1)


    elif frequency == 'monthly':
        if day_of_month_setting is None or not (1 <= day_of_month_setting <= 31):
            day_of_month_setting = actual_start_date_of_item.day # Usar día del mes de inicio

        # Avanzar al siguiente mes desde base_date
        month = base_date.month + 1
        year = base_date.year
        if month > 12:
            month = 1
            year += 1
        
        # Intentar crear la fecha con el día objetivo, manejar si el día no existe en ese mes
        try:
            next_occurrence = date(year, month, day_of_month_setting)
        except ValueError: # Día no existe (ej. 30 de Feb)
            # Ir al último día del mes
            next_month_first_day = date(year, month, 1)
            if month == 12:
                next_occurrence = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                next_occurrence = date(year, month + 1, 1) - timedelta(days=1)
                
    elif frequency == 'annually':
        if day_of_month_setting is None or not (1 <= day_of_month_setting <= 31):
            day_of_month_setting = actual_start_date_of_item.day
        target_month = actual_start_date_of_item.month # Mantener el mes original del item
        
        year_to_try = base_date.year
        # Intentar para el año actual de base_date
        try:
            potential_date = date(year_to_try, target_month, day_of_month_setting)
            if potential_date > base_date:
                next_occurrence = potential_date
            else: # Si ya pasó este año, ir al siguiente
                next_occurrence = date(year_to_try + 1, target_month, day_of_month_setting)
        except ValueError: # Día no válido para el mes (ej. 29 Feb en año no bisiesto)
             # Podríamos tratar de encontrar el más cercano o fallar. Aquí vamos al siguiente año.
            next_occurrence = date(year_to_try + 1, target_month, day_of_month_setting)


    # ... (Lógica para 'quarterly', 'semi-annually', 'bi-weekly' necesitaría ser implementada) ...
    # Esta función es un buen ejemplo de lógica de negocio que puede ser compleja.

    # Asegurarse de que la fecha calculada no sea anterior a la fecha de inicio real del ítem recurrente
    if next_occurrence and next_occurrence < actual_start_date_of_item:
        # Esto puede pasar si base_date es la fecha de la última transacción procesada
        # y actual_start_date_of_item es la fecha en que el recurrente comenzó.
        # En este caso, el primer 'next_due_date' debe ser después o igual a actual_start_date_of_item
        # Volver a calcular, pero esta vez usando actual_start_date_of_item como base si la base_date original
        # era anterior al inicio del item.
        # Esta es una simplificación, la lógica precisa puede ser complicada.
        # Si base_date ya era el next_due_date original, entonces next_occurrence ya es futuro.
        pass


    # Si, después de todo, la próxima ocurrencia sigue siendo hoy o pasada y queríamos la *siguiente*
    if next_occurrence and next_occurrence <= today and base_date >= today :
        # Este es un caso complicado, implica que el calculo basado en 'base_date' que es hoy/futura
        # dió un resultado no futuro. Necesitamos forzar avance.
        # Ej: si base_date es hoy y freq es 'daily', debería ser mañana.
        # La función está pensada para dar la SIGUIENTE aparición después de base_date.
        # Si base_date es la fecha en que el item está configurado para ocurrir (ej. day_of_month)
        # y esta fecha ya pasó en el periodo actual, la función debe calcular para el *próximo* periodo.

        # Revisión: La `base_date` que se pasa a esta función DEBE ser la fecha que se acaba de procesar
        # o la fecha de inicio si es la primera vez. La función calcula la SIGUIENTE ocurrencia.
        if frequency == 'daily' and next_occurrence <= base_date: next_occurrence = base_date + timedelta(days=1)
        # ... se necesitarían más ajustes aquí para otras frecuencias ...


    return next_occurrence


def get_pending_recurring_items_to_process(as_of_date_obj: date | None = None) -> list[dict]:
    if as_of_date_obj is None:
        as_of_date_obj = date.today()

    conn = get_db_connection()
    if not conn: return []
    items_list = []
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM recurring_financial_items
            WHERE is_active = 1 AND next_due_date <= ?
              AND (end_date IS NULL OR end_date >= ?) 
            ORDER BY next_due_date ASC, id ASC
        """, (convert_date_to_db_string(as_of_date_obj), convert_date_to_db_string(as_of_date_obj)))
        
        for row in cursor.fetchall():
            item_dict = dict(row)
            item_dict['default_amount_decimal'] = Decimal(str(row['default_amount'])) # Convertir a Decimal
            item_dict['start_date_obj'] = parse_string_to_date(row['start_date'])
            item_dict['next_due_date_obj'] = parse_string_to_date(row['next_due_date'])
            item_dict['end_date_obj'] = parse_string_to_date(row['end_date']) if row['end_date'] else None
            items_list.append(item_dict)
        return items_list
    except sqlite3.Error as e:
        print(f"ERROR (finances.py - get_pending_recurring_items_to_process): {e}")
        return []
    finally:
        if conn: conn.close()


def process_single_recurring_item(item_id: int, recorded_by_user_id: int | None) -> tuple[bool, str]:
    conn = get_db_connection()
    if not conn: return False, "Error de conexión a BD."

    try:
        # Iniciar transacción para asegurar atomicidad
        with conn: # conn.isolation_level = None # Podría ser necesario para control manual
            # conn.execute("BEGIN") # No necesario si with conn hace la transacción
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM recurring_financial_items WHERE id = ?", (item_id,))
            item_data = cursor.fetchone()

            if not item_data:
                return False, f"Ítem recurrente ID {item_id} no encontrado."
            if not item_data['is_active']:
                return False, f"Ítem recurrente {item_id} no está activo."

            item_dict = dict(item_data) # Convertir a dict para fácil acceso
            item_dict['default_amount_decimal'] = Decimal(str(item_data['default_amount']))
            item_dict['start_date_obj'] = parse_string_to_date(item_data['start_date'])
            item_dict['next_due_date_obj'] = parse_string_to_date(item_data['next_due_date'])


            # 1. Registrar la transacción financiera
            # Usar la next_due_date del ítem como fecha de la transacción
            transaction_date_for_item = item_dict['next_due_date_obj']
            if not transaction_date_for_item:
                 return False, f"Fecha de vencimiento (next_due_date) inválida para ítem {item_id}."

            success_trn, msg_trn_id = record_financial_transaction(
                transaction_type=item_dict['item_type'],
                transaction_date_str=convert_date_to_db_string(transaction_date_for_item), # Convertir de objeto date a string BD
                description=f"(Recurrente) {item_dict['description']}",
                category=item_dict['category'],
                amount_str=str(item_dict['default_amount_decimal']),
                recorded_by_user_id=recorded_by_user_id,
                is_from_recurring=True,
                source_recurring_id=item_id
            )
            if not success_trn:
                # conn.execute("ROLLBACK") # Si la transacción falló, no actualizar el recurrente
                raise sqlite3.Error(f"Fallo al generar transacción para ítem recurrente {item_id}: {msg_trn_id}")


            # 2. Calcular la nueva next_due_date para el ítem recurrente
            # La base para el cálculo es la 'next_due_date' que acabamos de procesar.
            new_next_due_obj = _calculate_next_due_date_for_recurring(
                transaction_date_for_item, # La fecha de la transacción recién creada
                item_dict['frequency'],
                item_dict['day_of_month_to_process'],
                item_dict['day_of_week_to_process'],
                item_dict['start_date_obj'] # La fecha original de inicio del ítem
            )

            if not new_next_due_obj:
                raise sqlite3.Error(f"No se pudo calcular nueva next_due_date para ítem {item_id}.")
            
            # 3. Actualizar el ítem recurrente en la BD con la nueva next_due_date
            cursor.execute(
                "UPDATE recurring_financial_items SET next_due_date = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (convert_date_to_db_string(new_next_due_obj), item_id)
            )
            # conn.execute("COMMIT") # No necesario si with conn hace el commit
            return True, f"Ítem {item_id} procesado. Transacción: {msg_trn_id}. Próx. venc.: {format_date_for_ui(new_next_due_obj)}."

    except sqlite3.Error as e:
        print(f"ERROR (finances.py - process_single_recurring_item - Transacción): {e}")
        # conn.execute("ROLLBACK") # Ya se maneja por 'with conn' o debería.
        return False, f"Error de BD al procesar ítem recurrente {item_id}. Se revirtieron los cambios."
    finally:
        if conn: conn.close()



# --- Script de autocomprobación ---
if __name__ == "__main__":
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