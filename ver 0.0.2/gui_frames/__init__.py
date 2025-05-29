# gimnasio_mgmt_gui/gui_frames/__init__.py

# Este archivo, incluso estando vacío, convierte al directorio 'gui_frames'
# en un paquete de Python.

# Esto permite importar clases Frame de forma estructurada desde main_gui.py
# y otros posibles módulos de la GUI.
# Ejemplo: from gui_frames.login_frame import LoginFrame

# En proyectos más grandes, este archivo podría también usarse para definir
# una API pública para el paquete, controlando qué se importa con 'from gui_frames import *'
# o para realizar alguna inicialización específica del paquete de frames,
# pero para nuestra aplicación, vacío es suficiente por ahora.

class BaseFrame(ttk.Frame):
    """Frame base que proporciona funcionalidad comun a todos los frames."""
    def __init__(self, parent, controller):
        super().__init__(parent, style='TFrame')
        self.parent = parent
        self.controller = controller

        def on_show_frame(self, data_to_pass: dict | None = None):
            """Método a llamar cuando se muestra este frame."""
            pass

        def give_focus(self):
            """Dado que este frame es un widget de Tkinter,
            podemos darle el foco para que pueda recibir eventos."""
            pass
        