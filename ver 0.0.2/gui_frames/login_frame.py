# gimnasio_mgmt_gui/gui_frames/login_frame.py
# Frame para la pantalla de inicio de sesión de la aplicación.

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime # <-- CORRECCIÓN: Importar la clase datetime del módulo datetime

# Importaciones de la aplicación
try:
    from config import APP_NAME
    from core_logic.auth import attempt_user_login
    # from .base_frame import BaseFrame # Opcional
except ImportError as e:
    messagebox.showerror("Error de Carga (LoginFrame)", f"No se pudieron cargar componentes.\nError: {e}")
    raise


class LoginFrame(ttk.Frame):
    def __init__(self, parent, controller):
        # (El constructor __init__ como lo tenías)
        super().__init__(parent, style="TFrame")
        self.parent = parent
        self.controller = controller

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        self.create_widgets()
        self.grid_widgets()

        self.columnconfigure(0, weight=1); self.rowconfigure(0, weight=1) # Para que el frame ocupe todo el espacio disponible
        self.center_frame.columnconfigure(1, weight=1)
        self.center_frame.rowconfigure(0, weight=1)

        self.username_entry.focus_set()

    def create_widgets(self):
        # (El método create_widgets como lo tenías)
        self.center_frame = ttk.Frame(self, style="TFrame", padding=(20, 20, 20, 20))
        self.title_label = ttk.Label(self.center_frame, text=f"Bienvenido a {APP_NAME}", style="Header.TLabel")
        self.login_prompt_label = ttk.Label(self.center_frame, text="Inicie sesión para continuar:", style="TLabel")
        self.username_label = ttk.Label(self.center_frame, text="Usuario:", style="TLabel")
        self.username_entry = ttk.Entry(self.center_frame, textvariable=self.username_var, width=35, font=(self.controller.style.lookup("TEntry", "font")))
        self.username_entry.bind("<Return>", lambda event: self.password_entry.focus_set())
        self.password_label = ttk.Label(self.center_frame, text="Contraseña:", style="TLabel")
        self.password_entry = ttk.Entry(self.center_frame, textvariable=self.password_var, show="*", width=35, font=(self.controller.style.lookup("TEntry", "font")))
        self.password_entry.bind("<Return>", self.handle_login_attempt)
        self.login_button = ttk.Button(self.center_frame, text="Iniciar Sesión", command=self.handle_login_attempt, style="TButton", width=15)
        self.status_label = ttk.Label(self.center_frame, text="", style="Error.TLabel")

    def grid_widgets(self):
        # (El método grid_widgets como lo tenías)
        self.columnconfigure(0, weight=1); self.rowconfigure(0, weight=1) 
        self.center_frame.grid(row=0, column=0, padx=10, pady=10, sticky="")
        self.title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="ew")
        self.login_prompt_label.grid(row=1, column=0, columnspan=2, pady=(0, 20), sticky="ew")
        self.username_label.grid(row=2, column=0, padx=(0, 5), pady=5, sticky="w")
        self.username_entry.grid(row=2, column=1, pady=5, sticky="ew")
        self.password_label.grid(row=3, column=0, padx=(0, 5), pady=5, sticky="w")
        self.password_entry.grid(row=3, column=1, pady=5, sticky="ew")
        self.status_label.grid(row=4, column=0, columnspan=2, pady=(10, 5), sticky="ew")
        self.login_button.grid(row=5, column=0, columnspan=2, pady=(10, 0))
        self.center_frame.columnconfigure(1, weight=1)


    def handle_login_attempt(self, event=None):
        username = self.username_var.get()
        password = self.password_var.get()

        if not username or not password:
            self.show_status_message("Usuario y contraseña son obligatorios.", is_error=True)
            return

        self.login_button.config(state="disabled")
        self.show_status_message("Verificando...", is_error=False, color="blue") # Mensaje más genérico
        self.update_idletasks()

        user_info = attempt_user_login(username, password) # De core_logic.auth

        self.login_button.config(state="normal")

        if user_info:
            if "error" in user_info:
                error_type = user_info["error"]
                if error_type == "account_locked":
                    unlock_time_str = user_info.get("unlock_time", "desconocido")
                    unlock_time_ui = "pronto" # Fallback
                    if unlock_time_str != "desconocido":
                        try:
                            # --- CORRECCIÓN: Usar datetime.fromisoformat (clase.metodo) ---
                            unlock_dt = datetime.fromisoformat(unlock_time_str)
                            # Para formatear, sería mejor usar una función de utils si la tuviéramos
                            # o asegurar que UI_DISPLAY_DATETIME_FORMAT esté importado
                            try:
                                from config import UI_DISPLAY_DATETIME_FORMAT
                                unlock_time_ui = unlock_dt.strftime(UI_DISPLAY_DATETIME_FORMAT)
                            except ImportError: # Si no se pudo importar UI_DISPLAY_DATETIME_FORMAT
                                unlock_time_ui = unlock_dt.strftime("%H:%M:%S del %d/%m/%Y") # Fallback de formato
                        except ValueError: # Si unlock_time_str no es un ISO format válido
                            print(f"ADVERTENCIA (LoginFrame): Formato de unlock_time_str no es ISO: {unlock_time_str}")
                    self.show_status_message(f"Cuenta bloqueada. Intente tras las {unlock_time_ui}.", is_error=True)
                elif error_type == "account_inactive":
                    self.show_status_message("Su cuenta está inactiva.", is_error=True)
                else: # Otros errores de login que devuelvan auth.py
                    self.show_status_message(user_info.get("message", "Usuario o contraseña incorrectos."), is_error=True)
            else: # Login exitoso
                self.show_status_message("¡Inicio de sesión exitoso!", is_error=False, color="green")
                self.controller.user_logged_in(user_info)
                # clear_login_fields se llamará en on_show_frame si se vuelve
        else: # Si attempt_user_login devuelve None (error genérico o usuario/pass no coinciden)
            self.show_status_message("Usuario o contraseña incorrectos.", is_error=True)
            self.password_var.set("")
            self.password_entry.focus_set()

    def show_status_message(self, message: str, is_error: bool, color: str | None = None):
        # (Sin cambios funcionales)
        self.status_label.config(text=message)
        if color: self.status_label.config(foreground=color)
        elif is_error: self.status_label.config(style="Error.TLabel")
        else: self.status_label.config(style="Success.TLabel")


    def clear_login_fields(self):
        # (Sin cambios funcionales)
        self.username_var.set("")
        self.password_var.set("")
        self.status_label.config(text="", style="Error.TLabel") # Resetear a estilo de error por si acaso
        # self.username_entry.focus_set() # Se hará en on_show_frame


    def on_show_frame(self, data_to_pass: dict | None = None):
        # (Sin cambios funcionales)
        self.clear_login_fields()
        self.username_entry.focus_set()


