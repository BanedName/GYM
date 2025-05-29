# gimnasio_mgmt_gui/gui_frames/user_management_frame.py
# Frame para la gestión de usuarios del sistema.

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime # <-- CORRECCIÓN: Importar datetime

# Importaciones de la aplicación
try:
    from config import (
        ALL_DEFINED_ROLES, ASSIGNABLE_ROLES_BY_SYSTEM_ADMIN, ROLE_SUPERUSER,
        SUPERUSER_INIT_USERNAME,
        # --- CORRECCIÓN: Asegurar que los roles usados en el __main__ también se importan si se prueba aisladamente ---
        ROLE_DATA_MANAGER, ROLE_STAFF_MEMBER, ROLE_SYSTEM_ADMIN # (ROLE_SYSTEM_ADMIN ya estaba)
    )
    from core_logic.auth import (
        get_all_system_users, create_system_user, update_user_role,
        set_user_activation_status, delete_system_user, get_system_user_by_username,
        update_user_password
    )
    from core_logic.utils import is_valid_system_username, check_password_strength, format_datetime_for_ui
except ImportError as e:
    messagebox.showerror("Error de Carga (UserManagement)", f"No se pudieron cargar componentes para Gestión de Usuarios.\nError: {e}")
    raise


class UserManagementFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="TFrame")
        self.parent = parent
        self.controller = controller 

        self.selected_user_id = None
        self.selected_username = None

        self.create_widgets()
        self.grid_widgets()
        self.load_user_list()

    def create_widgets(self):
        # (Código de create_widgets sin cambios funcionales aquí)
        self.action_buttons_frame = ttk.Frame(self, style="TFrame", padding=(10,10))

        self.btn_refresh_list = ttk.Button(self.action_buttons_frame, text="Refrescar Lista", command=self.load_user_list, style="TButton")
        self.btn_create_user = ttk.Button(self.action_buttons_frame, text="Crear Nuevo Usuario", command=self.open_create_user_dialog, style="TButton")
        
        self.btn_edit_user = ttk.Button(self.action_buttons_frame, text="Modificar Usuario", command=self.open_edit_user_dialog, style="TButton", state="disabled")
        self.btn_change_password = ttk.Button(self.action_buttons_frame, text="Cambiar Contraseña", command=self.open_change_password_dialog, style="TButton", state="disabled")
        self.btn_toggle_active = ttk.Button(self.action_buttons_frame, text="Activar/Desactivar", command=self.toggle_user_activation, style="TButton", state="disabled")
        self.btn_delete_user = ttk.Button(self.action_buttons_frame, text="Eliminar Usuario", command=self.delete_selected_user, style="TButton", state="disabled")

        self.tree_columns = ("id", "username", "role", "is_active", "last_login")
        self.tree_column_names = ("ID DB", "Nombre de Usuario", "Rol Asignado", "Estado Cuenta", "Último Inicio Sesión")
        
        self.users_treeview = ttk.Treeview(
            self, columns=self.tree_columns, show="headings", selectmode="browse"
        )

        for col, name in zip(self.tree_columns, self.tree_column_names):
            width = 120; anchor="w" # Default width
            if col == "id": width = 60; anchor="center"
            elif col == "username": width = 200
            elif col == "role": width = 180
            elif col == "is_active": width = 100; anchor="center"
            elif col == "last_login": width = 180; anchor="center"
            self.users_treeview.heading(col, text=name, anchor=anchor) # Usar el anchor definido
            self.users_treeview.column(col, width=width, stretch=tk.YES, anchor=anchor)


        self.users_treeview.bind("<<TreeviewSelect>>", self.on_user_selected_in_tree)

        self.tree_scrollbar_y = ttk.Scrollbar(self, orient="vertical", command=self.users_treeview.yview)
        self.users_treeview.configure(yscrollcommand=self.tree_scrollbar_y.set)

    def grid_widgets(self):
        # (Código de grid_widgets sin cambios funcionales aquí)
        self.columnconfigure(0, weight=1) 
        self.columnconfigure(1, weight=0) 
        self.rowconfigure(1, weight=1)   

        self.action_buttons_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.btn_refresh_list.pack(side="left", padx=5, pady=5)
        self.btn_create_user.pack(side="left", padx=5, pady=5)
        self.btn_edit_user.pack(side="left", padx=5, pady=5)
        self.btn_change_password.pack(side="left", padx=5, pady=5)
        self.btn_toggle_active.pack(side="left", padx=5, pady=5)
        self.btn_delete_user.pack(side="left", padx=5, pady=5)

        self.users_treeview.grid(row=1, column=0, sticky="nsew", padx=(5,0), pady=5)
        self.tree_scrollbar_y.grid(row=1, column=1, sticky="ns", padx=(0,5), pady=5)


    def load_user_list(self):
        for item in self.users_treeview.get_children():
            self.users_treeview.delete(item)
        
        current_user_role = self.controller.current_user_info.get('role') if self.controller.current_user_info else None
        exclude_su = (current_user_role != ROLE_SUPERUSER)
        users_data = get_all_system_users(exclude_superuser=exclude_su)

        if users_data:
            for user_item in users_data:
                user_id_db = user_item.get('id', 'N/A')
                username = user_item.get('username', 'N/A')
                role = user_item.get('role', 'N/A')
                is_active_num = user_item.get('is_active', 0)
                status_text = "Activo" if is_active_num == 1 else "Inactivo"
                
                last_login_raw = user_item.get('last_login_at')
                last_login_ui = "Nunca"
                if isinstance(last_login_raw, str):
                    try:
                        # Línea 127 (del error) donde se usa `datetime`
                        dt_obj = datetime.fromisoformat(last_login_raw) # Uso de `datetime`
                        last_login_ui = format_datetime_for_ui(dt_obj) # Asumimos que esta función existe en utils
                    except ValueError:
                        last_login_ui = "Fecha Inv." 
                elif isinstance(last_login_raw, datetime): # Si ya es un objeto datetime
                     last_login_ui = format_datetime_for_ui(last_login_raw)


                values = (user_id_db, username, role, status_text, last_login_ui)
                self.users_treeview.insert("", "end", values=values, iid=username)
        
        self.deselect_user()

    # (Resto de los métodos de UserManagementFrame como on_user_selected_in_tree,
    #  deselect_user, update_action_buttons_state, open_create_user_dialog,
    #  open_edit_user_dialog, open_change_password_dialog, toggle_user_activation,
    #  delete_selected_user, on_show_frame, give_focus SIN CAMBIOS FUNCIONALES AQUÍ.
    #  Es importante que el cierre de conexiones a BD esté bien manejado en las funciones
    #  de core_logic.auth que estas llaman.)
    def on_user_selected_in_tree(self, event=None):
        selected_items = self.users_treeview.selection()
        if selected_items:
            selected_iid = selected_items[0] 
            self.selected_username = selected_iid
            self.update_action_buttons_state(is_selected=True)
        else:
            self.deselect_user()

    def deselect_user(self):
        self.selected_user_id = None
        self.selected_username = None
        self.update_action_buttons_state(is_selected=False)

    def update_action_buttons_state(self, is_selected: bool):
        state_if_selected = "normal" if is_selected else "disabled"
        self.btn_edit_user.config(state=state_if_selected)
        self.btn_change_password.config(state=state_if_selected)
        self.btn_toggle_active.config(state=state_if_selected)
        self.btn_delete_user.config(state=state_if_selected)

        if is_selected and self.selected_username:
            current_logged_in_user = self.controller.current_user_info.get('username', "").lower() if self.controller.current_user_info else ""
            selected_user_lower = self.selected_username.lower()
            
            if selected_user_lower == SUPERUSER_INIT_USERNAME.lower() or \
               selected_user_lower == current_logged_in_user:
                self.btn_toggle_active.config(state="disabled")
                self.btn_delete_user.config(state="disabled")
                # Un superusuario no puede cambiar su propia contraseña o rol desde esta interfaz general
                if selected_user_lower == current_logged_in_user and selected_user_lower == SUPERUSER_INIT_USERNAME.lower() :
                     self.btn_edit_user.config(state="disabled") # Superadmin no se edita el rol a sí mismo aquí
                     self.btn_change_password.config(state="disabled") # Ni su contraseña desde aquí


    def open_create_user_dialog(self):
        dialog = UserFormDialog(self, controller=self.controller, title="Crear Nuevo Usuario del Sistema", existing_username=None)
        if dialog.result and dialog.result.get("success"): 
            self.load_user_list() 
            messagebox.showinfo("Usuario Creado", f"Usuario '{dialog.result.get('username', 'N/A')}' creado.", parent=self)

    def open_edit_user_dialog(self):
        if not self.selected_username:
            messagebox.showwarning("Selección Requerida", "Seleccione un usuario para modificar.", parent=self)
            return
        
        dialog = UserFormDialog(self, controller=self.controller, title=f"Modificar Usuario: {self.selected_username}", existing_username=self.selected_username)
        if dialog.result and dialog.result.get("success"):
            self.load_user_list()
            messagebox.showinfo("Usuario Modificado", f"Usuario '{self.selected_username}' modificado.", parent=self)

    def open_change_password_dialog(self):
        if not self.selected_username:
            messagebox.showwarning("Selección Requerida", "Seleccione un usuario.", parent=self)
            return
        # Un usuario no puede cambiar la contraseña del SUPERUSER_INIT_USERNAME desde aquí,
        # salvo que el propio superusuario sea el logueado (y para eso tendría un panel "Mi Perfil").
        # Esta es una acción administrativa sobre OTRO usuario.
        if self.selected_username.lower() == SUPERUSER_INIT_USERNAME.lower() and \
           (not self.controller.current_user_info or self.controller.current_user_info.get('role') != ROLE_SUPERUSER):
            messagebox.showerror("Permiso Denegado", "No se puede cambiar la contraseña del superadministrador desde aquí.", parent=self)
            return

        dialog = ChangePasswordDialog(self, controller=self.controller, username_to_change=self.selected_username)
        if dialog.result and dialog.result.get("success"):
             messagebox.showinfo("Contraseña Cambiada", f"Contraseña para '{self.selected_username}' actualizada.", parent=self)

    def toggle_user_activation(self):
        if not self.selected_username: return
        user_data = get_system_user_by_username(self.selected_username) 
        if not user_data:
            messagebox.showerror("Error", "Usuario no encontrado.", parent=self)
            self.load_user_list(); return
        current_is_active = bool(user_data.get('is_active', 0))
        action_text = "desactivar" if current_is_active else "activar"
        new_status = not current_is_active
        if messagebox.askyesno("Confirmar", f"¿Desea {action_text} la cuenta '{self.selected_username}'?", parent=self):
            admin_role = self.controller.current_user_info.get('role') if self.controller.current_user_info else ""
            success, msg = set_user_activation_status(self.selected_username, new_status, admin_role)
            if success: messagebox.showinfo("Estado Actualizado", msg, parent=self); self.load_user_list()
            else: messagebox.showerror("Error", msg, parent=self)

    def delete_selected_user(self):
        if not self.selected_username: return
        if messagebox.askyesno("Confirmar Eliminación", f"¿ELIMINAR PERMANENTEMENTE al usuario '{self.selected_username}'?\n¡Acción irreversible!", icon='warning', parent=self):
            admin_user = self.controller.current_user_info.get('username') if self.controller.current_user_info else ""
            admin_role = self.controller.current_user_info.get('role') if self.controller.current_user_info else ""
            success, msg = delete_system_user(self.selected_username, admin_user, admin_role)
            if success: messagebox.showinfo("Usuario Eliminado", msg, parent=self); self.load_user_list()
            else: messagebox.showerror("Error al Eliminar", msg, parent=self)

    def on_show_frame(self, data_to_pass: dict | None = None):
        self.load_user_list()
        self.give_focus()

    def give_focus(self):
        self.btn_refresh_list.focus_set()


