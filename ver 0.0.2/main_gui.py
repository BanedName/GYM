# gimnasio_mgmt_gui/main_gui.py
# Punto de entrada principal y controlador de la aplicación GUI GymManager Pro.

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys # Para sys.exit en caso de errores críticos

# --- IMPORTACIONES DE CONFIGURACIÓN Y LÓGICA DEL NÚCLEO ---
# Estas importaciones son cruciales para el arranque de la aplicación.
# Asumimos que main_gui.py se ejecuta desde el directorio raíz del proyecto (gimnasio_mgmt_gui/),
# lo que pone ese directorio en el sys.path y permite estas importaciones.
try:
    import config # Configuraciones globales de la aplicación

    # Módulos de inicialización del backend
    from core_logic.utils import setup_app_data_directories
    from core_logic.database import create_or_verify_tables
    from core_logic.auth import initialize_superuser_account
    
    # Los frames específicos de la GUI se importarán dinámicamente a través de _get_frame_class.
    # No es necesario listarlos aquí si se usa ese método de carga.
    
except ImportError as e_initial_import:
    # Este es un error crítico que impide que la aplicación funcione.
    error_title = "Error Crítico de Arranque"
    error_message = (
        f"Fallo al cargar componentes esenciales de la aplicación.\n"
        f"Asegúrese de que la estructura del proyecto es correcta y todos los módulos están presentes.\n\n"
        f"Detalle del error:\n{e_initial_import}\n\n"
        "La aplicación se cerrará."
    )
    print(f"ERROR FATAL (main_gui.py - Importaciones): {error_message}")
    try: # Intentar mostrar un messagebox si Tkinter está disponible
        root_error = tk.Tk()
        root_error.withdraw() # Ocultar la ventana principal si solo es para el error
        messagebox.showerror(error_title, error_message)
    except Exception as e_tk_init_fail:
        print(f"Error adicional: Tkinter no pudo inicializar para mostrar el mensaje de error: {e_tk_init_fail}")
    finally:
        sys.exit(1) # Salir con código de error

