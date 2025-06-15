# gimnasio_mgmt_gui/core_logic/auth.py
# Lógica de autenticación, gestión de usuarios del sistema y permisos.

import sqlite3
from datetime import datetime, timedelta
import os # <-- CORRECCIÓN 1: Importar el módulo os

# Importaciones del mismo paquete (core_logic) o de la raíz del proyecto
try:
    from .database import get_db_connection
    from .utils import hash_secure_password, is_valid_system_username, check_password_strength
    from config import (
        SUPERUSER_INIT_USERNAME, SUPERUSER_INIT_PASSWORD, ROLE_SUPERUSER,
        ALL_DEFINED_ROLES, MAX_FAILED_LOGIN_ATTEMPTS_BEFORE_LOCKOUT,
        ACCOUNT_LOCKOUT_DURATION_SECONDS,
        # --- CORRECCIÓN 2: Asegurarse de importar TODOS los roles definidos en config.py ---
        ROLE_SYSTEM_ADMIN, ROLE_DATA_MANAGER, ROLE_STAFF_MEMBER
    )
except ImportError as e:
    print(f"ERROR CRÍTICO (auth.py): Fallo en importaciones esenciales. Error: {e}")
    raise


def create_system_user(
    username: str,
    password: str,
    role: str,
    is_active: bool = True,
    *,
    allow_superuser_creation: bool = False,
) -> tuple[bool, str]:
    """Crea un nuevo usuario del sistema.

    Parameters
    ----------
    username : str
        Nombre de usuario para la nueva cuenta.
    password : str
        Contraseña en texto plano que será hasheada.
    role : str
        Rol que se asignará al usuario.
    is_active : bool, optional
        Indica si la cuenta estará activa tras ser creada.
    allow_superuser_creation : bool, optional
        Permite crear la cuenta del superusuario inicial.  ``False`` por
        defecto para evitar que desde la interfaz se creen nuevos usuarios
        con el nombre o rol reservado para ``root``.

    Returns
    -------
    tuple
        ``(exito, mensaje_o_id_usuario)``
    """

    username_clean = username.strip().lower()

    if not allow_superuser_creation:
        if username_clean == SUPERUSER_INIT_USERNAME.lower():
            return False, "Nombre de usuario reservado para el superadministrador."
        if role == ROLE_SUPERUSER:
            return False, "No se puede asignar el rol de Superadministrador."

    if not is_valid_system_username(username):
        return False, "Formato de nombre de usuario no válido."
    
    is_strong_enough, strength_msg = check_password_strength(password)
    if not is_strong_enough:
        return False, strength_msg

    if role not in ALL_DEFINED_ROLES:
        return False, f"Rol '{role}' no es un rol válido del sistema."

    conn = get_db_connection()
    if not conn:
        return False, "No se pudo conectar a la base de datos."

    try:
        with conn: 
            hashed_pwd = hash_secure_password(password)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO system_users (username, password_hash, role, is_active, created_at, updated_at)
                   VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                (username.strip().lower(), hashed_pwd, role, 1 if is_active else 0)
            )
            user_id = cursor.lastrowid
            return True, str(user_id) 
    except sqlite3.IntegrityError:
        return False, f"El nombre de usuario '{username.strip().lower()}' ya existe."
    except sqlite3.Error as e:
        print(f"ERROR (auth.py - create_system_user): {e}")
        return False, "Error de base de datos al crear usuario."


def initialize_superuser_account():
    """
    Verifica y crea la cuenta del superusuario inicial si no existe.
    """
    # (Resto del código de initialize_superuser_account sin cambios...)
    conn = get_db_connection()
    if not conn:
        print("ERROR CRÍTICO (auth.py - initialize_superuser): No hay conexión a BD.")
        return

    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM system_users WHERE username = ?", (SUPERUSER_INIT_USERNAME.lower(),))
            if not cursor.fetchone():
                print(f"INFO (auth.py): Creando cuenta de superusuario inicial '{SUPERUSER_INIT_USERNAME}'...")
                success, msg_or_id = create_system_user(
                    SUPERUSER_INIT_USERNAME,
                    SUPERUSER_INIT_PASSWORD,
                    ROLE_SUPERUSER,  # Rol del superusuario
                    allow_superuser_creation=True,
                )
                if success:
                    print(f"INFO (auth.py): Superusuario '{SUPERUSER_INIT_USERNAME}' creado con ID: {msg_or_id}.")
                else:
                    print(f"ERROR CRÍTICO (auth.py): Falló la creación del superusuario. Razón: {msg_or_id}")
    except sqlite3.Error as e:
        print(f"ERROR (auth.py - initialize_superuser): Error de BD. {e}")

