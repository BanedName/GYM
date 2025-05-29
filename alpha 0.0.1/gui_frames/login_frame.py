# gimnasio_mgmt_gui/gui_frames/login_frame.py
# Frame para la pantalla de inicio de sesión de la aplicación.

import tkinter as tk
from tkinter import ttk, messagebox
import datetime

# Importaciones
try:
    from config import APP_NAME # Para el título o mensajes
    from core_logic.auth import attempt_user_login # Función de login del backend
    # from .base_frame import BaseFrame # Si tuviéramos una clase base para todos los frames (opcional)
except ImportError as e:
    messagebox.showerror("Error de Carga (LoginFrame)", f"No se pudieron cargar componentes necesarios para Login.\nError: {e}")
    raise # Relanzar para que main_gui lo capture si es necesario o para detener la carga del frame


class LoginFrame(ttk.Frame):
    """
    Frame que maneja la interfaz de inicio de sesión del usuario.
    """
    def __init__(self, parent, controller):
        super().__init__(parent, style="TFrame") # Usar el estilo base para Frames
        self.parent = parent
        self.controller = controller # Referencia a la instancia de GymManagerApp (main_gui.py)

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        self.create_widgets()
        self.grid_widgets() # Separar creación de la disposición

        # Enfocar el campo de usuario al mostrar el frame
        self.username_entry.focus_set()

    def create_widgets(self):
        """Crea los widgets del frame de login."""
        # --- Frame contenedor interno para centrar los widgets ---
        # Esto ayuda a que no ocupen todo el ancho del LoginFrame si este es grande
        self.center_frame = ttk.Frame(self, style="TFrame", padding=(20, 20, 20, 20))
        # (el padding se aplica alrededor de los hijos del center_frame)

        # --- Título ---
        self.title_label = ttk.Label(
            self.center_frame,
            text=f"Bienvenido a {APP_NAME}",
            style="Header.TLabel" # Usar el estilo definido en main_gui
        )
        self.login_prompt_label = ttk.Label(
            self.center_frame,
            text="Por favor, inicie sesión para continuar:",
            style="TLabel" # Estilo normal de etiqueta
        )

        # --- Campo de Usuario ---
        self.username_label = ttk.Label(self.center_frame, text="Usuario:", style="TLabel")
        self.username_entry = ttk.Entry(
            self.center_frame,
            textvariable=self.username_var,
            width=35, # Ancho del campo
            font=(self.controller.style.lookup("TEntry", "font")) # Tomar la fuente del estilo global
        )
        # Bind Enter key para pasar al campo de contraseña
        self.username_entry.bind("<Return>", lambda event: self.password_entry.focus_set())


        # --- Campo de Contraseña ---
        self.password_label = ttk.Label(self.center_frame, text="Contraseña:", style="TLabel")
        self.password_entry = ttk.Entry(
            self.center_frame,
            textvariable=self.password_var,
            show="*", # Mostrar asteriscos para la contraseña
            width=35,
            font=(self.controller.style.lookup("TEntry", "font"))
        )
        # Bind Enter key para intentar el login
        self.password_entry.bind("<Return>", self.handle_login_attempt)


        # --- Botón de Login ---
        self.login_button = ttk.Button(
            self.center_frame,
            text="Iniciar Sesión",
            command=self.handle_login_attempt, # Llama a la función de este frame
            style="TButton", # Estilo por defecto para botones
            width=15 # Ancho del botón
        )

        # --- Etiqueta de Estado/Error ---
        self.status_label = ttk.Label(self.center_frame, text="", style="Error.TLabel") # Usará color rojo

    def grid_widgets(self):
        """Organiza los widgets en el frame usando grid."""
        # Configurar el LoginFrame para que centre su contenido (center_frame)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1) # Si quieres centrar verticalmente también
        
        # Colocar el center_frame, pero no hacer que se expanda, para que los widgets se agrupen
        self.center_frame.grid(row=0, column=0, padx=10, pady=10, sticky="") # No usar sticky="nsew"

        # Widgets dentro de center_frame
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        self.login_prompt_label.grid(row=1, column=0, columnspan=2, pady=(0, 20), sticky="ew")

        self.username_label.grid(row=2, column=0, padx=(0, 5), pady=5, sticky="w")
        self.username_entry.grid(row=2, column=1, pady=5, sticky="ew")

        self.password_label.grid(row=3, column=0, padx=(0, 5), pady=5, sticky="w")
        self.password_entry.grid(row=3, column=1, pady=5, sticky="ew")

        self.status_label.grid(row=4, column=0, columnspan=2, pady=(10, 5), sticky="ew")
        self.login_button.grid(row=5, column=0, columnspan=2, pady=(10, 0))

        # Permitir que la columna 1 (donde están los Entry) se expanda
        self.center_frame.columnconfigure(1, weight=1)

    def handle_login_attempt(self, event=None): # event=None para que funcione con botón y Enter
        """Maneja el intento de login cuando se pulsa el botón o Enter."""
        username = self.username_var.get()
        password = self.password_var.get()

        if not username or not password:
            self.show_status_message("Usuario y contraseña son obligatorios.", is_error=True)
            return

        self.login_button.config(state="disabled") # Deshabilitar botón durante el intento
        self.show_status_message("Verificando credenciales...", is_error=False, color="blue")
        self.update_idletasks() # Forzar actualización de la UI

        # Llamar a la lógica de autenticación del backend (core_logic.auth)
        user_info = attempt_user_login(username, password)

        self.login_button.config(state="normal") # Rehabilitar botón

        if user_info:
            if "error" in user_info: # Si attempt_user_login devuelve un dict de error
                error_type = user_info["error"]
                if error_type == "account_locked":
                    unlock_time_str = user_info.get("unlock_time", "desconocido")
                    try:
                        # Formatear el tiempo de desbloqueo para que sea legible
                        unlock_dt = datetime.fromisoformat(unlock_time_str)
                        unlock_time_ui = self.controller.style.lookup("TLabel", "font") # Usar una utilidad de utils
                        unlock_time_ui = unlock_dt.strftime("%H:%M:%S del %d/%m/%Y") # utils.format_datetime_for_ui()
                    except:
                        unlock_time_ui = "pronto"
                    self.show_status_message(f"Cuenta bloqueada. Intente de nuevo después de las {unlock_time_ui}.", is_error=True)
                elif error_type == "account_inactive":
                    self.show_status_message("Su cuenta está inactiva. Contacte al administrador.", is_error=True)
                else:
                    self.show_status_message("Usuario o contraseña incorrectos.", is_error=True)
            else: # Login exitoso
                self.show_status_message("¡Inicio de sesión exitoso!", is_error=False, color="green")
                # Notificar a la app principal (controller) para cambiar de frame
                self.controller.user_logged_in(user_info)
                # El frame de login se ocultará, pero limpiamos los campos para la próxima vez
                self.clear_login_fields() # Lo haremos en on_show_frame
        else:
            self.show_status_message("Usuario o contraseña incorrectos.", is_error=True)
            self.password_var.set("") # Limpiar solo la contraseña en caso de error
            self.password_entry.focus_set()


    def show_status_message(self, message: str, is_error: bool, color: str | None = None):
        """Muestra un mensaje en la etiqueta de estado."""
        self.status_label.config(text=message)
        if color:
            self.status_label.config(foreground=color)
        elif is_error:
            self.status_label.config(style="Error.TLabel") # Usará el estilo definido
        else:
            self.status_label.config(style="Success.TLabel") # O un "Info.TLabel" si lo tienes


    def clear_login_fields(self):
        """Limpia los campos de usuario y contraseña, y el mensaje de estado."""
        self.username_var.set("")
        self.password_var.set("")
        self.status_label.config(text="", style="Error.TLabel") # Resetear estilo
        self.username_entry.focus_set() # Poner foco en el campo de usuario


    def on_show_frame(self, data_to_pass: dict | None = None):
        """
        Llamado por el controlador (main_gui) cuando este frame se muestra.
        'data_to_pass' no se usa mucho en LoginFrame, pero es bueno tener el método.
        """
        self.clear_login_fields()
        self.username_entry.focus_set()
        # Podríamos cambiar el texto del título si, por ejemplo, se mostró un mensaje de sesión expirada.
        # if data_to_pass and "message" in data_to_pass:
        #     self.show_status_message(data_to_pass["message"], is_error=False)