# --- CLASES DE DIÁLOGO (UserFormDialog, ChangePasswordDialog) ---
# (El código de estas clases de diálogo permanece como estaba antes en su estructura general.
#  La corrección clave es asegurar que SI usan constantes de config.py como UI_DEFAULT_FONT_FAMILY,
#  estas deben ser importadas explícitamente al inicio del archivo user_management_frame.py
#  y usadas sin el prefijo 'config.'.)

# Ejemplo: si UserFormDialog.create_form_widgets usa fuentes de config:
# class UserFormDialog(tk.Toplevel):
#     ...
#     def create_form_widgets(self):
#         ...
#         self.username_entry = ttk.Entry(..., font=(UI_DEFAULT_FONT_FAMILY, UI_DEFAULT_FONT_SIZE_NORMAL)) # Correcto
#         ...

# Manteniendo las clases de diálogo como estaban, pero Pylance no debería quejarse de `datetime` dentro de ellas
# si la importación principal está hecha. Lo mismo para roles si se usan en mocks.
class UserFormDialog(tk.Toplevel):
    def __init__(self, parent_frame, controller, title: str, existing_username: str | None = None):
        super().__init__(parent_frame)
        self.parent_frame = parent_frame
        self.controller = controller 
        self.existing_username = existing_username 
        self.result = None 

        self.title(title)
        self.transient(parent_frame) 
        self.grab_set() 
        self.resizable(False, False)

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()
        self.role_var = tk.StringVar()
        self.is_active_var = tk.BooleanVar(value=True)

        self.create_form_widgets_user_dialog() # Renombrado para unicidad
        self.grid_form_widgets_user_dialog() # Renombrado

        if self.existing_username:
            self.load_existing_user_data_dialog() # Renombrado
        else:
            current_user_role = self.controller.current_user_info.get('role')
            available_roles = ASSIGNABLE_ROLES_BY_SYSTEM_ADMIN
            default_role_selection_idx = -1 # Seleccionar el último como staff
            if current_user_role == ROLE_SUPERUSER: # Superusuario puede asignar cualquier rol
                available_roles = ALL_DEFINED_ROLES
            
            self.role_combobox['values'] = available_roles
            if available_roles : self.role_var.set(available_roles[default_role_selection_idx])

            self.username_entry.config(state="normal")
            self.password_label.config(text="Contraseña (*):") 
            self.confirm_password_label.config(text="Confirmar Contraseña (*):")

        self.protocol("WM_DELETE_WINDOW", self.on_cancel_user_dialog) # Renombrado
        self.center_dialog_user() # Renombrado
        self.username_entry.focus_set() 
        self.wait_window() 

    def center_dialog_user(self):
        self.update_idletasks()
        # ... (código de centrado, igual que en otros diálogos)
        parent_x = self.master.winfo_rootx()
        parent_y = self.master.winfo_rooty()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        if dialog_width > 0 and dialog_height > 0:
             self.geometry(f"+{x}+{y}")

    def create_form_widgets_user_dialog(self): # Renombrado
        self.form_frame = ttk.Frame(self, padding=20, style="TFrame")
        
        self.username_label = ttk.Label(self.form_frame, text="Nombre de Usuario (*):")
        self.username_entry = ttk.Entry(self.form_frame, textvariable=self.username_var, width=35)
        
        self.password_label = ttk.Label(self.form_frame, text="Contraseña (vacío para no cambiar):")
        self.password_entry = ttk.Entry(self.form_frame, textvariable=self.password_var, show="*", width=35)
        
        self.confirm_password_label = ttk.Label(self.form_frame, text="Confirmar Contraseña:")
        self.confirm_password_entry = ttk.Entry(self.form_frame, textvariable=self.confirm_password_var, show="*", width=35)
        
        self.role_label = ttk.Label(self.form_frame, text="Rol Asignado (*):")
        self.role_combobox = ttk.Combobox(self.form_frame, textvariable=self.role_var, state="readonly", width=33)

        self.is_active_checkbutton = ttk.Checkbutton(self.form_frame, text="Cuenta Activa", variable=self.is_active_var, onvalue=True, offvalue=False)
        
        self.status_label_user_dialog = ttk.Label(self.form_frame, text="", style="Error.TLabel", wraplength=300) # Nombre único

        self.btn_save = ttk.Button(self.form_frame, text="Guardar Cambios", command=self.on_save_user_dialog, style="TButton") # Renombrado
        self.btn_cancel = ttk.Button(self.form_frame, text="Cancelar", command=self.on_cancel_user_dialog, style="TButton") # Renombrado

    def grid_form_widgets_user_dialog(self): # Renombrado
        self.form_frame.pack(fill="both", expand=True)
        
        row = 0
        self.username_label.grid(row=row, column=0, sticky="w", pady=(0,5))
        self.username_entry.grid(row=row, column=1, sticky="ew", pady=(0,5)); row += 1
        self.password_label.grid(row=row, column=0, sticky="w", pady=(0,5))
        self.password_entry.grid(row=row, column=1, sticky="ew", pady=(0,5)); row += 1
        self.confirm_password_label.grid(row=row, column=0, sticky="w", pady=(0,5))
        self.confirm_password_entry.grid(row=row, column=1, sticky="ew", pady=(0,5)); row += 1
        self.role_label.grid(row=row, column=0, sticky="w", pady=(0,5))
        self.role_combobox.grid(row=row, column=1, sticky="ew", pady=(0,5)); row += 1
        self.is_active_checkbutton.grid(row=row, column=1, sticky="w", pady=(5,10)); row += 1
        self.status_label_user_dialog.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(5,10)); row += 1
        
        buttons_frame = ttk.Frame(self.form_frame, style="TFrame")
        buttons_frame.grid(row=row, column=0, columnspan=2, pady=(10,0), sticky="e")
        self.btn_save.pack(side="right", padx=(5,0))
        self.btn_cancel.pack(side="right")
        self.form_frame.columnconfigure(1, weight=1)

    def load_existing_user_data_dialog(self): # Renombrado
        if not self.existing_username: return
        user_data = get_system_user_by_username(self.existing_username)
        if not user_data:
            messagebox.showerror("Error", f"Datos no encontrados para '{self.existing_username}'.", parent=self); self.destroy(); return

        self.username_var.set(user_data.get('username', ''))
        self.username_entry.config(state="disabled")
        self.role_var.set(user_data.get('role', ''))
        self.is_active_var.set(bool(user_data.get('is_active', 0)))

        current_admin_role = self.controller.current_user_info.get('role')
        editing_user_role = user_data.get('role')
        is_editing_superuser_init = (self.existing_username.lower() == SUPERUSER_INIT_USERNAME.lower())

        available_roles_for_combo = ASSIGNABLE_ROLES_BY_SYSTEM_ADMIN
        role_combo_state = "readonly"
        is_active_state = "normal"

        if current_admin_role == ROLE_SUPERUSER:
            available_roles_for_combo = ALL_DEFINED_ROLES
            if is_editing_superuser_init: # Superadmin editando el superusuario inicial
                role_combo_state = "disabled" # No puede cambiar su propio rol
                is_active_state = "disabled"  # No puede desactivarse a sí mismo
        elif editing_user_role == ROLE_SUPERUSER: # System Admin intentando editar un Superusuario
            messagebox.showerror("Permiso Denegado", "No puede modificar una cuenta de Superadministrador.", parent=self)
            self.destroy()
            return
        
        self.role_combobox['values'] = available_roles_for_combo
        self.role_combobox.config(state=role_combo_state)
        self.is_active_checkbutton.config(state=is_active_state)


    def on_save_user_dialog(self): # Renombrado
        username = self.username_var.get().strip()
        password = self.password_var.get()
        confirm_password = self.confirm_password_var.get()
        role = self.role_var.get()
        is_active = self.is_active_var.get()
        current_admin_role = self.controller.current_user_info.get('role') if self.controller.current_user_info else ""

        if not self.existing_username: # Creación
            if not is_valid_system_username(username):
                self.status_label_user_dialog.config(text="Nombre de usuario inválido."); return
            if not password:
                self.status_label_user_dialog.config(text="Contraseña obligatoria en creación."); return
        
        if password:
            if password != confirm_password:
                self.status_label_user_dialog.config(text="Contraseñas no coinciden."); return
            is_strong, strength_msg = check_password_strength(password)
            if not is_strong:
                self.status_label_user_dialog.config(text=f"Contraseña: {strength_msg}"); return
        
        if not role: self.status_label_user_dialog.config(text="Rol es obligatorio."); return

        if self.existing_username: # Editando
            # Actualizar rol y estado primero
            s_role, m_role = update_user_role(self.existing_username, role, current_admin_role)
            if not s_role: messagebox.showerror("Error Rol", m_role, parent=self); return
            
            # Solo intentar cambiar el estado si no es el superusuario inicial (ya protegido en set_user_activation_status)
            if not (self.existing_username.lower() == SUPERUSER_INIT_USERNAME.lower() and not is_active):
                s_active, m_active = set_user_activation_status(self.existing_username, is_active, current_admin_role)
                if not s_active: messagebox.showerror("Error Estado", m_active, parent=self); return # Fallar si no se pudo actualizar estado
            
            # Cambiar contraseña si se proporcionó una nueva
            if password:
                s_pass, m_pass = update_user_password(self.existing_username, password)
                if not s_pass: messagebox.showerror("Error Contraseña", m_pass, parent=self); return

            self.result = {"success": True, "username": self.existing_username}
        else: # Creando
            success_create, msg_or_id = create_system_user(username, password, role, is_active)
            if success_create:
                self.result = {"success": True, "username": username, "id": msg_or_id}
            else:
                self.status_label_user_dialog.config(text=f"Error: {msg_or_id}"); return
        
        self.destroy()

    def on_cancel_user_dialog(self): # Renombrado
        self.result = None; self.destroy()