def attempt_user_login(username: str, password: str) -> dict | None:
    """
    Intenta autenticar un usuario.
    Devuelve dict con info del usuario o dict con 'error'.
    """
    # (Resto del código de attempt_user_login sin cambios significativos aquí...)
    # (Revisar si las importaciones de config de MAX_FAILED... y ACCOUNT_LOCKOUT... son correctas arriba)
    if not username or not password:
        return None

    username_clean = username.strip().lower()
    conn = get_db_connection()
    if not conn:
        return None # O manejar de otra forma

    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, username, role, password_hash, is_active,
                      failed_login_attempts, account_locked_until
               FROM system_users WHERE username = ?""",
            (username_clean,)
        )
        user_record = cursor.fetchone()

        if not user_record:
            return None

        if user_record["account_locked_until"]:
            lockout_time = datetime.fromisoformat(user_record["account_locked_until"])
            if datetime.now() < lockout_time:
                return {"error": "account_locked", "unlock_time": user_record["account_locked_until"]}
            else:
                _reset_failed_login_attempts(conn, username_clean)
                user_record = cursor.execute(
                    "SELECT * FROM system_users WHERE username = ?", (username_clean,)).fetchone()

        if user_record["password_hash"] == hash_secure_password(password):
            if not user_record["is_active"]:
                return {"error": "account_inactive"}

            with conn:
                cursor.execute(
                    """UPDATE system_users
                       SET failed_login_attempts = 0, account_locked_until = NULL, last_login_at = CURRENT_TIMESTAMP
                       WHERE username = ?""",
                    (username_clean,)
                )
            return {
                "id": user_record["id"],
                "username": user_record["username"],
                "role": user_record["role"],
                "is_active": bool(user_record["is_active"])
            }
        else:
            _handle_failed_login_attempt(conn, username_clean, user_record["failed_login_attempts"])
            return None
            
    except sqlite3.Error as e:
        print(f"ERROR (auth.py - attempt_user_login): Error de BD. {e}")
        return None # Podríamos devolver un dict de error también
    finally:
        if conn:
            conn.close() # Cerrar la conexión obtenida aquí

# (Las funciones _handle_failed_login_attempt y _reset_failed_login_attempts permanecen igual)
def _handle_failed_login_attempt(conn: sqlite3.Connection, username: str, current_attempts: int):
    new_attempts = current_attempts + 1
    lock_until_timestamp = None

    if new_attempts >= MAX_FAILED_LOGIN_ATTEMPTS_BEFORE_LOCKOUT:
        lock_duration = timedelta(seconds=ACCOUNT_LOCKOUT_DURATION_SECONDS)
        lock_until_time = datetime.now() + lock_duration
        lock_until_timestamp = lock_until_time.isoformat()
        print(f"WARN (auth.py): Cuenta '{username}' bloqueada por {MAX_FAILED_LOGIN_ATTEMPTS_BEFORE_LOCKOUT} intentos fallidos. Bloqueada hasta {lock_until_timestamp}.")

    try:
        with conn: 
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE system_users SET failed_login_attempts = ?, account_locked_until = ? WHERE username = ?",
                (new_attempts, lock_until_timestamp, username)
            )
    except sqlite3.Error as e:
        print(f"ERROR (auth.py - _handle_failed_login_attempt): Error de BD. {e}")

def _reset_failed_login_attempts(conn: sqlite3.Connection, username: str):
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE system_users SET failed_login_attempts = 0, account_locked_until = NULL WHERE username = ?",
                (username,)
            )
    except sqlite3.Error as e:
        print(f"ERROR (auth.py - _reset_failed_login_attempts): Error de BD. {e}")


def get_system_user_by_username(username: str) -> dict | None:
    # (Sin cambios, pero asegurarse que conn se cierra)
    conn = get_db_connection()
    if not conn: return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, role, is_active, last_login_at, created_at FROM system_users WHERE username = ?",
            (username.strip().lower(),)
        )
        user_data = cursor.fetchone()
        return dict(user_data) if user_data else None
    except sqlite3.Error as e:
        print(f"ERROR (auth.py - get_system_user_by_username): {e}")
        return None
    finally:
        if conn: conn.close()

def get_all_system_users(exclude_superuser: bool = False) -> list[dict]:
    # (Sin cambios, pero asegurarse que conn se cierra)
    conn = get_db_connection()
    if not conn: return []
    users_list = []
    try:
        cursor = conn.cursor()
        query = "SELECT id, username, role, is_active, last_login_at FROM system_users ORDER BY username"
        params = ()
        if exclude_superuser:
            query = "SELECT id, username, role, is_active, last_login_at FROM system_users WHERE username != ? ORDER BY username"
            params = (SUPERUSER_INIT_USERNAME.lower(),) # Comparar con el username del superuser
        
        cursor.execute(query, params)
        for row in cursor.fetchall():
            users_list.append(dict(row))
        return users_list
    except sqlite3.Error as e:
        print(f"ERROR (auth.py - get_all_system_users): {e}")
        return []
    finally:
        if conn: conn.close()


def update_user_password(username: str, new_password: str) -> tuple[bool, str]:
    # (Sin cambios, pero asegurarse que conn se cierra)
    is_strong_enough, strength_msg = check_password_strength(new_password)
    if not is_strong_enough:
        return False, strength_msg

    conn = get_db_connection()
    if not conn: return False, "Error de conexión a BD."
    try:
        with conn:
            cursor = conn.cursor()
            hashed_pwd = hash_secure_password(new_password)
            cursor.execute(
                """UPDATE system_users
                   SET password_hash = ?, updated_at = CURRENT_TIMESTAMP,
                       failed_login_attempts = 0, account_locked_until = NULL
                   WHERE username = ?""",
                (hashed_pwd, username.strip().lower())
            )
            if cursor.rowcount == 0:
                return False, "Usuario no encontrado."
            return True, "Contraseña actualizada exitosamente."
    except sqlite3.Error as e:
        print(f"ERROR (auth.py - update_user_password): {e}")
        return False, "Error de base de datos al actualizar contraseña."
    finally: # Asegurar que la conexión se cierre si se abrió en esta función
        if conn: conn.close()


def update_user_role(username: str, new_role: str, current_admin_role: str) -> tuple[bool, str]:
    # (Sin cambios, pero asegurarse que conn se cierra)
    username_clean = username.strip().lower()
    if new_role not in ALL_DEFINED_ROLES:
        return False, f"Rol '{new_role}' no es válido."

    if username_clean == SUPERUSER_INIT_USERNAME.lower() and current_admin_role != ROLE_SUPERUSER:
        return False, "Solo un Superadministrador puede modificar esta cuenta."
    if new_role == ROLE_SUPERUSER:
        if username_clean != SUPERUSER_INIT_USERNAME.lower():
            return False, "No se pueden crear nuevos Superadministradores."
        if current_admin_role != ROLE_SUPERUSER:
            return False, "Solo un Superadministrador puede modificar esta cuenta."

    conn = get_db_connection()
    if not conn: return False, "Error de conexión a BD."
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE system_users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?",
                (new_role, username_clean)
            )
            if cursor.rowcount == 0:
                return False, "Usuario no encontrado."
            return True, f"Rol de '{username_clean}' actualizado a '{new_role}'."
    except sqlite3.Error as e:
        print(f"ERROR (auth.py - update_user_role): {e}")
        return False, "Error de base de datos al actualizar rol."
    finally:
        if conn: conn.close()

def set_user_activation_status(username: str, is_active: bool, current_admin_role: str) -> tuple[bool, str]:
    # (Sin cambios, pero asegurarse que conn se cierra)
    username_clean = username.strip().lower()
    # Aquí, en lugar de current_admin_role, podríamos simplemente proteger al superusuario inicial.
    if username_clean == SUPERUSER_INIT_USERNAME.lower() and not is_active:
        return False, "La cuenta del Superadministrador inicial no puede ser desactivada."

    conn = get_db_connection()
    if not conn: return False, "Error de conexión a BD."
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE system_users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE username = ?",
                (1 if is_active else 0, username_clean)
            )
            if cursor.rowcount == 0:
                return False, "Usuario no encontrado."
            action = "activada" if is_active else "desactivada"
            return True, f"Cuenta '{username_clean}' ha sido {action}."
    except sqlite3.Error as e:
        print(f"ERROR (auth.py - set_user_activation_status): {e}")
        return False, f"Error de base de datos al cambiar estado de activación."
    finally:
        if conn: conn.close()


def delete_system_user(username_to_delete: str, current_admin_username: str, current_admin_role: str) -> tuple[bool, str]:
    # (Sin cambios, pero asegurarse que conn se cierra)
    username_clean_delete = username_to_delete.strip().lower()
    username_clean_admin = current_admin_username.strip().lower()

    if username_clean_delete == SUPERUSER_INIT_USERNAME.lower():
        return False, "La cuenta del Superadministrador no puede ser eliminada."
    if username_clean_delete == username_clean_admin:
        return False, "No puede eliminarse a sí mismo."
    
    conn = get_db_connection()
    if not conn: return False, "Error de conexión a BD."
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM system_users WHERE username = ?", (username_clean_delete,))
            if cursor.rowcount == 0:
                return False, "Usuario no encontrado para eliminar."
            return True, f"Usuario '{username_clean_delete}' eliminado exitosamente."
    except sqlite3.Error as e:
        print(f"ERROR (auth.py - delete_system_user): {e}")
        return False, "Error de base de datos al eliminar usuario."
    finally:
        if conn: conn.close()


def check_user_permission(user_role: str | None, required_roles: list[str] | str) -> bool:
    # (Sin cambios...)
    if not user_role:
        return False 
    if user_role == ROLE_SUPERUSER:
        return True 

    if isinstance(required_roles, str):
        required_roles = [required_roles] 
    
    return user_role in required_roles


# --- Script de autocomprobación ---
if __name__ == "__main__":
    # --- CORRECCIÓN 1 (aquí): No es necesario llamar a os.path.basename si usamos __name__
    print(f"--- {__name__} (Módulo auth.py) Self-Check ---")
    
    print("\n1. Inicializando Superusuario (si no existe)...")
    initialize_superuser_account()

    print("\n2. Probando Login del Superusuario...")
    su_details = attempt_user_login(SUPERUSER_INIT_USERNAME, SUPERUSER_INIT_PASSWORD)
    SUPERUSER_ROLE_FROM_LOGIN = None # Inicializar
    if su_details and "error" not in su_details:
        print(f"  Login Superusuario EXITO. Rol: {su_details.get('role')}")
        SUPERUSER_ROLE_FROM_LOGIN = su_details.get('role')
    else:
        print(f"  Login Superusuario FALLIDO. Detalles: {su_details}")

    print("\n3. Creando Usuario de Prueba 'stafftest' con rol Staff...")
    # --- CORRECCIÓN 3: Usar las constantes de rol importadas ---
    success_create, msg_create = create_system_user("stafftest", "TestPass123!", ROLE_STAFF_MEMBER)
    if success_create:
        print(f"  Creación de 'stafftest' EXITO. ID: {msg_create}")
    else:
        print(f"  Creación de 'stafftest' FALLIDO. Razón: {msg_create}")

    print("\n4. Probando Login de 'stafftest'...")
    staff_details = attempt_user_login("stafftest", "TestPass123!")
    if staff_details and "error" not in staff_details:
        print(f"  Login 'stafftest' EXITO. Rol: {staff_details.get('role')}")
    else:
        print(f"  Login 'stafftest' FALLIDO. Detalles: {staff_details}")
    
    # ... (resto de las pruebas pueden seguir aquí, usando las constantes de rol correctas) ...

    # Ejemplo de una prueba que usaba los roles incorrectos, ahora corregida:
    if SUPERUSER_ROLE_FROM_LOGIN == ROLE_SUPERUSER:
        print(f"\n7. Superusuario cambiando rol de 'stafftest' a '{ROLE_DATA_MANAGER}'...")
        success_role, msg_role = update_user_role("stafftest", ROLE_DATA_MANAGER, SUPERUSER_ROLE_FROM_LOGIN) # Usar la constante correcta
        print(f"  Cambio de rol: {success_role} - {msg_role}")
        updated_staff = get_system_user_by_username("stafftest")
        if updated_staff: print(f"    Nuevo rol de 'stafftest': {updated_staff.get('role')}")

    print("\n10. Verificación de Permisos...")
    # --- CORRECCIÓN 4: Usar las constantes de rol correctas en las pruebas de check_user_permission ---
    print(f"  ¿'{ROLE_STAFF_MEMBER}' tiene permiso para '{[ROLE_DATA_MANAGER]}'? {check_user_permission(ROLE_STAFF_MEMBER, [ROLE_DATA_MANAGER])}")
    print(f"  ¿'{ROLE_DATA_MANAGER}' tiene permiso para '{[ROLE_DATA_MANAGER]}'? {check_user_permission(ROLE_DATA_MANAGER, [ROLE_DATA_MANAGER])}")
    print(f"  ¿'{ROLE_SUPERUSER}' tiene permiso para '{[ROLE_STAFF_MEMBER]}'? {check_user_permission(ROLE_SUPERUSER, [ROLE_STAFF_MEMBER])}")
    
    print(f"\n--- Fin de pruebas de {__name__} (auth.py) ---")