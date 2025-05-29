import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import os 
import sys
from database import create_tables
from auth import (
    login_user,
    create_user,
    get_all_users,
    update_user_role,
    delete_user,
    has_permission,
    initialize_superuser
)
from members import (
    add_member as db_add_member, # Renombrar para evitar conflicto si tenemos una función add_member en la GUI
    view_all_members as db_view_all_members,
    find_member_by_id as db_find_member_by_id,
    record_attendance as db_record_member_attendance,
    generate_member_card as db_generate_member_card # Simularemos mostrarlo en un área de texto
)
from finances import (
    record_transaction as db_record_transaction,
    view_financial_summary as db_view_financial_summary
)
from config import (
    ROLE_SUPERUSER,
    ROLE_PROGRAM_ADMIN,
    ROLE_DATA_ADMIN,
    ROLE_STAFF,
    SUPERUSER_USERNAME
)

# --- Clase principal de la Aplicación GUI ---
class GymApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Sistema de Gestión de Gimnasio")
        # Centrar la ventana (aproximado)
        window_width = 800
        window_height = 600
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        center_x = int(screen_width/2 - window_width / 2)
        center_y = int(screen_height/2 - window_height / 2)
        self.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')

        self.current_user = None

        # Contenedor principal para cambiar entre vistas (Login, Main)
        self.container = ttk.Frame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {} # Diccionario para almacenar diferentes vistas/frames

        # Crear la vista de Login primero
        self.show_frame(LoginFrame)

    def show_frame(self, Frm):
        """Muestra un frame/vista específica."""
        # Si el frame ya existe, simplemente lo levanta
        if Frm in self.frames:
            frame = self.frames[Frm]
        else:
            # Si no existe, lo crea y lo guarda
            frame = Frm(parent=self.container, controller=self)
            self.frames[Frm] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        
        frame.tkraise()
        # Lógica para actualizar el frame si es necesario al mostrarse
        if Frm == MainFrame and hasattr(frame, 'update_for_user'):
             frame.update_for_user()


    def successful_login(self, user_data):
        self.current_user = user_data
        self.title(f"Gimnasio - Usuario: {self.current_user['username']} ({self.current_user['role']})")
        self.show_frame(MainFrame)

    def logout(self):
        self.current_user = None
        self.title("Sistema de Gestión de Gimnasio")
        # Limpiar frames para que no guarden estado (opcional, pero bueno para el login)
        if LoginFrame in self.frames:
            self.frames[LoginFrame].clear_entries() # Necesitarás un método clear_entries en LoginFrame
        self.show_frame(LoginFrame)


# --- Frame/Vista de Login ---
class LoginFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller # Referencia a la aplicación principal GymApp

        ttk.Label(self, text="Inicio de Sesión", font=("Arial", 18)).pack(pady=20)

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        ttk.Label(self, text="Usuario:").pack()
        self.username_entry = ttk.Entry(self, textvariable=self.username_var, width=30)
        self.username_entry.pack(pady=5)

        ttk.Label(self, text="Contraseña:").pack()
        self.password_entry = ttk.Entry(self, textvariable=self.password_var, show="*", width=30)
        self.password_entry.pack(pady=5)

        self.login_button = ttk.Button(self, text="Login", command=self.attempt_login)
        self.login_button.pack(pady=20)
        self.password_entry.bind("<Return>", lambda event: self.attempt_login()) # Login con Enter
        self.username_entry.bind("<Return>", lambda event: self.password_entry.focus()) # Saltar a password con Enter


        self.status_label = ttk.Label(self, text="", foreground="red")
        self.status_label.pack(pady=10)

    def attempt_login(self):
        username = self.username_var.get()
        password = self.password_var.get()
        user_data = login_user(username, password) # Llama a la función de auth.py

        if user_data:
            self.status_label.config(text="")
            self.controller.successful_login(user_data)
        else:
            self.status_label.config(text="Usuario o contraseña incorrectos.")
            self.password_var.set("") # Limpiar contraseña

    def clear_entries(self):
        """Limpia los campos de entrada al volver a este frame."""
        self.username_var.set("")
        self.password_var.set("")
        self.status_label.config(text="")
        self.username_entry.focus_set() # Poner el foco en el usuario


