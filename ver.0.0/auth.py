# auth.py
import sqlite3
from database import get_db_connection # Para interactuar con la BD
from utils import hash_password      # Para hashear contraseñas
from config import (                 # Configuraciones y roles
    SUPERUSER_USERNAME,
    SUPERUSER_PASSWORD,
    SUPERUSER_EMAIL, 
    ROLE_SUPERUSER,
    ROLE_PROGRAM_ADMIN,
    ROLE_DATA_ADMIN,
    ROLE_STAFF,
    ALL_ROLES,
    MAX_LOGIN_ATTEMPTS # Si queremos implementar bloqueo de cuenta (no en esta versión)
)

# Podríamos implementar un seguimiento de intentos de login fallidos aquí si fuera necesario
# failed_login_attempts = {} # Ejemplo: {username: (attempts, last_attempt_time)}

def create_user(username: str, password: str, role: str, email: str = None, is_active: bool = True) -> bool:
    """
    Crea un nuevo usuario en la base de datos.
    Devuelve True si el usuario se creó con éxito, False en caso contrario (ej. usuario ya existe).
    """
    if not username or not password or not role:
        print("Error: Nombre de usuario, contraseña y rol son obligatorios.")
        return False

    if role not in ALL_ROLES:
        print(f"Error: Rol '{role}' no es válido. Roles válidos: {', '.join(ALL_ROLES)}")
        return False

    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()

    try:
        hashed_pwd = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, email, is_active) VALUES (?, ?, ?, ?, ?)",
            (username.strip(), hashed_pwd, role, email.strip() if email else None, 1 if is_active else 0)
        )
        conn.commit()
        print(f"Usuario '{username}' creado con rol '{role}'.")
        return True
    except sqlite3.IntegrityError as e: # Ocurre si el username o email (si es UNIQUE) ya existe
        if "UNIQUE constraint failed: users.username" in str(e):
            print(f"Error: El nombre de usuario '{username}' ya existe.")
        elif email and "UNIQUE constraint failed: users.email" in str(e):
             print(f"Error: El email '{email}' ya está registrado.")
        else:
            print(f"Error de base de datos al crear usuario: {e}")
        return False
    except Exception as e:
        print(f"Error inesperado al crear usuario: {e}")
        return False
    finally:
        conn.close()

def initialize_superuser():
    """
    Crea el superusuario inicial definido en config.py si no existe.
    Esto se llama una vez al iniciar la aplicación.
    """
    conn = get_db_connection()
    if not conn: return
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE username = ?", (SUPERUSER_USERNAME,))
        if not cursor.fetchone():
            print(f"Superusuario '{SUPERUSER_USERNAME}' no encontrado. Creándolo...")
            if create_user(SUPERUSER_USERNAME, SUPERUSER_PASSWORD, ROLE_SUPERUSER, SUPERUSER_EMAIL):
                print(f"Superusuario '{SUPERUSER_USERNAME}' creado exitosamente.")
            else:
                print(f"Error al crear el superusuario '{SUPERUSER_USERNAME}'. Verifica los logs.")
        # else:
        #     print(f"Superusuario '{SUPERUSER_USERNAME}' ya existe.")
    except Exception as e:
        print(f"Error al inicializar superusuario: {e}")
    finally:
        conn.close()

def login_user(username: str, password: str) -> dict | None:
    """
    Verifica las credenciales del usuario contra la base de datos.
    Devuelve un diccionario con los datos del usuario (id, username, role) si es exitoso,
    o None si el login falla o el usuario está inactivo.
    """
    if not username or not password:
        return None

    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id, username, role, password_hash, is_active FROM users WHERE username = ?",
            (username.strip(),)
        )
        user_data = cursor.fetchone()

        if user_data:
            if not user_data['is_active']:
                print(f"Login fallido: El usuario '{username}' está inactivo.")
                return None
            
            # Verificar la contraseña hasheada
            # En un sistema real, no se compara el hash directamente si la BD devuelve None o algo inesperado.
            # Aquí hash_password maneja None para password.
            if user_data['password_hash'] == hash_password(password):
                # print(f"Login exitoso para '{username}'.") # Descomentar para debugging CLI
                return {"id": user_data['id'], "username": user_data['username'], "role": user_data['role']}
            else:
                # print(f"Contraseña incorrecta para '{username}'.") # Descomentar para debugging CLI
                return None
        else:
            # print(f"Usuario '{username}' no encontrado.") # Descomentar para debugging CLI
            return None
    except Exception as e:
        print(f"Error durante el login: {e}")
        return None
    finally:
        conn.close()