# --- CLASE PRINCIPAL DE LA APLICACIÓN GUI ---
class GymManagerApp(tk.Tk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.title(config.UI_MAIN_WINDOW_TITLE) # Título de config.py
        self.set_window_geometry()           # Método para tamaño y posición
        self.set_app_icon()                  # Método para el icono

        # Estado de la aplicación
        self.current_user_info = None # Almacenará datos del usuario logueado

        # Configuración de estilos globales TTK
        self.style = ttk.Style(self)
        self.configure_global_styles()       # Método para aplicar estilos visuales

        # Contenedor principal para los frames (vistas)
        self.main_container = ttk.Frame(self, style="App.TFrame") # Estilo base para el contenedor
        self.main_container.pack(side="top", fill="both", expand=True)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        # Caché para las instancias de los frames
        self.frames_cache = {}

        # --- Realizar tareas críticas de inicialización ---
        if not self.perform_application_setup():
            # Si el setup falla (ej. no se puede crear BD), la app no puede continuar.
            # perform_application_setup ya debería haber cerrado la ventana si es necesario.
            return # Evitar continuar si el setup falló

        # Mostrar el frame de Login al iniciar
        self.show_frame_by_name("LoginFrame")


    def perform_application_setup(self) -> bool:
        """Realiza las tareas de configuración inicial críticas y necesarias."""
        print_prefix_setup = "INFO (main_gui.py - Setup):"

        # 1. Asegurar directorios de datos de la aplicación
        print(f"{print_prefix_setup} Verificando/Creando directorios de datos...")
        if not setup_app_data_directories(): # De core_logic.utils
            messagebox.showerror(
                "Error Crítico de Directorios",
                "No se pudieron crear los directorios necesarios para la aplicación.\n"
                "Verifique los permisos de escritura en la carpeta del proyecto.\n"
                "La aplicación se cerrará."
            )
            self.destroy()
            return False
        print(f"{print_prefix_setup} Directorios de datos listos.")

        # 2. Inicializar la base de datos (crear tablas si no existen)
        print(f"{print_prefix_setup} Verificando/Creando tablas de la base de datos...")
        if not create_or_verify_tables(): # De core_logic.database
             messagebox.showerror(
                "Error Crítico de Base de Datos",
                "No se pudo inicializar la base de datos (crear/verificar tablas).\n"
                "Verifique la consola para más detalles. La aplicación se cerrará."
            )
             self.destroy()
             return False
        print(f"{print_prefix_setup} Base de datos lista.")
        
        # 3. Inicializar la cuenta de superusuario
        print(f"{print_prefix_setup} Verificando/Creando cuenta de superusuario...")
        initialize_superuser_account() # De core_logic.auth
        print(f"{print_prefix_setup} Cuenta de superusuario lista.")
        
        print(f"{print_prefix_setup} Configuración inicial completada exitosamente.")
        return True


    def set_window_geometry(self, width_percent=0.85, height_percent=0.9):
        # (Como lo teníamos, con tamaños mínimos ajustados)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        w = int(screen_width * width_percent)
        h = int(screen_height * height_percent)
        min_w, min_h = 900, 700
        w = max(w, min_w)
        h = max(h, min_h)
        x = (screen_width // 2) - (w // 2)
        y = (screen_height // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(min_w, min_h)


    def set_app_icon(self):
        # (Como lo teníamos, intentando cargar .ico en Win y .png en otros)
        try:
            icon_filename = "app_icon.ico" if os.name == 'nt' else "app_icon.png"
            icon_path = os.path.join(config.PROJECT_ROOT_DIR, "assets", "icons", icon_filename)
            if os.path.exists(icon_path):
                if os.name == 'nt':
                    self.iconbitmap(default=icon_path)
                else:
                    try:
                        img = tk.PhotoImage(file=icon_path)
                        self.tk.call('wm', 'iconphoto', self._w, img)
                    except tk.TclError as e_icon_load:
                        print(f"ADVERTENCIA (Icono): Fallo al cargar '{icon_filename}' con PhotoImage: {e_icon_load}. Para PNG/JPG en Linux/macOS, puede necesitarse Pillow.")
            else:
                print(f"ADVERTENCIA (Icono): Archivo de icono no encontrado: '{icon_path}'")
        except Exception as e_icon_general:
            print(f"ADVERTENCIA (Icono): Error inesperado al establecer icono: {e_icon_general}")


    def configure_global_styles(self):
        # (Como lo teníamos, con los estilos ttk definidos)
        try:
            self.style.theme_use(config.UI_DEFAULT_THEME)
        except tk.TclError: # Manejar caso donde el tema no esté disponible
            print(f"ADVERTENCIA (Estilos): Tema TTK '{config.UI_DEFAULT_THEME}' no disponible. Usando tema por defecto.")

        bg_main_container = "#EAECEE" # Gris muy claro, casi blanco
        bg_frames = "#FFFFFF"        # Blanco para los frames internos
        text_color = "#2C3E50"       # Azul oscuro para texto
        header_color = "#2980B9"     # Azul más brillante para cabeceras
        error_color = "#C0392B"      # Rojo
        success_color = "#27AE60"    # Verde
        link_color = "#3498DB"       # Azul para enlaces
        button_bg = "#3498DB"       # Azul principal para botones
        button_active_bg = "#2980B9" # Azul más oscuro para hover/active

        self.style.configure("TFrame", background=bg_frames)
        self.style.configure("App.TFrame", background=bg_main_container)

        self.style.configure("TLabel", font=(config.UI_DEFAULT_FONT_FAMILY, config.UI_DEFAULT_FONT_SIZE_NORMAL), 
                             padding=config.UI_DEFAULT_WIDGET_PADDING, background=bg_frames, foreground=text_color)
        self.style.configure("Header.TLabel", font=(config.UI_DEFAULT_FONT_FAMILY, config.UI_DEFAULT_FONT_SIZE_HEADER, "bold"), 
                             foreground=header_color, background=bg_frames, anchor="center") # Centrar Headers
        self.style.configure("SubHeader.TLabel", font=(config.UI_DEFAULT_FONT_FAMILY, config.UI_DEFAULT_FONT_SIZE_LARGE, "normal"), 
                             foreground=header_color, background=bg_frames)
        self.style.configure("Error.TLabel", foreground=error_color, background=bg_frames)
        self.style.configure("Success.TLabel", foreground=success_color, background=bg_frames)

        self.style.configure("TButton", font=(config.UI_DEFAULT_FONT_FAMILY, config.UI_DEFAULT_FONT_SIZE_MEDIUM, "bold"),
                             padding=(10, 6), foreground="white", borderwidth=1) # Padding X,Y
        self.style.map("TButton",
                       background=[('disabled', '#BDC3C7'), ('pressed', '#1F618D'), ('active', button_active_bg), ('!active', button_bg)],
                       relief=[('pressed', 'sunken'), ('!pressed', 'raised')])
        
        self.style.configure("Link.TButton", relief="flat", foreground=link_color, 
                             font=(config.UI_DEFAULT_FONT_FAMILY, config.UI_DEFAULT_FONT_SIZE_NORMAL, "underline"))
        self.style.map("Link.TButton", foreground=[('active', '#E74C3C'), ('hover', button_active_bg)])
        
        entry_font = (config.UI_DEFAULT_FONT_FAMILY, config.UI_DEFAULT_FONT_SIZE_MEDIUM)
        self.style.configure("TEntry", font=entry_font, padding=(5,4), fieldbackground="white", relief="solid", borderwidth=1)
        self.style.configure("TCombobox", font=entry_font, padding=5)
        self.style.map('TCombobox', fieldbackground=[('readonly','white'), ('disabled', bg_frames)])
        self.style.map('TCombobox', selectbackground=[('readonly', '#E0EFFF')])
        self.style.map('TCombobox', selectforeground=[('readonly', 'black')])

        self.style.configure("Treeview", rowheight=30, font=(config.UI_DEFAULT_FONT_FAMILY, config.UI_DEFAULT_FONT_SIZE_NORMAL), 
                             fieldbackground="white", background="white")
        self.style.configure("Treeview.Heading", font=(config.UI_DEFAULT_FONT_FAMILY, config.UI_DEFAULT_FONT_SIZE_MEDIUM, "bold"), 
                             background="#BDC3C7", relief="raised", padding=(8, 6)) # Gris más claro para cabeceras
        self.style.map("Treeview.Heading", relief=[('active','groove'),('pressed','sunken')])
        
        self.style.configure("TLabelframe", padding=10, background=bg_frames, relief="groove", borderwidth=1)
        self.style.configure("TLabelframe.Label", font=(config.UI_DEFAULT_FONT_FAMILY, config.UI_DEFAULT_FONT_SIZE_MEDIUM, "bold"), 
                             padding=(0,0,0,5), background=bg_frames, foreground=header_color)
        
        self.configure(background=bg_main_container) # Fondo de la ventana tk.Tk


    def _get_frame_class(self, frame_name_str: str) -> type[ttk.Frame] | None:
        """
        Importa dinámicamente y devuelve la clase del Frame (de gui_frames/)
        basado en su nombre de cadena.
        """
        # --- MAPA DE TODOS LOS FRAMES DE LA APLICACIÓN ---
        # Clave: Nombre de cadena usado en show_frame_by_name
        # Valor: (ruta_del_módulo_en_gui_frames, NombreDeLaClaseDelFrame)
        frame_map = {
            "LoginFrame": ("gui_frames.login_frame", "LoginFrame"),
            "MainMenuFrame": ("gui_frames.main_menu_frame", "MainMenuFrame"),
            "UserManagementFrame": ("gui_frames.user_management_frame", "UserManagementFrame"),
            "MemberManagementFrame": ("gui_frames.member_management_frame", "MemberManagementFrame"),
            "FinanceManagementFrame": ("gui_frames.finance_management_frame", "FinanceManagementFrame"),
            
            # --- PLACEHOLDERS PARA FRAMES AÚN NO CREADOS (Comentados para evitar error si no existen) ---
            # "AttendanceFrame": ("gui_frames.attendance_frame", "AttendanceFrame"),
            # "ReportsFrame": ("gui_frames.reports_frame", "ReportsFrame"),
            # "SystemSettingsFrame": ("gui_frames.system_settings_frame", "SystemSettingsFrame"),
        }
        # --- FIN DEL MAPA DE FRAMES ---

        if frame_name_str not in frame_map:
            error_msg = f"Frame desconocido solicitado: '{frame_name_str}'. Verifique el 'frame_map' en main_gui.py."
            print(f"ERROR CRÍTICO (main_gui.py - _get_frame_class): {error_msg}")
            messagebox.showerror("Error de Navegación Crítico", error_msg + "\nContacte al administrador.")
            return None # No se pudo encontrar la definición del frame
        
        module_path_str, class_name_str = frame_map[frame_name_str]
        
        try:
            # Importar el módulo que contiene la clase del frame
            frame_module = __import__(module_path_str, fromlist=[class_name_str])
            # Obtener la clase del frame desde el módulo importado
            frame_class_definition = getattr(frame_module, class_name_str)
            return frame_class_definition
        except ImportError as e_imp:
            detailed_error = (f"Fallo al importar el módulo '{module_path_str}' (para el frame '{frame_name_str}').\n"
                              f"Asegúrese que el archivo '{module_path_str.replace('.', '/')}.py' existe en 'gui_frames/' "
                              f"y que no tiene errores de sintaxis que impidan su importación.\n\n"
                              f"Detalle del sistema: {e_imp}")
            print(f"ERROR (main_gui.py - _get_frame_class): {detailed_error}")
            messagebox.showerror("Error al Cargar Componente de UI", detailed_error)
            return None
        except AttributeError:
            detailed_error = f"La clase '{class_name_str}' no se encontró dentro del módulo '{module_path_str}'."
            print(f"ERROR (main_gui.py - _get_frame_class): {detailed_error}")
            messagebox.showerror("Error al Cargar Componente de UI", detailed_error)
            return None
        except Exception as e_general_load: # Capturar otros errores inesperados
            detailed_error = f"Error inesperado al intentar cargar el componente '{frame_name_str}':\n{e_general_load}"
            print(f"ERROR (main_gui.py - _get_frame_class): {detailed_error}")
            messagebox.showerror("Error Inesperado de Carga de UI", detailed_error)
            return None


    def show_frame_by_name(self, frame_name_to_show: str, data_to_pass: dict | None = None):
        """Muestra un frame específico, creándolo o reutilizándolo de la caché."""
        frame_instance = self.frames_cache.get(frame_name_to_show)

        if not frame_instance:
            FrameClass = self._get_frame_class(frame_name_to_show)
            if not FrameClass: return # Error ya mostrado

            try:
                frame_instance = FrameClass(parent=self.main_container, controller=self)
            except Exception as e_frame_create:
                messagebox.showerror("Error al Crear Panel UI", 
                                     f"No se pudo inicializar el panel '{frame_name_to_show}'.\n"
                                     f"Consulte la consola para más detalles.\nError: {e_frame_create}")
                print(f"ERROR (main_gui.py - show_frame): Fallo al instanciar {frame_name_to_show}. Error: {e_frame_create}")
                return
            
            self.frames_cache[frame_name_to_show] = frame_instance
            frame_instance.grid(row=0, column=0, sticky="nsew")

        # Actualizar el frame si tiene un método 'on_show_frame'
        if hasattr(frame_instance, "on_show_frame") and callable(frame_instance.on_show_frame):
            self.after(10, lambda f=frame_instance, d=data_to_pass: f.on_show_frame(d))
        elif hasattr(frame_instance, "give_focus") and callable(frame_instance.give_focus):
            self.after(20, lambda f=frame_instance: f.give_focus()) # Dar foco si no hay on_show

        frame_instance.tkraise() # Traer al frente
        self.update_app_title()


    def update_app_title(self):
        """Actualiza el título de la ventana, añadiendo info del usuario si está logueado."""
        base_title = config.MAIN_WINDOW_TITLE
        if self.current_user_info:
            username = self.current_user_info.get('username', 'Usuario')
            role = self.current_user_info.get('role', 'Desconocido')
            self.title(f"{config.APP_NAME} - {username} [{role}]")
        else:
            self.title(base_title)


    def user_logged_in(self, user_session_info: dict):
        """Callback para cuando un usuario inicia sesión exitosamente."""
        self.current_user_info = user_session_info
        log_msg = f"Usuario '{user_session_info.get('username')}' logueado con rol '{user_session_info.get('role')}'."
        print(f"INFO (main_gui.py - Login): {log_msg}")
        self.update_app_title()
        
        # Opcional: Limpiar el frame de login de la caché para resetear su estado.
        if "LoginFrame" in self.frames_cache:
            # self.frames_cache["LoginFrame"].destroy() # Si se quiere destruir completamente
            del self.frames_cache["LoginFrame"]
        
        self.show_frame_by_name("MainMenuFrame")


    def user_logged_out(self):
        """Callback para cerrar la sesión del usuario."""
        if self.current_user_info:
            print(f"INFO (main_gui.py - Logout): Usuario '{self.current_user_info.get('username', '(desconocido)')}' ha cerrado sesión.")
        
        self.current_user_info = None
        self.update_app_title()
        
        # Limpiar caché de frames que puedan contener datos específicos del usuario
        # o cuyo estado deba reiniciarse al cambiar de usuario.
        frames_to_clear_on_logout = [
            "MainMenuFrame", "UserManagementFrame", "MemberManagementFrame", 
            "FinanceManagementFrame", "AttendanceFrame", "ReportsFrame", "SystemSettingsFrame"
            # Añadir cualquier otro frame sensible al estado de sesión
        ]
        for frame_key in frames_to_clear_on_logout:
            if frame_key in self.frames_cache:
                frame_to_remove = self.frames_cache.pop(frame_key) # Quita y devuelve el frame
                # frame_to_remove.destroy() # Destruir el frame y sus widgets (más completo)
                # Simplemente quitarlo de la caché fuerza su recreación la próxima vez.
        
        self.show_frame_by_name("LoginFrame") # Volver a la pantalla de login

    


# --- PUNTO DE ENTRADA PRINCIPAL DE LA APLICACIÓN ---
if __name__ == "__main__":
    # Configuración opcional de un manejador global de excepciones de Tkinter
    # para errores no capturados en callbacks, etc.
    # def global_tk_exception_reporter(exc_type, exc_value, exc_traceback):
    #     import traceback
    #     error_details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    #     full_error_message = (f"Error inesperado en la aplicación (Tkinter callback):\n\n"
    #                           f"{exc_value}\n\nDetalles:\n{error_details}")
    #     print(f"ERROR GLOBAL TKINTER: {full_error_message}")
    #     messagebox.showerror("Error Inesperado en UI", full_error_message)
    # tk.Tk.report_callback_exception = global_tk_exception_reporter # Activar

    print(f"INFO (main_gui.py): Iniciando {config.APP_NAME} v{config.APP_VERSION}...")
    try:
        app = GymManagerApp() # Crear la instancia de la aplicación
        app.mainloop()        # Iniciar el bucle principal de eventos de Tkinter
        print(f"INFO (main_gui.py): {config.APP_NAME} cerrado normalmente.")
    except Exception as e_startup_fatal:
        # Este try-except captura errores muy tempranos (antes del mainloop o si mainloop falla críticamente)
        final_error_msg = (f"Error fatal e irrecuperable durante el arranque o ejecución de la aplicación:\n"
                           f"{e_startup_fatal}\n\nLa aplicación no puede continuar.")
        print(f"ERROR CRÍTICO (main_gui.py - __main__): {final_error_msg}")
        try:
            root_fatal = tk.Tk()
            root_fatal.withdraw()
            messagebox.showerror("Error Fatal de la Aplicación", final_error_msg)
        except:
            pass # Si incluso Tkinter falla aquí, ya no hay más que hacer.
        finally:
            sys.exit(1) # Salir con un código de error indicando fallo