# --- Frame/Vista Principal (después del Login) ---
class MainFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Barra de menú (opcional, botones pueden ser suficientes)
        menubar = tk.Menu(self.controller)
        self.controller.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        file_menu.add_command(label="Logout", command=self.controller.logout)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.controller.quit)

        # Título en el frame principal
        self.welcome_label = ttk.Label(self, text="", font=("Arial", 16))
        self.welcome_label.pack(pady=20)

        # Frame para los botones de acción
        self.actions_frame = ttk.Frame(self)
        self.actions_frame.pack(pady=10, padx=10, fill="x")

        # Botones (se crearán/actualizarán en update_for_user)
        self.btn_manage_users = None
        self.btn_manage_members = None
        self.btn_manage_finances = None
        self.btn_record_attendance = None
        
        # Frame para mostrar contenido (ej. listas, formularios, etc.)
        # Este sería el lugar donde se cargarían sub-vistas o widgets más complejos
        self.content_frame = ttk.Frame(self, relief="sunken", borderwidth=1)
        self.content_frame.pack(pady=20, padx=20, fill="both", expand=True)
        ttk.Label(self.content_frame, text="Área de contenido principal").pack(padx=10, pady=10)

    def update_for_user(self):
        """Actualiza la UI basada en el usuario actual (roles y permisos)."""
        if not self.controller.current_user:
            self.controller.logout() # Si no hay usuario, volver al login
            return

        user = self.controller.current_user
        self.welcome_label.config(text=f"Bienvenido, {user['username']} (Rol: {user['role']})")

        # Limpiar botones anteriores para redibujar si el rol cambia
        for widget in self.actions_frame.winfo_children():
            widget.destroy()
        self.btn_manage_users = None # Resetear para que se creen de nuevo
        self.btn_manage_members = None
        self.btn_manage_finances = None
        self.btn_record_attendance = None


        # --- Crear botones basados en permisos ---
        current_col = 0 # Para ttk.Grid

        # Botón Gestión de Usuarios (PROGRAM_ADMIN o SUPERUSER)
        if has_permission(user['role'], [ROLE_PROGRAM_ADMIN, ROLE_SUPERUSER]):
            self.btn_manage_users = ttk.Button(self.actions_frame, text="Gestionar Usuarios",
                                               command=self.open_user_management)
            self.btn_manage_users.grid(row=0, column=current_col, padx=5, pady=5, sticky="ew")
            current_col += 1

        # Botón Gestión de Miembros (DATA_ADMIN o SUPERUSER)
        if has_permission(user['role'], [ROLE_DATA_ADMIN, ROLE_SUPERUSER]):
            self.btn_manage_members = ttk.Button(self.actions_frame, text="Gestionar Miembros",
                                                 command=self.open_member_management)
            self.btn_manage_members.grid(row=0, column=current_col, padx=5, pady=5, sticky="ew")
            current_col += 1

        # Botón Gestión de Finanzas (DATA_ADMIN o SUPERUSER)
        if has_permission(user['role'], [ROLE_DATA_ADMIN, ROLE_SUPERUSER]):
            self.btn_manage_finances = ttk.Button(self.actions_frame, text="Gestionar Finanzas",
                                                 command=self.open_finance_management)
            self.btn_manage_finances.grid(row=0, column=current_col, padx=5, pady=5, sticky="ew")
            current_col += 1
        
        # Botón Registrar Asistencia (STAFF, DATA_ADMIN, PROGRAM_ADMIN, SUPERUSER)
        if has_permission(user['role'], [ROLE_STAFF, ROLE_DATA_ADMIN, ROLE_PROGRAM_ADMIN, ROLE_SUPERUSER]):
            self.btn_record_attendance = ttk.Button(self.actions_frame, text="Registrar Asistencia",
                                                 command=self.open_record_attendance) # No implementada aún
            self.btn_record_attendance.grid(row=0, column=current_col, padx=5, pady=5, sticky="ew")
            current_col +=1

        # Ajustar columnas del frame de acciones para que se expandan equitativamente
        for i in range(current_col):
            self.actions_frame.grid_columnconfigure(i, weight=1)
        
        # Limpiar content_frame al cambiar de usuario o al cargar por primera vez
        self.clear_content_frame()
        ttk.Label(self.content_frame, text="Seleccione una opción del menú superior.").pack(padx=10, pady=10)


    def clear_content_frame(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    # --- Métodos para abrir las diferentes secciones de gestión (Placeholder) ---
    def open_user_management(self):
        self.clear_content_frame()
        # Aquí instanciarías y mostrarías un UserManagementFrame(self.content_frame, self.controller)
        # o llamarías a una función que construya la UI de gestión de usuarios en self.content_frame
        UserManagementFrame(parent=self.content_frame, controller=self.controller).pack(fill="both", expand=True)

    def open_member_management(self):
        self.clear_content_frame()
        ttk.Label(self.content_frame, text="[Sección: Gestión de Miembros - GUI en construcción]").pack(padx=10, pady=10)
        # Aquí llamarías a la creación de la GUI para miembros.
        # Ejemplo de cómo se haría la integración:
        btn_add = ttk.Button(self.content_frame, text="Añadir Miembro (Test)", command=self.test_add_member)
        btn_add.pack(pady=5)

    def test_add_member(self): # Esto sería mucho más complejo en la realidad
        # db_add_member() necesita muchos inputs, esto es solo para ver la llamada
        # Para una GUI real, crearías Entry widgets, obtendrías sus valores y los pasarías a db_add_member
        messagebox.showinfo("Test Miembro", "Llamaría a una ventana para añadir datos de miembro.")

    def open_finance_management(self):
        self.clear_content_frame()
        ttk.Label(self.content_frame, text="[Sección: Gestión de Finanzas - GUI en construcción]").pack(padx=10, pady=10)
    
    def open_record_attendance(self):
        self.clear_content_frame()
        ttk.Label(self.content_frame, text="[Sección: Registrar Asistencia - GUI en construcción]").pack(padx=10, pady=10)

# --- Frame de ejemplo para la Gestión de Usuarios ---
class UserManagementFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text="Gestión de Usuarios", font=("Arial", 14)).pack(pady=10)

        # --- Frame para botones de acción ---
        action_button_frame = ttk.Frame(self)
        action_button_frame.pack(pady=5, fill="x", padx=10)

        ttk.Button(action_button_frame, text="Crear Usuario", command=self.create_user_window).pack(side="left", padx=5)
        ttk.Button(action_button_frame, text="Actualizar Lista", command=self.populate_user_list).pack(side="left", padx=5)
        # Podríamos añadir botones para modificar y eliminar si hay un usuario seleccionado en la lista

        # --- Lista de Usuarios (TreeView) ---
        cols = ('ID', 'Username', 'Role')
        self.user_tree = ttk.Treeview(self, columns=cols, show='headings', selectmode="browse")
        for col in cols:
            self.user_tree.heading(col, text=col)
            self.user_tree.column(col, width=150, anchor="w")
        self.user_tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.user_tree.bind("<<TreeviewSelect>>", self.on_user_select)
        self.selected_user_id = None # Para saber qué usuario está seleccionado

        # Botones para acciones sobre el usuario seleccionado
        self.edit_button = ttk.Button(action_button_frame, text="Modificar Rol Seleccionado", command=self.edit_selected_user_role, state="disabled")
        self.edit_button.pack(side="left", padx=5)
        self.delete_button = ttk.Button(action_button_frame, text="Eliminar Seleccionado", command=self.delete_selected_user, state="disabled")
        self.delete_button.pack(side="left", padx=5)

        self.populate_user_list()

    def on_user_select(self, event):
        selected_item = self.user_tree.focus() # Obtiene el item seleccionado
        if selected_item:
            item_values = self.user_tree.item(selected_item, "values")
            self.selected_user_id = item_values[0] # Suponiendo que el ID es el primer valor
            self.selected_username = item_values[1]
            self.edit_button.config(state="normal")
            self.delete_button.config(state="normal")
        else:
            self.selected_user_id = None
            self.selected_username = None
            self.edit_button.config(state="disabled")
            self.delete_button.config(state="disabled")


    def populate_user_list(self):
        # Limpiar lista actual
        for i in self.user_tree.get_children():
            self.user_tree.delete(i)
        # Obtener usuarios y poblarlos
        users_data = get_all_users() # De auth.py
        if users_data:
            for user_item in users_data:
                self.user_tree.insert("", "end", values=(user_item['id'], user_item['username'], user_item['role']))
        self.edit_button.config(state="disabled") # Deshabilitar botones de acción
        self.delete_button.config(state="disabled")
        self.selected_user_id = None


    def create_user_window(self):
        # Esta función abriría una nueva ventana (Toplevel) para ingresar datos del nuevo usuario.
        # Por simplicidad, aquí un ejemplo de cómo sería la lógica, sin la ventana completa.
        win_create = tk.Toplevel(self)
        win_create.title("Crear Nuevo Usuario")
        win_create.geometry("350x250")
        # Para centrar la ventana Toplevel con respecto a la principal:
        # app_x = self.controller.winfo_x()
        # app_y = self.controller.winfo_y()
        # app_width = self.controller.winfo_width()
        # app_height = self.controller.winfo_height()
        # win_create_x = app_x + (app_width // 2) - (350 // 2)
        # win_create_y = app_y + (app_height // 2) - (250 // 2)
        # win_create.geometry(f"+{win_create_x}+{win_create_y}")


        ttk.Label(win_create, text="Nombre de Usuario:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        username_entry = ttk.Entry(win_create, width=30)
        username_entry.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(win_create, text="Contraseña:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        password_entry = ttk.Entry(win_create, show="*", width=30)
        password_entry.grid(row=1, column=1, padx=10, pady=5)

        ttk.Label(win_create, text="Rol:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        roles = [ROLE_PROGRAM_ADMIN, ROLE_DATA_ADMIN, ROLE_STAFF]
        role_var = tk.StringVar(value=roles[2]) # Default a staff
        role_combobox = ttk.Combobox(win_create, textvariable=role_var, values=roles, state="readonly", width=28)
        role_combobox.grid(row=2, column=1, padx=10, pady=5)

        def do_create():
            uname = username_entry.get()
            pwd = password_entry.get()
            role = role_var.get()
            if not uname or not pwd:
                messagebox.showerror("Error", "Usuario y contraseña no pueden estar vacíos.", parent=win_create)
                return
            
            # Llama a la función de auth.py
            if create_user(uname, pwd, role):
                messagebox.showinfo("Éxito", f"Usuario '{uname}' creado.", parent=win_create)
                self.populate_user_list() # Actualizar la lista en el frame padre
                win_create.destroy()
            else:
                # create_user ya imprime un error si el usuario existe, aquí podríamos ser más específicos
                messagebox.showerror("Error", f"No se pudo crear el usuario '{uname}'.\nPuede que ya exista.", parent=win_create)

        save_button = ttk.Button(win_create, text="Guardar Usuario", command=do_create)
        save_button.grid(row=3, column=0, columnspan=2, pady=15)
        
        win_create.transient(self.controller) # Hacer que la ventana sea modal con respecto a la app
        win_create.grab_set() # Capturar eventos para esta ventana
        win_create.wait_window() # Esperar a que se cierre


    def edit_selected_user_role(self):
        if not self.selected_user_id or not self.selected_username:
            messagebox.showwarning("Selección", "Por favor, seleccione un usuario de la lista.")
            return
        if self.selected_username == SUPERUSER_USERNAME:
            messagebox.showerror("Error", "No se puede modificar el rol del superusuario.")
            return

        win_edit = tk.Toplevel(self)
        win_edit.title(f"Modificar Rol - {self.selected_username}")
        # ... (similar a create_user_window para obtener el nuevo rol)
        # Luego llamar a: update_user_role(self.selected_username, nuevo_rol)
        # Y después: self.populate_user_list()
        
        ttk.Label(win_edit, text=f"Modificar rol para: {self.selected_username}").grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        ttk.Label(win_edit, text="Nuevo Rol:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        roles = [ROLE_PROGRAM_ADMIN, ROLE_DATA_ADMIN, ROLE_STAFF]
        new_role_var = tk.StringVar()
        # Obtener rol actual para preseleccionar, si es posible (no lo tenemos fácilmente aquí)
        role_combobox = ttk.Combobox(win_edit, textvariable=new_role_var, values=roles, state="readonly", width=28)
        role_combobox.grid(row=1, column=1, padx=10, pady=5)
        
        def do_update_role():
            new_role = new_role_var.get()
            if not new_role:
                messagebox.showerror("Error", "Debe seleccionar un nuevo rol.", parent=win_edit)
                return
            if update_user_role(self.selected_username, new_role):
                 messagebox.showinfo("Éxito", f"Rol de '{self.selected_username}' actualizado a '{new_role}'.", parent=win_edit)
                 self.populate_user_list()
                 win_edit.destroy()
            else:
                 messagebox.showerror("Error", "No se pudo actualizar el rol.", parent=win_edit)

        update_button = ttk.Button(win_edit, text="Actualizar Rol", command=do_update_role)
        update_button.grid(row=2, column=0, columnspan=2, pady=15)
        
        win_edit.transient(self.controller)
        win_edit.grab_set()
        win_edit.wait_window()


    def delete_selected_user(self):
        if not self.selected_user_id or not self.selected_username:
            messagebox.showwarning("Selección", "Por favor, seleccione un usuario de la lista.")
            return
        if self.selected_username == self.controller.current_user['username']:
             messagebox.showerror("Error", "No puede eliminarse a sí mismo.")
             return
        if self.selected_username == SUPERUSER_USERNAME:
            messagebox.showerror("Error", "No se puede eliminar al superusuario.")
            return
        
        if messagebox.askyesno("Confirmar", f"¿Está seguro de eliminar al usuario '{self.selected_username}'?"):
            if delete_user(self.selected_username): # Llama a la función de auth.py
                messagebox.showinfo("Éxito", f"Usuario '{self.selected_username}' eliminado.")
                self.populate_user_list()
            else:
                messagebox.showerror("Error", f"No se pudo eliminar al usuario '{self.selected_username}'.")


# --- Punto de Entrada de la Aplicación ---
if __name__ == "__main__":
    # 1. Asegurar que la estructura de la base de datos está lista
    print("Verificando/Creando estructura de la base de datos...")
    create_tables()
    print("Estructura de la base de datos verificada/creada.")

    # 2. Asegurar que el superusuario existe
    print(f"Verificando/Inicializando superusuario '{SUPERUSER_USERNAME}'...")
    initialize_superuser()
    print(f"Superusuario '{SUPERUSER_USERNAME}' verificado/inicializado.")
    print("--- Lanzando aplicación GUI ---")

    app = GymApp()
    app.mainloop()