def get_user_by_username(username: str) -> dict | None:
    """Obtiene los datos de un usuario por su nombre de usuario."""
    conn = get_db_connection()
    if not conn: return None
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, username, email, role, is_active, created_at, updated_at FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def get_all_users() -> list[dict]:
    """Devuelve una lista de todos los usuarios (excepto quizás el superusuario si se desea filtrar)."""
    conn = get_db_connection()
    if not conn: return []
    cursor = conn.cursor()
    try:
        # Podríamos excluir al superusuario de esta lista si es para gestión por un program_admin
        # cursor.execute("SELECT id, username, email, role, is_active FROM users WHERE username != ?", (SUPERUSER_USERNAME,))
        cursor.execute("SELECT id, username, email, role, is_active FROM users ORDER BY username")
        users = [dict(row) for row in cursor.fetchall()]
        return users
    except Exception as e:
        print(f"Error al obtener todos los usuarios: {e}")
        return []
    finally:
        conn.close()

def update_user_details(current_username: str, new_email: str = None, new_password: str = None) -> bool:
    """
    Permite a un usuario actualizar su propio email o contraseña.
    """
    user_to_update = get_user_by_username(current_username)
    if not user_to_update:
        print(f"Error: Usuario '{current_username}' no encontrado para actualizar.")
        return False

    updates = []
    params = []

    if new_email is not None and new_email.strip() != user_to_update.get('email'):
        updates.append("email = ?")
        params.append(new_email.strip())
    
    if new_password: # Si se provee nueva contraseña
        updates.append("password_hash = ?")
        params.append(hash_password(new_password))

    if not updates:
        print("No hay cambios para actualizar.")
        return True # No es un error, simplemente no hubo nada que cambiar

    params.append(current_username) # Para la cláusula WHERE

    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        sql_query = f"UPDATE users SET {', '.join(updates)} WHERE username = ?"
        cursor.execute(sql_query, tuple(params))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Detalles del usuario '{current_username}' actualizados.")
            return True
        else:
            # Esto no debería pasar si el usuario fue encontrado inicialmente
            print(f"No se pudo actualizar el usuario '{current_username}'.")
            return False
    except sqlite3.IntegrityError as e:
        if new_email and "UNIQUE constraint failed: users.email" in str(e):
            print(f"Error: El nuevo email '{new_email}' ya está en uso.")
        else:
            print(f"Error de base de datos al actualizar usuario: {e}")
        return False
    except Exception as e:
        print(f"Error inesperado al actualizar usuario: {e}")
        return False
    finally:
        conn.close()

def update_user_role_by_admin(username_to_update: str, new_role: str, performing_user_role: str) -> bool:
    """
    Actualiza el rol de un usuario. Realizado por un admin.
    Un PROGRAM_ADMIN no puede cambiar el rol del SUPERUSER ni asignarse a sí mismo como SUPERUSER.
    """
    if username_to_update == SUPERUSER_USERNAME and performing_user_role != ROLE_SUPERUSER:
        print(f"Error: Solo el superusuario puede modificar al usuario '{SUPERUSER_USERNAME}'.")
        return False
    if new_role == ROLE_SUPERUSER and performing_user_role != ROLE_SUPERUSER:
        print("Error: No se puede asignar el rol de superusuario.")
        return False
    if new_role not in ALL_ROLES:
        print(f"Error: Rol '{new_role}' no es válido.")
        return False
    
    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET role = ? WHERE username = ?", (new_role, username_to_update))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Rol del usuario '{username_to_update}' actualizado a '{new_role}'.")
            return True
        else:
            print(f"Usuario '{username_to_update}' no encontrado o el rol ya era ese.")
            return False # Podría ser True si no es un error que no haya cambio
    except Exception as e:
        print(f"Error al actualizar rol de usuario: {e}")
        return False
    finally:
        conn.close()