# --- Para probar este frame de forma aislada (si fuera necesario) ---
if __name__ == "__main__":
    class MockController(tk.Tk):
        # (MockController como antes)
        def __init__(self):
            super().__init__()
            self.title("Test LoginFrame"); self.style = ttk.Style(self)
            try: self.style.theme_use("clam")
            except: pass
            self.style.configure("Header.TLabel", font=("Arial", 18, "bold"))
            self.style.configure("Error.TLabel", foreground="red"); self.style.configure("Success.TLabel", foreground="green")
            self.style.configure("TEntry", font=("Arial", 10)) # Para que lookup no falle
        def user_logged_in(self, user_info): print("Mock Login OK:", user_info); messagebox.showinfo("Login Test", "Login OK (simulado)!"); self.destroy()

    original_attempt_user_login = None
    # Necesitamos que attempt_user_login exista para poder sobreescribirla, aunque sea un mock
    if 'attempt_user_login' in globals():
        original_attempt_user_login = attempt_user_login
    
    def mock_attempt_user_login(username, password):
        if username == "test" and password == "test":
            return {"id": 1, "username": "testuser", "role": "Data Manager", "is_active": True}
        elif username == "lock" and password == "lock":
            # --- CORRECCIÓN: Usar datetime.now (clase.metodo) ---
            return {"error": "account_locked", "unlock_time": datetime.now().isoformat()}
        return None

    attempt_user_login = mock_attempt_user_login

    app_test_controller = MockController()
    login_view = LoginFrame(app_test_controller, app_test_controller)
    login_view.pack(fill="both", expand=True)
    
    w, h = 450, 350; ws=app_test_controller.winfo_screenwidth(); hs=app_test_controller.winfo_screenheight(); x=(ws/2)-(w/2); y=(hs/2)-(h/2)
    app_test_controller.geometry('%dx%d+%d+%d' % (w,h,x,y))
    app_test_controller.mainloop()

    if original_attempt_user_login: # Restaurar si se guardó
        attempt_user_login = original_attempt_user_login