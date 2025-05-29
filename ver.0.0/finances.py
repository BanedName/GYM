# finances.py
import sqlite3
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta # Para cálculos de fechas más complejos (ej. "próximo mes")

from database import get_db_connection
from utils import (
    generate_invoice_number,
    format_currency,
    format_date,
    parse_date_string,
    clean_string_input
)
from config import (
    CURRENCY_SYMBOL,
    DEFAULT_INCOME_CATEGORIES,
    DEFAULT_EXPENSE_CATEGORIES,
    DATE_FORMAT_DISPLAY
)

# --- Funciones para Transacciones (Ingresos y Gastos Puntuales) ---

def record_transaction(
    type_str: str, # 'income' o 'expense'
    description: str,
    amount: float,
    transaction_date_str: str = None, # YYYY-MM-DD, si es None, hoy
    category: str = None,
    payment_method: str = None,
    member_id: int = None, # ID de la BD del miembro, si aplica
    user_id: int = None, # ID del usuario del sistema que registra
    reference_id: str = None # Ej. número de factura manual
) -> dict | None:
    """
    Registra una transacción financiera (ingreso o gasto).
    Devuelve un diccionario con la transacción registrada o None si falla.
    """
    description = clean_string_input(description)
    if not description or not type_str or amount is None: # Amount puede ser 0, pero no None
        print("Error: Tipo, descripción y monto son obligatorios.")
        return None
    if type_str not in ['income', 'expense']:
        print("Error: El tipo de transacción debe ser 'income' o 'expense'.")
        return None
    if not isinstance(amount, (int, float)) or amount < 0: # Permitir 0 para correcciones? No, monto debe ser > 0
        print("Error: El monto debe ser un número positivo.")
        return None

    parsed_transaction_date = parse_date_string(transaction_date_str) if transaction_date_str else date.today()
    if not parsed_transaction_date:
        print("Error: Formato de fecha de transacción inválido. Use YYYY-MM-DD o deje en blanco para hoy.")
        return None

    if not category: # Asignar una categoría genérica si no se provee
        category = "Otros Ingresos" if type_str == 'income' else "Otros Gastos"
        print(f"Advertencia: No se especificó categoría, usando '{category}'.")

    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()

    try:
        # Si es un ingreso y no tiene reference_id, generamos uno tipo recibo
        if type_str == 'income' and not reference_id:
            reference_id = generate_invoice_number(prefix="REC")

        sql = """
            INSERT INTO financial_transactions (
                type, description, amount, transaction_date, category,
                payment_method, member_id, user_id, reference_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            type_str, description, amount, parsed_transaction_date, category,
            payment_method, member_id, user_id, reference_id
        )
        cursor.execute(sql, params)
        transaction_db_id = cursor.lastrowid
        conn.commit()

        print(f"{type_str.capitalize()} de {format_currency(amount, CURRENCY_SYMBOL)} registrado: '{description}'.")
        return get_transaction_by_id(transaction_db_id) # Devolver la transacción completa

    except Exception as e:
        print(f"Error al registrar transacción: {e}")
        return None
    finally:
        conn.close()

def get_transaction_by_id(transaction_id: int) -> dict | None:
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM financial_transactions WHERE id = ?", (transaction_id,))
        transaction = cursor.fetchone()
        return dict(transaction) if transaction else None
    finally:
        conn.close()

def get_transactions(
    type_filter: str = None, # 'income', 'expense', o None para ambos
    start_date_str: str = None, # YYYY-MM-DD
    end_date_str: str = None,   # YYYY-MM-DD
    category_filter: str = None,
    member_id_filter: int = None,
    limit: int = 100,
    sort_by: str = "transaction_date",
    order: str = "DESC"
) -> list[dict]:
    """
    Obtiene una lista de transacciones financieras con filtros opcionales.
    """
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor()

    allowed_sort_columns = ["transaction_date", "amount", "category", "type", "id"]
    if sort_by not in allowed_sort_columns: sort_by = "transaction_date"
    if order.upper() not in ["ASC", "DESC"]: order = "DESC"

    base_query = "SELECT ft.*, m.full_name as member_name FROM financial_transactions ft LEFT JOIN members m ON ft.member_id = m.id"
    conditions = []
    params = []

    if type_filter and type_filter in ['income', 'expense']:
        conditions.append("ft.type = ?")
        params.append(type_filter)
    
    parsed_start_date = parse_date_string(start_date_str)
    if parsed_start_date:
        conditions.append("ft.transaction_date >= ?")
        params.append(parsed_start_date)

    parsed_end_date = parse_date_string(end_date_str)
    if parsed_end_date:
        conditions.append("ft.transaction_date <= ?")
        params.append(parsed_end_date)
    
    if category_filter:
        conditions.append("ft.category = ?")
        params.append(category_filter)

    if member_id_filter is not None:
        conditions.append("ft.member_id = ?")
        params.append(member_id_filter)
    
    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += f" ORDER BY ft.{sort_by} {order.upper()} LIMIT ?"
    params.append(limit)

    try:
        cursor.execute(base_query, tuple(params))
        transactions = [dict(row) for row in cursor.fetchall()]
        return transactions
    except Exception as e:
        print(f"Error al obtener transacciones: {e}")
        return []
    finally:
        conn.close()

def get_financial_summary(start_date_str: str = None, end_date_str: str = None) -> dict:
    """Calcula el resumen financiero (ingresos, gastos, balance) para un periodo."""
    conn = get_db_connection()
    if not conn: return {"total_income": 0, "total_expense": 0, "net_balance": 0, "error": "DB connection failed"}
    cursor = conn.cursor()

    params_income = []
    params_expense = []
    date_condition = ""

    parsed_start_date = parse_date_string(start_date_str)
    parsed_end_date = parse_date_string(end_date_str)

    if parsed_start_date and parsed_end_date:
        date_condition = "AND transaction_date BETWEEN ? AND ?"
        params_income.extend([parsed_start_date, parsed_end_date])
        params_expense.extend([parsed_start_date, parsed_end_date])
    elif parsed_start_date:
        date_condition = "AND transaction_date >= ?"
        params_income.append(parsed_start_date)
        params_expense.append(parsed_start_date)
    elif parsed_end_date:
        date_condition = "AND transaction_date <= ?"
        params_income.append(parsed_end_date)
        params_expense.append(parsed_end_date)

    try:
        # Total Ingresos
        cursor.execute(f"SELECT SUM(amount) FROM financial_transactions WHERE type = 'income' {date_condition}", tuple(params_income))
        total_income_row = cursor.fetchone()
        total_income = total_income_row[0] if total_income_row and total_income_row[0] is not None else 0.0

        # Total Gastos
        cursor.execute(f"SELECT SUM(amount) FROM financial_transactions WHERE type = 'expense' {date_condition}", tuple(params_expense))
        total_expense_row = cursor.fetchone()
        total_expense = total_expense_row[0] if total_expense_row and total_expense_row[0] is not None else 0.0
        
        net_balance = total_income - total_expense
        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_balance": net_balance,
            "period_start": format_date(parsed_start_date) if parsed_start_date else "Inicio",
            "period_end": format_date(parsed_end_date) if parsed_end_date else "Fin"
        }
    except Exception as e:
        print(f"Error al calcular resumen financiero: {e}")
        return {"total_income": 0, "total_expense": 0, "net_balance": 0, "error": str(e)}
    finally:
        conn.close()


# --- Funciones para Gastos Recurrentes ---

def _calculate_next_due_date(start_date: date, frequency: str, day_of_month: int = None, day_of_week: int = None) -> date:
    """Calcula la próxima fecha de vencimiento basada en la frecuencia."""
    current_date = start_date # Para el primer cálculo, usamos start_date como referencia
    if frequency == 'daily':
        return current_date + timedelta(days=1)
    elif frequency == 'weekly':
        next_date = current_date + timedelta(days= (day_of_week - current_date.weekday() + 7) % 7 )
        if next_date <= current_date: # Si ya pasó esta semana, a la siguiente
            next_date += timedelta(weeks=1)
        return next_date
    elif frequency == 'monthly':
        target_day = day_of_month if day_of_month else current_date.day
        # Ir al próximo mes
        next_month_date = current_date + relativedelta(months=1)
        # Intentar poner el día correcto en el próximo mes
        try:
            return next_month_date.replace(day=target_day)
        except ValueError: # Si el día es > días en ese mes (ej. 31 en Febrero)
            # Usar el último día del mes
            last_day_of_next_month = (next_month_date.replace(day=1) + relativedelta(months=1)) - timedelta(days=1)
            return last_day_of_next_month
    elif frequency == 'quarterly':
        return current_date + relativedelta(months=3)
    elif frequency == 'biannual':
        return current_date + relativedelta(months=6)
    elif frequency == 'annual':
        return current_date + relativedelta(years=1)
    return current_date # Fallback, debería ser manejado


def add_recurring_expense(
    description: str, default_amount: float, category: str,
    frequency: str, start_date_str: str,
    day_of_month_to_apply: int = None, # Para 'monthly'
    day_of_week_to_apply: int = None,  # Para 'weekly' (0=Mon, 6=Sun)
    end_date_str: str = None, is_active: bool = True,
    auto_apply: bool = False, notes: str = None
) -> dict | None:
    """Añade una definición de gasto recurrente."""
    # ... (validaciones similares a record_transaction para los campos obligatorios)
    description = clean_string_input(description)
    if not all([description, default_amount, category, frequency, start_date_str]):
        print("Error: Descripción, monto, categoría, frecuencia y fecha de inicio son obligatorios para gasto recurrente.")
        return None
    if default_amount <=0:
        print("Error: Monto por defecto debe ser positivo.")
        return None
    
    valid_frequencies = ['daily', 'weekly', 'monthly', 'quarterly', 'biannual', 'annual']
    if frequency not in valid_frequencies:
        print(f"Error: Frecuencia '{frequency}' no válida. Use una de: {', '.join(valid_frequencies)}")
        return None

    parsed_start_date = parse_date_string(start_date_str)
    if not parsed_start_date:
        print("Error: Formato de fecha de inicio inválido.")
        return None
    
    parsed_end_date = parse_date_string(end_date_str) if end_date_str else None
    if end_date_str and not parsed_end_date:
        print("Advertencia: Formato de fecha de fin inválido. Se guardará como NULL.")

    # Calcular la primera next_due_date. Si start_date es en el futuro, es start_date.
    # Si start_date es en el pasado o hoy, calculamos la siguiente a partir de hoy.
    today = date.today()
    initial_next_due = parsed_start_date
    if parsed_start_date <= today:
        initial_next_due = _calculate_next_due_date(today, frequency, day_of_month_to_apply, day_of_week_to_apply)
        # Si la start_date original es después de esta 'next_due' calculada a partir de hoy,
        # entonces la verdadera primera vez es la start_date
        if parsed_start_date > initial_next_due:
             initial_next_due = parsed_start_date

    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        sql = """INSERT INTO recurring_expenses (
                    description, default_amount, category, frequency, start_date,
                    day_of_month_to_apply, day_of_week_to_apply, next_due_date,
                    end_date, is_active, auto_apply, notes
                 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (
            description, default_amount, category, frequency, parsed_start_date,
            day_of_month_to_apply, day_of_week_to_apply, initial_next_due,
            parsed_end_date, 1 if is_active else 0, 1 if auto_apply else 0, notes
        )
        cursor.execute(sql, params)
        re_id = cursor.lastrowid
        conn.commit()
        print(f"Gasto recurrente '{description}' añadido con ID {re_id}.")
        return get_recurring_expense_by_id(re_id)
    except Exception as e:
        print(f"Error al añadir gasto recurrente: {e}")
        return None
    finally:
        conn.close()

def get_recurring_expense_by_id(re_id: int) -> dict | None:
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM recurring_expenses WHERE id = ?", (re_id,))
        re_expense = cursor.fetchone()
        return dict(re_expense) if re_expense else None
    finally:
        conn.close()

def get_all_recurring_expenses(active_only: bool = False) -> list[dict]:
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor()
    query = "SELECT * FROM recurring_expenses"
    params = []
    if active_only:
        query += " WHERE is_active = 1"
    query += " ORDER BY description"
    try:
        cursor.execute(query, tuple(params))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def update_recurring_expense(re_id: int, updates: dict) -> bool:
    # ... (similar a update_member_details, construir query SQL dinámica)
    # Importante: si se cambia la frecuencia o start_date, recalcular next_due_date
    # Esta función sería más compleja, la dejo como placeholder.
    print(f"Actualizar gasto recurrente {re_id} - No implementado completamente.")
    existing_re = get_recurring_expense_by_id(re_id)
    if not existing_re:
        print(f"Error: Gasto recurrente con ID {re_id} no encontrado.")
        return False
    
    fields_to_set = []
    params_sql = []
    recalculate_next_due = False

    # Campos permitidos para actualización
    allowed_fields = ['description', 'default_amount', 'category', 'frequency', 
                        'start_date', 'day_of_month_to_apply', 'day_of_week_to_apply',
                        'end_date', 'is_active', 'auto_apply', 'notes', 'next_due_date']

    for field, value in updates.items():
        if field in allowed_fields:
            if field in ['start_date', 'end_date', 'next_due_date'] and value: # Si es campo de fecha
                parsed_val = parse_date_string(str(value))
                if not parsed_val:
                    print(f"Advertencia: Formato de fecha inválido para '{field}'. No se actualizará.")
                    continue
                value = parsed_val
            
            fields_to_set.append(f"{field} = ?")
            params_sql.append(value)
            if field in ['frequency', 'start_date', 'day_of_month_to_apply', 'day_of_week_to_apply']:
                recalculate_next_due = True # Marcar para recalcular si cambian estos campos

    if not fields_to_set:
        print("No hay campos válidos para actualizar.")
        return True

    # Si se debe recalcular next_due_date y no se está estableciendo explícitamente
    if recalculate_next_due and 'next_due_date' not in updates:
        # Usar los valores existentes o los que se están actualizando para el cálculo
        freq = updates.get('frequency', existing_re['frequency'])
        start_dt = updates.get('start_date', parse_date_string(existing_re['start_date']))
        if isinstance(start_dt, str): start_dt = parse_date_string(start_dt) # Asegurar que es date

        day_month = updates.get('day_of_month_to_apply', existing_re.get('day_of_month_to_apply'))
        day_week = updates.get('day_of_week_to_apply', existing_re.get('day_of_week_to_apply'))
        
        # Aquí la lógica de cuándo empezar a recalcular es tricky.
        # Por simplicidad, si cambiaron datos de frecuencia, recalculamos desde hoy o la nueva start_date.
        reference_date_for_recalc = updates.get('start_date', parse_date_string(existing_re['start_date']))
        if isinstance(reference_date_for_recalc, str): reference_date_for_recalc = parse_date_string(reference_date_for_recalc)

        if reference_date_for_recalc <= date.today() or 'start_date' not in updates: # Si start_date no cambia y es pasado/hoy, o cambia y es pasado/hoy
            reference_date_for_recalc = date.today()

        new_next_due = _calculate_next_due_date(reference_date_for_recalc, freq, day_month, day_week)
        if start_dt > new_next_due: # Si la (nueva) fecha de inicio es posterior al cálculo, usar la fecha de inicio.
            new_next_due = start_dt
            
        fields_to_set.append("next_due_date = ?")
        params_sql.append(new_next_due)


    params_sql.append(re_id) # Para el WHERE
    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        sql_query = f"UPDATE recurring_expenses SET {', '.join(fields_to_set)} WHERE id = ?"
        cursor.execute(sql_query, tuple(params_sql))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Gasto recurrente ID {re_id} actualizado.")
            return True
        else:
            print(f"No se realizaron cambios en gasto recurrente ID {re_id}.")
            return True
    except Exception as e:
        print(f"Error al actualizar gasto recurrente: {e}")
        return False
    finally:
        conn.close()


def process_pending_recurring_expenses(user_id: int, process_date: date = None) -> int:
    """
    Busca gastos recurrentes activos cuya next_due_date ha llegado y los procesa:
    1. Crea una transacción en financial_transactions.
    2. Actualiza la next_due_date del gasto recurrente.
    Devuelve el número de gastos procesados.
    """
    if process_date is None:
        process_date = date.today()
    
    conn = get_db_connection()
    if not conn: return 0
    cursor = conn.cursor()
    
    processed_count = 0
    
    try:
        # Seleccionar gastos recurrentes activos, cuya next_due_date es hoy o antes,
        # y que no tengan fecha de fin o cuya fecha de fin no haya pasado.
        cursor.execute("""
            SELECT * FROM recurring_expenses
            WHERE is_active = 1
            AND next_due_date <= ?
            AND (end_date IS NULL OR end_date >= ?)
            """, (process_date, process_date))
        
        pending_expenses = cursor.fetchall()

        if not pending_expenses:
            print(f"No hay gastos recurrentes pendientes para procesar a fecha de {format_date(process_date)}.")
            return 0

        print(f"Encontrados {len(pending_expenses)} gastos recurrentes para procesar...")

        for re_dict in pending_expenses:
            re = dict(re_dict) # Convertir la Row a diccionario
            print(f"Procesando gasto recurrente ID {re['id']}: {re['description']}...")
            
            # 1. Crear la transacción en financial_transactions
            # La fecha de la transacción será la next_due_date original del gasto recurrente
            transaction_date_to_record = parse_date_string(re['next_due_date'])
            
            transaction_recorded = record_transaction(
                type_str='expense',
                description=f"(Recurrente) {re['description']}",
                amount=re['default_amount'],
                transaction_date_str=transaction_date_to_record.isoformat(),
                category=re['category'],
                user_id=user_id, # Usuario que ejecuta el proceso
                reference_id=f"RE-{re['id']}-{transaction_date_to_record.strftime('%Y%m%d')}"
            )

            if transaction_recorded:
                # 2. Calcular y actualizar la next_due_date del gasto recurrente
                # La nueva next_due_date se calcula a partir de la ANTERIOR next_due_date, NO de process_date
                current_next_due = parse_date_string(re['next_due_date'])
                new_next_due_date = _calculate_next_due_date(
                    current_next_due,
                    re['frequency'],
                    re.get('day_of_month_to_apply'),
                    re.get('day_of_week_to_apply')
                )

                # Si la nueva next_due_date supera la end_date (si existe), desactivar el gasto recurrente
                # o simplemente no actualizar la next_due_date y dejar que no se coja la próxima vez.
                # Por ahora, solo actualizamos. El filtro SELECT ya se encarga de end_date.
                
                cursor.execute(
                    "UPDATE recurring_expenses SET next_due_date = ? WHERE id = ?",
                    (new_next_due_date, re['id'])
                )
                conn.commit() # Commit por cada gasto procesado correctamente
                print(f"  - Gasto registrado. Próximo vencimiento para ID {re['id']}: {format_date(new_next_due_date)}")
                processed_count += 1
            else:
                print(f"  - ERROR al registrar la transacción para el gasto recurrente ID {re['id']}. Se omitirá.")
                # Aquí podrías registrar este error en algún log del sistema.

        print(f"Total de gastos recurrentes procesados: {processed_count}")
        return processed_count

    except Exception as e:
        print(f"Error durante el procesamiento de gastos recurrentes: {e}")
        conn.rollback() # Revertir si hubo un error en el bucle o en las queries principales
        return 0
    finally:
        conn.close()

# --- Simulación para la prueba ---
def get_current_user_id_for_test() -> int:
    # En una app real, obtendrías el ID del usuario logueado.
    # Para pruebas, devolvemos el ID del superuser (asumiendo que es 1).
    conn = get_db_connection()
    if not conn: return 1 # Fallback
    cursor = conn.cursor()
    try:
        from config import SUPERUSER_USERNAME
        cursor.execute("SELECT id FROM users WHERE username = ?", (SUPERUSER_USERNAME,))
        user = cursor.fetchone()
        return user['id'] if user else 1
    except:
        return 1 # Fallback si algo falla
    finally:
        if conn: conn.close()


if __name__ == "__main__":
    print("--- Probando el módulo finances.py ---")
    # Asumir que database.py ya se ejecutó (incluyendo la tabla recurring_expenses)
    # y auth.py para tener usuarios (el superuser_id se usa en process_recurring_expenses).
    # Para probar esto aislado, necesitamos un user_id.
    test_user_id = get_current_user_id_for_test() 
    print(f"ID de usuario para pruebas: {test_user_id}")


    # --- Registrar Transacciones de Prueba ---
    print("\n[TEST] Registrando transacciones...")
    ingreso1 = record_transaction('income', "Cuota mensual Juan Pérez", 35.00, category="Cuota Mensual", payment_method="cash", user_id=test_user_id)
    gasto1 = record_transaction('expense', "Compra de material limpieza", 50.25, category="Limpieza", payment_method="card", user_id=test_user_id)
    ingreso2 = record_transaction('income', "Venta de botella de agua", 1.50, category="Venta de Productos", user_id=test_user_id)


    # --- Obtener transacciones ---
    print("\n[TEST] Últimas transacciones:")
    latest_trans = get_transactions(limit=5)
    if latest_trans:
        for t in latest_trans:
            print(f"  - {format_date(parse_date_string(t['transaction_date']))} | {t['type'].capitalize():<7} | {t['description']:<30} | {format_currency(t['amount'], CURRENCY_SYMBOL)}")
    else:
        print("  No hay transacciones o error.")


    # --- Resumen Financiero (Total) ---
    print("\n[TEST] Resumen Financiero (Total):")
    summary_total = get_financial_summary()
    if "error" not in summary_total:
        print(f"  Ingresos: {format_currency(summary_total['total_income'], CURRENCY_SYMBOL)}")
        print(f"  Gastos:   {format_currency(summary_total['total_expense'], CURRENCY_SYMBOL)}")
        print(f"  Balance:  {format_currency(summary_total['net_balance'], CURRENCY_SYMBOL)}")
    else:
        print(f"  Error: {summary_total['error']}")
        
    # --- Resumen Financiero (Periodo específico) ---
    # Crear algunas transacciones más para probar el filtro de fecha
    record_transaction('expense', "Factura Luz Mes Pasado", 120.00, transaction_date_str=(date.today() - timedelta(days=35)).isoformat(), category="Suministros", user_id=test_user_id)
    record_transaction('income', "Cuota Ana Mes Pasado", 35.00, transaction_date_str=(date.today() - timedelta(days=40)).isoformat(), category="Cuota Mensual", user_id=test_user_id)
    
    start_period = (date.today() - timedelta(days=60)).isoformat()
    end_period = (date.today() - timedelta(days=30)).isoformat()
    print(f"\n[TEST] Resumen Financiero para periodo {format_date(parse_date_string(start_period))} - {format_date(parse_date_string(end_period))}:")
    summary_period = get_financial_summary(start_date_str=start_period, end_date_str=end_period)
    if "error" not in summary_period:
        print(f"  Ingresos: {format_currency(summary_period['total_income'], CURRENCY_SYMBOL)}")
        print(f"  Gastos:   {format_currency(summary_period['total_expense'], CURRENCY_SYMBOL)}")
        print(f"  Balance:  {format_currency(summary_period['net_balance'], CURRENCY_SYMBOL)}")
    else:
        print(f"  Error: {summary_period['error']}")


    # --- Gastos Recurrentes ---
    print("\n[TEST] Gestión de Gastos Recurrentes...")
    
    # Añadir gasto recurrente mensual para el día 5, empezando el mes pasado
    alquiler_start_date = (date.today().replace(day=1) - relativedelta(months=1)).isoformat()
    print(f"Añadiendo 'Alquiler Local' recurrente (inicia: {alquiler_start_date}, día 5 de mes)")
    rec_alquiler = add_recurring_expense(
        "Alquiler Local Gimnasio", 500.00, "Alquiler Local", "monthly",
        alquiler_start_date, day_of_month_to_apply=5
    )
    if rec_alquiler:
         print(f"  - Gasto 'Alquiler' creado. Próximo vencimiento: {format_date(parse_date_string(rec_alquiler['next_due_date']))}")


    # Añadir gasto recurrente semanal para limpieza los miércoles (day_of_week=2), empezando hace 2 semanas
    limpieza_start_date = (date.today() - timedelta(weeks=2)).isoformat()
    rec_limpieza = add_recurring_expense(
        "Servicio Limpieza Semanal", 60.00, "Limpieza", "weekly",
        limpieza_start_date, day_of_week_to_apply=2 # Miércoles
    )
    if rec_limpieza:
         print(f"  - Gasto 'Limpieza Semanal' creado. Próximo vencimiento: {format_date(parse_date_string(rec_limpieza['next_due_date']))}")

    print("\n[TEST] Lista de todos los gastos recurrentes:")
    all_recs = get_all_recurring_expenses()
    if all_recs:
        for r_exp in all_recs:
            print(f"  - ID: {r_exp['id']}, {r_exp['description']}, {format_currency(r_exp['default_amount'])}, Next: {format_date(parse_date_string(r_exp['next_due_date']))}")
    
    print("\n[TEST] Procesando gastos recurrentes pendientes (para hoy):")
    # Si ejecutas esto varias veces en el mismo día, solo debería procesar una vez.
    # Para volver a probar, necesitarías manipular las 'next_due_date' en la BD o cambiar la fecha del sistema (no recomendado).
    # O, modificar el test para pasar una 'process_date' específica.
    
    # Vamos a probar con una fecha específica para forzar el procesamiento si el de hoy ya se hizo
    # Supongamos que estamos a principios de mes y queremos procesar los del día 5
    target_process_date_str = date.today().replace(day=6).isoformat() # Ej. dia 6 para pillar los del 5
    # O si es para el alquiler mensual que empieza el mes pasado día 5:
    # target_process_date_str = (date.today().replace(day=5)).isoformat()
    
    # Comentar la linea anterior y descomentar la siguiente para usar la fecha de hoy
    target_process_date_str = date.today().isoformat()

    print(f"Intentando procesar para fecha: {format_date(parse_date_string(target_process_date_str))}")
    num_processed = process_pending_recurring_expenses(user_id=test_user_id, process_date=parse_date_string(target_process_date_str))
    print(f"Número de gastos recurrentes procesados ahora: {num_processed}")

    print("\n[TEST] Volviendo a procesar para la misma fecha (no deberían procesarse de nuevo):")
    num_processed_again = process_pending_recurring_expenses(user_id=test_user_id, process_date=parse_date_string(target_process_date_str))
    print(f"Número de gastos recurrentes procesados en el segundo intento: {num_processed_again}")


    print("\n[TEST] Verificando transacciones después de procesar gastos recurrentes:")
    latest_trans_after_re = get_transactions(limit=10)
    if latest_trans_after_re:
        for t in latest_trans_after_re:
            if "(Recurrente)" in t['description']: # Destacar los recurrentes
                print(f"  -> {format_date(parse_date_string(t['transaction_date']))} | {t['type'].capitalize():<7} | {t['description']:<30} | {format_currency(t['amount'], CURRENCY_SYMBOL)}")
            else:
                print(f"     {format_date(parse_date_string(t['transaction_date']))} | {t['type'].capitalize():<7} | {t['description']:<30} | {format_currency(t['amount'], CURRENCY_SYMBOL)}")


    print("\n--- Fin de pruebas de finances.py ---")