def set_user_active_status(username_to_update: str, is_active: bool) -> bool:
    """Activa o desactiva un usuario."""
    if username_to_update == SUPERUSER_USERNAME and not is_active:
        print("Error: No se puede desactivar al superusuario.")
        return False

    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        status_int = 1 if is_active else 0
        cursor.execute("UPDATE users SET is_active = ? WHERE username = ?", (status_int, username_to_update))
        conn.commit()
        if cursor.rowcount > 0:
            action = "activado" if is_active else "desactivado"
            print(f"Usuario '{username_to_update}' ha sido {action}.")
            return True
        else:
            print(f"Usuario '{username_to_update}' no encontrado.")
            return False
    except Exception as e:
        print(f"Error al cambiar estado de activación del usuario: {e}")
        return False
    finally:
        conn.close()

def delete_user(username_to_delete: str, performing_user_username: str) -> bool:
    """
    Elimina un usuario de la base de datos.
    No se puede eliminar al superusuario ni al usuario que realiza la acción.
    """
    if username_to_delete == SUPERUSER_USERNAME:
        print("Error: El superusuario no puede ser eliminado.")
        return False
    if username_to_delete == performing_user_username:
        print("Error: No puedes eliminarte a ti mismo.")
        return False

    conn = get_db_connection()
    if not conn: return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE username = ?", (username_to_delete,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Usuario '{username_to_delete}' eliminado permanentemente.")
            return True
        else:
            print(f"Usuario '{username_to_delete}' no encontrado.")
            return False
    except Exception as e:
        print(f"Error al eliminar usuario: {e}")
        return False
    finally:
        conn.close()

def has_permission(user_role: str | None, required_roles: list[str]) -> bool:
    """
    Verifica si el rol de un usuario está en la lista de roles requeridos,
    o si el usuario es SUPERUSER (que tiene todos los permisos).
    """
    if not user_role: # Si el usuario no está logueado o no tiene rol
        return False
    if user_role == ROLE_SUPERUSER:
        return True # Superuser tiene todos los permisos
    
    if not isinstance(required_roles, list): # Asegurar que required_roles es una lista
        required_roles = [required_roles]
        
    return user_role in required_roles