class ChangePasswordDialog(tk.Toplevel):
    def __init__(self, parent_frame, controller, username_to_change: str):
        # (Sin cambios funcionales aquí, asumir que usa constantes importadas correctamente si aplica)
        super().__init__(parent_frame)
        self.controller = controller
        self.username_to_change = username_to_change
        self.result = None

        self.title(f"Cambiar Contraseña para '{username_to_change}'")
        self.transient(parent_frame)
        self.grab_set()
        self.resizable(False, False)

        self.new_password_var = tk.StringVar()
        self.confirm_password_var = tk.StringVar()
        
        self.create_form_widgets_change_pass() # Renombrado
        # No hay grid_form_widgets separado, está dentro de create_

        self.protocol("WM_DELETE_WINDOW", self.on_cancel_change_pass) # Renombrado
        self.center_dialog_change_pass() # Renombrado
        self.new_password_entry.focus_set()
        self.wait_window()

    def center_dialog_change_pass(self):
        self.update_idletasks()
        # ... (código de centrado ...)
        parent_x = self.master.winfo_rootx(); parent_y = self.master.winfo_rooty()
        parent_width = self.master.winfo_width(); parent_height = self.master.winfo_height()
        dialog_width = self.winfo_width(); dialog_height = self.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        if dialog_width > 0 and dialog_height > 0: self.geometry(f"+{x}+{y}")


    def create_form_widgets_change_pass(self): # Renombrado
        self.form_frame = ttk.Frame(self, padding=20, style="TFrame")
        
        info_label = ttk.Label(self.form_frame, text=f"Nueva contraseña para: {self.username_to_change}")
        new_pass_label = ttk.Label(self.form_frame, text="Nueva Contraseña (*):")
        self.new_password_entry = ttk.Entry(self.form_frame, textvariable=self.new_password_var, show="*", width=35)
        confirm_pass_label = ttk.Label(self.form_frame, text="Confirmar Nueva Contraseña (*):")
        self.confirm_password_entry = ttk.Entry(self.form_frame, textvariable=self.confirm_password_var, show="*", width=35)
        self.status_label_change_pass = ttk.Label(self.form_frame, text="", style="Error.TLabel", wraplength=300) # Nombre único

        self.btn_save = ttk.Button(self.form_frame, text="Guardar Contraseña", command=self.on_save_change_pass, style="TButton") # Renombrado
        self.btn_cancel = ttk.Button(self.form_frame, text="Cancelar", command=self.on_cancel_change_pass, style="TButton") # Renombrado
        
        info_label.grid(row=0, column=0, columnspan=2, pady=(0,10), sticky="w")
        new_pass_label.grid(row=1, column=0, sticky="w", pady=2)
        self.new_password_entry.grid(row=1, column=1, sticky="ew", pady=2)
        confirm_pass_label.grid(row=2, column=0, sticky="w", pady=2)
        self.confirm_password_entry.grid(row=2, column=1, sticky="ew", pady=2)
        self.status_label_change_pass.grid(row=3, column=0, columnspan=2, pady=(5,10), sticky="ew")
        
        buttons_frame = ttk.Frame(self.form_frame, style="TFrame")
        buttons_frame.grid(row=4, column=0, columnspan=2, pady=(10,0), sticky="e")
        self.btn_save.pack(side="right", padx=(5,0))
        self.btn_cancel.pack(side="right")

        self.form_frame.columnconfigure(1, weight=1)
        self.form_frame.pack(fill="both", expand=True)

    def on_save_change_pass(self): # Renombrado
        new_password = self.new_password_var.get()
        confirm_password = self.confirm_password_var.get()

        if not new_password: self.status_label_change_pass.config(text="Nueva contraseña no puede estar vacía."); return
        if new_password != confirm_password: self.status_label_change_pass.config(text="Contraseñas no coinciden."); return
        
        is_strong, strength_msg = check_password_strength(new_password)
        if not is_strong: self.status_label_change_pass.config(text=f"Contraseña: {strength_msg}"); return

        success, msg = update_user_password(self.username_to_change, new_password)
        if success: self.result = {"success": True}; self.destroy()
        else: self.status_label_change_pass.config(text=f"Error: {msg}")

    def on_cancel_change_pass(self): # Renombrado
        self.result = None; self.destroy()