# --- Para probar este frame de forma aislada (si fuera necesario) ---
if __name__ == "__main__":
    # Esta parte es solo para pruebas rápidas del layout del LoginFrame.
    # No realizará un login real a menos que mockees el controller y auth.
    # Se recomienda probar la integración completa ejecutando main_gui.py.

    # Crear un mock del controller para que el frame no falle
    class MockController(tk.Tk):
        def __init__(self):
            super().__init__()
            self.title("Test LoginFrame")
            self.style = ttk.Style(self) # Necesario para que el frame pueda usar estilos
            try: self.style.theme_use("clam")
            except: pass
            self.style.configure("Header.TLabel", font=("Arial", 18, "bold")) # Mockear estilos necesarios
            self.style.configure("Error.TLabel", foreground="red")
            self.style.configure("Success.TLabel", foreground="green")


        def user_logged_in(self, user_info):
            print("Mock Login Exitoso:", user_info)
            messagebox.showinfo("Login Test", "¡Login exitoso (simulado)!")
            self.destroy()

        # Añadir otros métodos o atributos que LoginFrame espere del controller
        # Por ejemplo, si usa self.controller.show_frame_by_name, mockearlo.

    # --- Mocks de la lógica de auth (muy simplificado) ---
    def mock_attempt_user_login(username, password):
        if username == "test" and password == "test":
            return {"id": 1, "username": "testuser", "role": "Admin Datos", "is_active": True}
        elif username == "lock" and password == "lock":
            return {"error": "account_locked", "unlock_time": datetime.now().isoformat()}
        return None

    # Sobrescribir la función real con el mock para esta prueba
    original_attempt_user_login = attempt_user_login
    attempt_user_login = mock_attempt_user_login


    app_test_controller = MockController()
    login_view = LoginFrame(app_test_controller, app_test_controller)
    login_view.pack(fill="both", expand=True)
    
    # Centrar la ventana de prueba
    w, h = 450, 350
    ws = app_test_controller.winfo_screenwidth()
    hs = app_test_controller.winfo_screenheight()
    x = (ws/2) - (w/2)
    y = (hs/2) - (h/2)
    app_test_controller.geometry('%dx%d+%d+%d' % (w, h, x, y))

    app_test_controller.mainloop()

    # Restaurar la función original después de la prueba (si importa para otras pruebas en el mismo run)
    attempt_user_login = original_attempt_user_login