if __name__ == "__main__":
    print("--- Probando el módulo auth.py ---")
    # Asegurarse de que la BD y config están listos (ejecutar database.py primero)
    # initialize_superuser() # Esto se llamará desde main.py usualmente

    # --- Crear Usuarios de Prueba ---
    print("\nCreando usuarios de prueba...")
    create_user("programadmin", "adminpass", ROLE_PROGRAM_ADMIN, "padmin@example.com")
    create_user("dataadmin", "datapass", ROLE_DATA_ADMIN, "dadmin@example.com")
    create_user("staffuser", "staffpass", ROLE_STAFF, "staff@example.com")
    create_user("testuser", "testpass", ROLE_STAFF, "test@example.com", is_active=False) # Usuario inactivo

    # --- Probar Login ---
    print("\nProbando logins...")
    root_user = login_user(SUPERUSER_USERNAME, SUPERUSER_PASSWORD)
    print(f"Login Superuser ({SUPERUSER_USERNAME}): {'Exitoso' if root_user else 'Fallido'} - Rol: {root_user.get('role') if root_user else 'N/A'}")
    
    p_admin_user = login_user("programadmin", "adminpass")
    print(f"Login Program Admin (programadmin): {'Exitoso' if p_admin_user else 'Fallido'} - Rol: {p_admin_user.get('role') if p_admin_user else 'N/A'}")
    
    wrong_pass_user = login_user("dataadmin", "wrongpassword")
    print(f"Login Data Admin (dataadmin) con contraseña incorrecta: {'Exitoso' if wrong_pass_user else 'Fallido'}")

    inactive_user_login = login_user("testuser", "testpass")
    print(f"Login Usuario Inactivo (testuser): {'Exitoso' if inactive_user_login else 'Fallido'}")

    non_existent_user = login_user("noexiste", "cualquiera")
    print(f"Login Usuario Inexistente (noexiste): {'Exitoso' if non_existent_user else 'Fallido'}")

    # --- Obtener todos los usuarios ---
    print("\nLista de todos los usuarios:")
    all_users_list = get_all_users()
    if all_users_list:
        for u in all_users_list:
            print(f"  - ID: {u['id']}, User: {u['username']}, Email: {u.get('email', 'N/A')}, Rol: {u['role']}, Activo: {u['is_active']}")
    else:
        print("  No se pudieron obtener usuarios.")

    # --- Actualizar detalles de un usuario (ej. email por el propio usuario) ---
    if p_admin_user:
        print(f"\nActualizando email de 'programadmin' a 'newpadmin@example.com'")
        update_user_details(p_admin_user['username'], new_email="newpadmin@example.com")
        updated_p_admin = get_user_by_username(p_admin_user['username'])
        print(f"Nuevo email para 'programadmin': {updated_p_admin.get('email') if updated_p_admin else 'Error'}")

    # --- Actualizar rol por admin ---
    if root_user: # El superuser realiza la acción
        print("\nSuperusuario actualizando rol de 'staffuser' a 'data_admin':")
        update_user_role_by_admin("staffuser", ROLE_DATA_ADMIN, root_user['role'])
        staff_updated = get_user_by_username("staffuser")
        print(f"Nuevo rol para 'staffuser': {staff_updated.get('role') if staff_updated else 'No encontrado'}")

        # Program admin intentando cambiar a superuser (debería fallar)
        print("\nProgram admin intentando cambiar 'staffuser' a 'superuser':")
        # Para esto, p_admin_user debe existir. Si la creación falló arriba, este test también.
        if p_admin_user:
            update_user_role_by_admin("staffuser", ROLE_SUPERUSER, p_admin_user['role']) # Debería imprimir error


    # --- Activar/Desactivar Usuario ---
    if root_user:
        print("\nDesactivando 'dataadmin':")
        set_user_active_status("dataadmin", False)
        da_status = get_user_by_username("dataadmin")
        print(f"Estado de 'dataadmin' después de desactivar: {'Activo' if da_status and da_status.get('is_active') else 'Inactivo'}")
        login_da_after_inactive = login_user("dataadmin", "datapass")
        print(f"Intento de login 'dataadmin' (inactivo): {'Exitoso' if login_da_after_inactive else 'Fallido'}")

        print("\nReactivando 'dataadmin':")
        set_user_active_status("dataadmin", True)
        login_da_after_active = login_user("dataadmin", "datapass")
        print(f"Intento de login 'dataadmin' (reactivado): {'Exitoso' if login_da_after_active else 'Fallido'}")


    # --- Verificar Permisos ---
    print("\nVerificando permisos:")
    if root_user:
        print(f"¿Superuser ({root_user['role']}) tiene permiso para ['program_admin']? {has_permission(root_user['role'], [ROLE_PROGRAM_ADMIN])}") # True
    if p_admin_user:
        print(f"¿Program Admin ({p_admin_user['role']}) tiene permiso para ['data_admin']? {has_permission(p_admin_user['role'], [ROLE_DATA_ADMIN])}") # False
        print(f"¿Program Admin ({p_admin_user['role']}) tiene permiso para ['program_admin', 'data_admin']? {has_permission(p_admin_user['role'], [ROLE_PROGRAM_ADMIN, ROLE_DATA_ADMIN])}") # True
    
    staff_user = login_user("staffuser", "staffpass") # Puede que el rol haya cambiado arriba
    if staff_user:
         print(f"¿Staff ({staff_user['role']}) tiene permiso para ['program_admin']? {has_permission(staff_user['role'], [ROLE_PROGRAM_ADMIN])}") # False


    # --- Eliminar Usuario ---
    # Asegúrate de que el 'performing_user_username' es válido. Usaremos 'programadmin' si existe.
    performing_username = p_admin_user['username'] if p_admin_user else SUPERUSER_USERNAME

    print(f"\nEliminando 'testuser' (realizado por '{performing_username}'):")
    delete_user("testuser", performing_username=performing_username)
    if get_user_by_username("testuser"):
        print("Error: 'testuser' no fue eliminado.")
    else:
        print("'testuser' eliminado correctamente o no existía.")
    
    # Para limpiar (¡CUIDADO AL EJECUTAR ESTO SI TIENES DATOS IMPORTANTES!),
    # estas líneas eliminarían los usuarios de prueba creados.
    # print("\nEliminando usuarios de prueba...")
    # for test_usr in ["programadmin", "dataadmin", "staffuser"]:
    #     if get_user_by_username(test_usr):
    #        delete_user(test_usr, performing_username=SUPERUSER_USERNAME)
    
    print("\n--- Fin de pruebas de auth.py ---")