# --- Para probar este frame de forma aislada ---
if __name__ == "__main__":
    class MockAppController(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Test UserManagementFrame")
            self.geometry("900x700") # Más grande para UserManagement
            self.current_user_info = {
                "id": 0, "username": "super_tester_user_mgmt", "role": ROLE_SUPERUSER, "is_active": True
            }
            self.style = ttk.Style(self)
            try: self.style.theme_use("clam")
            except: pass
            self.style.configure("Error.TLabel", foreground="red")
            self.style.configure("TFrame", background="#F0F0F0") # Asegurar que los TFrame tengan bg

        def show_frame_by_name(self, frame_name):
            print(f"Mock Controller: Show frame '{frame_name}' (no action)")

    # Mock de funciones de auth para que el frame no falle al cargar
    _original_get_all_system_users = get_all_system_users
    def _mock_get_all_users(exclude_superuser=False):
        print(f"Mock: get_all_system_users(exclude_superuser={exclude_superuser})")
        users = [
            {"id": 1, "username": "johndoe", "role": ROLE_DATA_MANAGER, "is_active": 1, "last_login_at": datetime.now().isoformat()}, # Uso de datetime
            {"id": 2, "username": "janedoe", "role": ROLE_STAFF_MEMBER, "is_active": 0, "last_login_at": None}
        ]
        if not exclude_superuser: # Si exclude es False, incluir superusuario
            users.insert(0, {"id": 0, "username": SUPERUSER_INIT_USERNAME.lower(), "role": ROLE_SUPERUSER, "is_active": 1, "last_login_at": datetime.now().isoformat()}) # Uso de datetime
        return users
    get_all_system_users = _mock_get_all_users # Aplicar mock

    # Mock para get_system_user_by_username
    _original_get_user = get_system_user_by_username
    def _mock_get_user(username):
        print(f"Mock: get_system_user_by_username({username})")
        if username == "johndoe": return {"id": 1, "username": "johndoe", "role": ROLE_DATA_MANAGER, "is_active": 1}
        if username == SUPERUSER_INIT_USERNAME.lower(): return {"id": 0, "username": SUPERUSER_INIT_USERNAME.lower(), "role": ROLE_SUPERUSER, "is_active": 1}
        return None
    get_system_user_by_username = _mock_get_user

    # Mocks para las funciones de actualización (solo devuelven éxito para que el diálogo se cierre)
    def _mock_update_role(u,r,ar): print(f"Mock: update_role({u}, {r}, {ar})"); return True, "Rol (mock) actualizado"
    update_user_role = _mock_update_role
    def _mock_set_active(u,s,ar): print(f"Mock: set_active({u}, {s}, {ar})"); return True, "Estado (mock) actualizado"
    set_user_activation_status = _mock_set_active
    def _mock_update_pass(u,p): print(f"Mock: update_pass({u}, '****')"); return True, "Pass (mock) actualizada"
    update_user_password = _mock_update_pass
    def _mock_create_user(u,p,r,a): print(f"Mock: create_user({u}, '****', {r}, {a})"); return True, "123" # ID mock
    create_system_user = _mock_create_user


    app_mock_ctrl = MockAppController()
    user_mgmt_view_test = UserManagementFrame(app_mock_ctrl, app_mock_ctrl)
    user_mgmt_view_test.pack(fill="both", expand=True)
    user_mgmt_view_test.on_show_frame() # Para que cargue la lista inicial
    
    app_mock_ctrl.mainloop()

    # Restaurar originales
    get_all_system_users = _original_get_all_system_users
    get_system_user_by_username = _original_get_user
    # (restaurar el resto si es necesario para un script de pruebas más largo)