# gimnasio_mgmt_gui/gui_frames/main_menu_frame.py
# Frame para el menú principal de la aplicación después del login.

import tkinter as tk
from tkinter import ttk, messagebox

# Importaciones
try:
    from config import APP_NAME, ROLE_SUPERUSER, ROLE_SYSTEM_ADMIN, ROLE_DATA_MANAGER, ROLE_STAFF_MEMBER
    from core_logic.auth import check_user_permission # Para habilitar/deshabilitar opciones
except ImportError as e:
    messagebox.showerror("Error de Carga (MainMenuFrame)", f"No se pudieron cargar componentes necesarios para el Menú Principal.\nError: {e}")
    raise


class MainMenuFrame(ttk.Frame):
    """
    Frame que muestra el menú principal y las opciones de navegación
    basadas en el rol del usuario actual.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, style="TFrame") # Usar el estilo base
        self.parent = parent
        self.controller = controller # Instancia de GymManagerApp

        self.buttons_config = [] # Lista para guardar la configuración de los botones
        self.action_buttons = {} # Diccionario para guardar las instancias de los botones

        self.create_widgets()
        # El layout se hará en on_show_frame para actualizar los botones según el usuario

    def create_widgets(self):
        """Crea los widgets base del frame del menú principal."""

        # --- Mensaje de Bienvenida Dinámico ---
        self.welcome_label = ttk.Label(
            self,
            text="", # Se actualizará en on_show_frame
            style="Header.TLabel", # Estilo para encabezados
            anchor="center"
        )
        self.welcome_label.pack(pady=(20, 10), padx=20, fill="x")

        self.info_label = ttk.Label(
            self,
            text="Seleccione una opción para comenzar:",
            style="TLabel",
            anchor="center"
        )
        self.info_label.pack(pady=(0, 20), padx=20, fill="x")

        # --- Contenedor para los Botones de Acción/Navegación ---
        # Usaremos un frame con grid para los botones, para mejor alineación.
        self.buttons_container = ttk.Frame(self, style="TFrame", padding=(30,10))
        self.buttons_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Configurar grid para centrar los botones
        self.buttons_container.columnconfigure(0, weight=1) # Columna de padding izquierda
        self.buttons_container.columnconfigure(1, weight=0) # Columna para los botones (no expandir)
        self.buttons_container.columnconfigure(2, weight=1) # Columna de padding derecha
        # Añadir filas de padding arriba y abajo si es necesario
        # self.buttons_container.rowconfigure(0, weight=1) # Para padding superior
        # ... (filas para botones)
        # self.buttons_container.rowconfigure(X, weight=1) # Para padding inferior

        # --- Botón de Cerrar Sesión ---
        self.logout_button = ttk.Button(
            self, # Lo colocamos directamente en el MainMenuFrame, no en buttons_container
            text="Cerrar Sesión",
            command=self.handle_logout,
            style="TButton",
            width=15
        )
        self.logout_button.pack(pady=(10, 20), padx=20, side="bottom") # Abajo y centrado horizontalmente (pack default)

    def define_navigation_buttons(self):
        """
        Define la configuración de los botones de navegación.
        Cada entrada: (texto_boton, comando_o_nombre_frame, roles_requeridos)
        """
        self.buttons_config = [
            ("Gestionar Miembros", "MemberManagementFrame", [ROLE_DATA_MANAGER, ROLE_SYSTEM_ADMIN]),
            ("Registrar Asistencia", "AttendanceFrame", [ROLE_STAFF_MEMBER, ROLE_DATA_MANAGER]), # Placeholder
            ("Gestionar Finanzas", "FinanceManagementFrame", [ROLE_DATA_MANAGER]),
            ("Generar Informes", "ReportsFrame", [ROLE_DATA_MANAGER, ROLE_SYSTEM_ADMIN]), # Placeholder
            ("Gestión de Usuarios del Sistema", "UserManagementFrame", [ROLE_SYSTEM_ADMIN]),
            ("Configuración del Sistema", "SystemSettingsFrame", [ROLE_SUPERUSER, ROLE_SYSTEM_ADMIN]), # Placeholder
        ]
        # El Superusuario tiene acceso a todo implícitamente por check_user_permission

    def layout_navigation_buttons(self):
        """Crea y dispone los botones de navegación basados en el rol del usuario."""
        # Limpiar botones existentes (si se llama múltiples veces)
        for widget in self.buttons_container.winfo_children():
            widget.destroy()
        self.action_buttons.clear()

        if not self.controller.current_user_info:
            # Esto no debería pasar si se navega correctamente al MainMenuFrame
            messagebox.showerror("Error de Sesión", "No hay información de usuario. Volviendo al login.")
            self.controller.user_logged_out() # Forzar logout
            return

        current_role = self.controller.current_user_info.get('role')
        row_num = 0 # Para el grid en buttons_container

        for text, target_frame_name_or_command, required_roles in self.buttons_config:
            if check_user_permission(current_role, required_roles):
                button = ttk.Button(
                    self.buttons_container,
                    text=text,
                    # El comando será navegar al frame
                    command=lambda tf=target_frame_name_or_command: self.navigate_to_frame(tf),
                    style="TButton",
                    width=35 # Ancho unificado para los botones de menú
                )
                # Colocar el botón en la columna central del grid
                button.grid(row=row_num, column=1, pady=7, sticky="ew") # "ew" para que se expanda horizontalmente
                self.action_buttons[target_frame_name_or_command] = button
                row_num += 1
        
        if not self.action_buttons: # Si no hay botones para el rol actual (poco probable pero posible)
            no_options_label = ttk.Label(self.buttons_container, text="No tiene opciones de menú disponibles.", style="Error.TLabel")
            no_options_label.grid(row=0, column=1, pady=10)


    def navigate_to_frame(self, frame_name: str):
        """Navega al frame especificado usando el controlador principal."""
        print(f"INFO (MainMenu): Navegando a '{frame_name}'...")
        self.controller.show_frame_by_name(frame_name)


    def handle_logout(self):
        """Maneja el cierre de sesión."""
        if messagebox.askyesno("Cerrar Sesión", "¿Está seguro de que desea cerrar la sesión actual?"):
            self.controller.user_logged_out()


    def on_show_frame(self, data_to_pass: dict | None = None):
        """
        Llamado por el controlador (main_gui) cuando este frame se muestra.
        Actualiza el mensaje de bienvenida y dispone los botones.
        """
        if self.controller.current_user_info:
            username = self.controller.current_user_info.get('username', 'Usuario')
            self.welcome_label.config(text=f"¡Bienvenido de nuevo, {username}!")
        else:
            # Si no hay info de usuario, algo raro pasó. Regresar a Login.
            self.welcome_label.config(text="Error de sesión.")
            self.controller.user_logged_out() # Forzar logout
            return
        
        # Definir y colocar los botones de navegación, ya que los permisos pueden haber cambiado
        # o es la primera vez que se muestra para este usuario.
        self.define_navigation_buttons()
        self.layout_navigation_buttons()

        # Poner foco en el primer botón de acción si existe
        self.give_focus()


    def give_focus(self):
        """Intenta poner el foco en el primer botón de acción disponible."""
        # Buscar el primer botón en el orden en que se añadieron
        first_button_key = next(iter(self.action_buttons), None)
        if first_button_key and self.action_buttons[first_button_key].winfo_exists():
            self.action_buttons[first_button_key].focus_set()
        else:
            self.logout_button.focus_set() # Fallback al botón de logout


# --- Para probar este frame de forma aislada ---
if __name__ == "__main__":
    # Esta sección es solo para pruebas visuales del layout de MainMenuFrame.
    # Las navegaciones no funcionarán sin el controller real de main_gui.py.

    class MockAppController(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Test MainMenuFrame")
            self.geometry("600x500")
            self.current_user_info = { # Simular un usuario logueado para probar permisos
                "id": 1,
                "username": "Tester",
                "role": ROLE_DATA_MANAGER, # Probar con diferentes roles: ROLE_SYSTEM_ADMIN, ROLE_STAFF_MEMBER
                "is_active": True
            }
            # Mock de estilos
            self.style = ttk.Style(self)
            try: self.style.theme_use("clam")
            except: pass
            self.style.configure("Header.TLabel", font=("Arial", 18, "bold"))
            self.style.configure("TLabel", font=("Arial", 10))
            self.style.configure("TButton", font=("Arial", 10, "bold"), padding=5)
            self.style.configure("Error.TLabel", foreground="red")

        def user_logged_out(self):
            print("Mock Logout: Sesión cerrada.")
            messagebox.showinfo("Logout Test", "Sesión cerrada (simulado).")
            self.destroy()

        def show_frame_by_name(self, frame_name):
            print(f"Mock Navigate: Intentando navegar a '{frame_name}'...")
            messagebox.showinfo("Navegación", f"Simulando navegación a:\n{frame_name}")

    app_mock = MockAppController()
    main_menu_view = MainMenuFrame(app_mock, app_mock)
    main_menu_view.pack(fill="both", expand=True)
    
    # Llamar a on_show_frame manualmente para que los widgets se actualicen como si se mostrara el frame
    main_menu_view.on_show_frame()
    
    app_mock.mainloop()