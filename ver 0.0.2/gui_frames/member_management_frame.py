# gimnasio_mgmt_gui/gui_frames/member_management_frame.py
# Frame para la gestión completa de miembros (socios) del gimnasio.
#IGNORE CALL 280
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk # Requiere: pip install Pillow
import os
import shutil
from datetime import date, datetime # <-- CORRECCIÓN: Importar 'date' y 'datetime'
from decimal import Decimal # <-- CORRECCIÓN: Importar 'Decimal'
import config
from gui_frames import BaseFrame

# Al inicio de gimnasio_mgmt_gui/gui_frames/member_management_frame.py

from config import (
        MEMBER_STATUS_OPTIONS_LIST, DEFAULT_MEMBERSHIP_PLANS, APP_DATA_ROOT_DIR,
        MEMBER_PHOTOS_SUBDIR_NAME, CURRENCY_DISPLAY_SYMBOL,
        DEFAULT_NEW_MEMBER_STATUS_ON_CREATION,
        UI_DEFAULT_FONT_FAMILY, # Asegurar que está aquí
        UI_DEFAULT_FONT_SIZE_NORMAL # Asegurar que está aquí
        # ... (y cualquier otra constante de config que se use directamente)
    )
    # ... (resto de importaciones) ...
# Importaciones de la aplicación
try:
    from config import (
        MEMBER_STATUS_OPTIONS_LIST, DEFAULT_MEMBERSHIP_PLANS, APP_DATA_ROOT_DIR,
        MEMBER_PHOTOS_SUBDIR_NAME, CURRENCY_DISPLAY_SYMBOL,
        DEFAULT_NEW_MEMBER_STATUS_ON_CREATION #Añadir si se usa explícitamente o para claridad
    )
    from core_logic.members import (
        add_new_member, get_all_members_summary, get_member_by_internal_id,
        update_member_details, add_membership_to_member,
        get_all_memberships_for_member, get_member_active_membership
    )
    from core_logic.utils import (
        sanitize_text_input, parse_string_to_date, format_date_for_ui,
        calculate_age, generate_internal_id, ensure_directory_exists,
        parse_string_to_decimal, format_currency_for_display, convert_date_to_db_string
    )
except ImportError as e:
    messagebox.showerror("Error de Carga (MemberManagement)", f"No se pudieron cargar componentes.\nError: {e}")
    raise


class MemberManagementFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="TFrame")
        self.parent = parent
        self.controller = controller

        self.selected_member_internal_id = None
        self.member_photo_path = None # Ruta de la foto original si se está editando y no se cambia
        self.temp_photo_path_for_dialog = None # Ruta de la foto seleccionada en el diálogo, antes de guardar

        self.create_widgets()
        self.grid_widgets()
        self.load_member_list()

    def create_widgets(self):
        # (Sin cambios en create_widgets respecto al último código, a menos que los errores sean aquí)
        # ...
        self.top_action_frame = ttk.Frame(self, style="TFrame", padding=10)
        
        self.search_var = tk.StringVar()
        self.search_label = ttk.Label(self.top_action_frame, text="Buscar Miembro (Nombre/ID):")
        self.search_entry = ttk.Entry(self.top_action_frame, textvariable=self.search_var, width=30)
        self.search_entry.bind("<Return>", lambda e: self.load_member_list())
        self.btn_search = ttk.Button(self.top_action_frame, text="Buscar", command=self.load_member_list)
        self.btn_clear_search = ttk.Button(self.top_action_frame, text="Limpiar", command=self.clear_search_and_reload)

        self.btn_add_member = ttk.Button(self.top_action_frame, text="Nuevo Miembro", command=self.open_member_form_dialog)
        self.btn_refresh_list = ttk.Button(self.top_action_frame, text="Refrescar Lista", command=self.load_member_list)

        self.member_list_frame = ttk.Frame(self, style="TFrame", padding=(10,0))
        self.tree_columns = ("internal_id", "full_name", "status", "join_date", "active_plan")
        self.tree_column_names = ("ID Miembro", "Nombre Completo", "Estado", "Fecha Ingreso", "Plan Activo")
        
        self.members_treeview = ttk.Treeview(
            self.member_list_frame, columns=self.tree_columns, show="headings", selectmode="browse"
        )
        for col, name in zip(self.tree_columns, self.tree_column_names):
            width = 180; anchor = "w"
            if col == "internal_id": width = 120
            elif col == "status": width = 100
            elif col == "join_date": width = 120
            self.members_treeview.heading(col, text=name, anchor=anchor)
            self.members_treeview.column(col, width=width, stretch=tk.YES, anchor=anchor)

        self.members_treeview.bind("<<TreeviewSelect>>", self.on_member_selected)
        self.members_treeview.bind("<Double-1>", self.on_member_double_click)

        self.tree_scrollbar_y = ttk.Scrollbar(self.member_list_frame, orient="vertical", command=self.members_treeview.yview)
        self.members_treeview.configure(yscrollcommand=self.tree_scrollbar_y.set)

        self.member_actions_frame = ttk.Frame(self, style="TFrame", padding=10)
        self.btn_view_details = ttk.Button(self.member_actions_frame, text="Ver/Editar Detalles", command=self.open_member_form_dialog_for_edit, state="disabled")
        self.btn_manage_memberships = ttk.Button(self.member_actions_frame, text="Gestionar Membresías", command=self.open_membership_management_dialog, state="disabled")
        self.btn_back_to_main = ttk.Button(slef.top_action_frame, text="Menu Principal", command=self.return_to_main_menu)
        
    def grid_widgets(self):
        # (Sin cambios)
        # ...
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1) 

        self.top_action_frame.grid(row=0, column=0, sticky="ew")
        self.search_label.pack(side="left", padx=(0,5), pady=5)
        self.search_entry.pack(side="left", padx=5, pady=5)
        self.btn_search.pack(side="left", padx=5, pady=5)
        self.btn_clear_search.pack(side="left", padx=(0,20), pady=5)
        self.btn_add_member.pack(side="left", padx=5, pady=5)
        self.btn_refresh_list.pack(side="left", padx=5, pady=5)
        
        self.member_list_frame.grid(row=1, column=0, sticky="nsew")
        self.member_list_frame.columnconfigure(0, weight=1)
        self.member_list_frame.rowconfigure(0, weight=1)
        self.members_treeview.grid(row=0, column=0, sticky="nsew")
        self.tree_scrollbar_y.grid(row=0, column=1, sticky="ns")

        self.member_actions_frame.grid(row=2, column=0, sticky="ew")
        self.btn_view_details.pack(side="left", padx=5, pady=5)
        self.btn_manage_memberships.pack(side="left", padx=5, pady=5)

    def return_to_main_menu(self):
        self.selected_member_internal_id = None
        self.selected_member_photo_path = None
        self.temp_photo_path_for_dialog = None

        # Limpiar cualquier foto temporal si está en uso
        self.controller.show_frame("MainMenuFrame")

    def load_member_list(self, event=None):
        for item in self.members_treeview.get_children():
            self.members_treeview.delete(item)
        
        search_term = sanitize_text_input(self.search_var.get())
        members_data = get_all_members_summary(search_term=search_term if search_term else None)

        for member_item in members_data:
            internal_id = member_item.get('internal_member_id', 'N/A')
            # ... (resto como antes)
            plan_display = "Ninguno"
            # Línea 132 (del error) dentro de esta lógica para obtener el plan activo
            # El error "`date` no está definido" sucedería si `date.today()` se usa aquí sin importar `date`.
            active_plan_info = get_member_active_membership(internal_id)
            if active_plan_info:
                expiry_dt_obj = active_plan_info.get('expiry_date_obj') # Asumimos que get_member_active_membership devuelve esto
                if expiry_dt_obj and expiry_dt_obj >= date.today(): # Uso de 'date'
                     plan_display = f"{active_plan_info['plan_name_at_purchase']} (Exp: {format_date_for_ui(expiry_dt_obj)})"
                else:
                    plan_display = f"{active_plan_info['plan_name_at_purchase']} (Expirado)"
            # ...
            values = (internal_id, member_item.get('full_name', 'N/A'), member_item.get('current_status', 'N/A'), 
                      member_item.get('join_date_ui', 'N/A'), plan_display)
            self.members_treeview.insert("", "end", values=values, iid=internal_id)
        self.deselect_member()

    # (Métodos on_member_selected, on_member_double_click, deselect_member sin cambios)
    def on_member_selected(self, event=None):
        selected_items = self.members_treeview.selection()
        if selected_items:
            self.selected_member_internal_id = selected_items[0]
            self.btn_view_details.config(state="normal")
            self.btn_manage_memberships.config(state="normal")
        else:
            self.deselect_member()
            
    def on_member_double_click(self, event=None):
        if self.selected_member_internal_id:
            self.open_member_form_dialog_for_edit()

    def deselect_member(self):
        self.selected_member_internal_id = None
        self.btn_view_details.config(state="disabled")
        self.btn_manage_memberships.config(state="disabled")


    def open_member_form_dialog(self, for_editing: bool = False):
        member_id_to_edit = self.selected_member_internal_id if for_editing else None
        if for_editing and not member_id_to_edit:
            messagebox.showwarning("Selección Requerida", "Seleccione un miembro para editar.", parent=self)
            return

        title = "Editar Detalles del Miembro" if for_editing else "Registrar Nuevo Miembro"
        
        # Limpiar/preparar path de foto temporal ANTES de abrir el diálogo
        self.temp_photo_path_for_dialog = None 
        
        dialog = MemberFormDialog(self, controller=self.controller, title=title, member_internal_id=member_id_to_edit)
        
        if dialog.result and dialog.result.get("success", False):
            self.load_member_list() 
            action_msg = "actualizado" if for_editing else "registrado"
            messagebox.showinfo(f"Miembro {action_msg.capitalize()}",
                                f"Miembro '{dialog.result.get('full_name', 'N/A')}' {action_msg} exitosamente.", parent=self)
        self.temp_photo_path_for_dialog = None # Limpiar después de cerrar el diálogo

    # (Métodos open_member_form_dialog_for_edit, open_membership_management_dialog sin cambios funcionales)
    def open_member_form_dialog_for_edit(self):
        self.open_member_form_dialog(for_editing=True)

    def open_membership_management_dialog(self):
        if not self.selected_member_internal_id:
            messagebox.showwarning("Selección Requerida", "Seleccione miembro para gestionar membresías.", parent=self)
            return
        
        dialog = MembershipManagementDialog(self, controller=self.controller, member_internal_id=self.selected_member_internal_id)
        if dialog.result and dialog.result.get("data_changed", False):
             self.load_member_list()

    def on_show_frame(self, data_to_pass: dict | None = None):
        self.load_member_list()
        self.give_focus()

    def give_focus(self):
        self.search_entry.focus_set()

    def clear_search_and_reload(self): # Definición si no estaba antes
        self.search_var.set("")
        self.load_member_list()

# --- CLASES DE DIÁLOGO ---
class MemberFormDialog(tk.Toplevel):
    """Diálogo para crear o editar información de un miembro."""
    def __init__(self, parent_frame, controller, title: str, member_internal_id: str | None = None):
        super().__init__(parent_frame)
        self.parent_frame = parent_frame # Instancia de MemberManagementFrame
        self.controller = controller # Instancia de GymManagerApp
        self.member_internal_id: str | None = member_internal_id
        self.result = None 
        
        self._photo_ref_dialog = None # Referencia interna para PhotoImage

        self.title(title)
        self.transient(parent_frame) 
        self.grab_set() 
        self.resizable(False, False)

        # Variables de Tkinter para los campos del formulario
        self.full_name_var = tk.StringVar()
        self.dob_var = tk.StringVar()
        self.gender_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.address1_var = tk.StringVar()
        self.city_var = tk.StringVar()
        self.postal_code_var = tk.StringVar()
        self.join_date_var = tk.StringVar(value=format_date_for_ui(date.today()))
        self.status_var = tk.StringVar(value=DEFAULT_NEW_MEMBER_STATUS_ON_CREATION)

        self.create_form_widgets()
        
        if self.member_internal_id: # Editando
            self.load_member_data_for_dialog()
        else: # Creando
            # Asegurar placeholder para DOB si está vacío en creación
            if not self.dob_var.get():
                self.restore_placeholder(self.dob_entry, "DD/MM/AAAA")

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.center_dialog()
        self.full_name_entry.focus_set()
        self.wait_window()

    def clear_placeholder(self, widget, placeholder_text):
        if widget.get() == placeholder_text:
            widget.delete(0, tk.END)
            widget.config(foreground='black') # O el color de texto normal

    def restore_placeholder(self, widget, placeholder_text):
        if not widget.get(): # Solo restaurar si el campo está realmente vacío
            widget.insert(0, placeholder_text)
            widget.config(foreground='grey')

    def center_dialog(self):
        self.update_idletasks()
        # Lógica de centrado...
        parent_x = self.master.winfo_rootx()
        parent_y = self.master.winfo_rooty()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        
        # Si el diálogo aún no tiene tamaño (ocurre antes de la primera visualización)
        # se puede intentar darle un tamaño por defecto o esperar a que se dibuje.
        # Aquí se asume que ya tiene algún tamaño o que el centrado relativo funciona.
        if dialog_width == 1 and dialog_height == 1: # Común si se llama antes de pack/grid
            # Estimar un tamaño o re-llamar después del primer pack/grid
            # Por ahora, si esto pasa, el centrado puede no ser perfecto la primera vez
            # print("WARN: Dialog dimensions not yet available for precise centering.")
            pass

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        # Solo aplicar geometría si las dimensiones son válidas
        if dialog_width > 1 and dialog_height > 1: # Evitar tamaño 1x1 que a veces reporta Tkinter
             self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        else: # Si no hay dimensiones, al menos posicionar
             self.geometry(f"+{x}+{y}")


    def create_form_widgets(self):
        main_frame = ttk.Frame(self, padding=(20, 15, 20, 15), style="TFrame")
        main_frame.pack(fill="both", expand=True)

        # Layout: 2 columnas de campos principales, 1 para foto
        main_frame.columnconfigure(1, weight=1) # Campos
        main_frame.columnconfigure(3, weight=1) # Segunda columna de campos (si hay)
        main_frame.columnconfigure(4, weight=0, minsize=160) # Foto

        row_idx = 0
        pady_fields = (0, 5) # Padding vertical entre filas de campos
        padx_labels = (0, 5)
        padx_fields_col2 = (15, 0) # Padding izquierdo para segunda columna de campos

        # Nombre Completo (ocupa dos columnas de campos)
        ttk.Label(main_frame, text="Nombre Completo (*):").grid(row=row_idx, column=0, sticky="w", pady=pady_fields)
        self.full_name_entry = ttk.Entry(main_frame, textvariable=self.full_name_var)
        self.full_name_entry.grid(row=row_idx, column=1, columnspan=3, sticky="ew", pady=pady_fields) # Ocupa hasta la columna 3
        row_idx += 1

        # --- Fila para DOB y Género ---
        ttk.Label(main_frame, text="Fecha Nac.:").grid(row=row_idx, column=0, sticky="w", pady=pady_fields, padx=padx_labels)
        self.dob_entry = ttk.Entry(main_frame, textvariable=self.dob_var, width=12)
        self.dob_entry.grid(row=row_idx, column=1, sticky="w", pady=pady_fields)
        self.dob_entry.insert(0, "DD/MM/AAAA")
        self.dob_entry.bind("<FocusIn>", lambda e: self.clear_placeholder(e.widget, "DD/MM/AAAA"))
        self.dob_entry.bind("<FocusOut>", lambda e: self.restore_placeholder(e.widget, "DD/MM/AAAA"))

        ttk.Label(main_frame, text="Género:").grid(row=row_idx, column=2, sticky="w", pady=pady_fields, padx=padx_fields_col2)
        gender_vals = ["", "Masculino", "Femenino", "Otro", "Prefiero no decirlo"]
        self.gender_combo = ttk.Combobox(main_frame, textvariable=self.gender_var, values=gender_vals, state="readonly", width=17)
        self.gender_combo.grid(row=row_idx, column=3, sticky="ew", pady=pady_fields)
        row_idx += 1
        
        # --- Fila para Teléfono y Fecha de Ingreso ---
        ttk.Label(main_frame, text="Teléfono:").grid(row=row_idx, column=0, sticky="w", pady=pady_fields, padx=padx_labels)
        self.phone_entry = ttk.Entry(main_frame, textvariable=self.phone_var, width=18)
        self.phone_entry.grid(row=row_idx, column=1, sticky="w", pady=pady_fields)

        ttk.Label(main_frame, text="Fecha Ingreso (*):").grid(row=row_idx, column=2, sticky="w", pady=pady_fields, padx=padx_fields_col2)
        self.join_date_entry = ttk.Entry(main_frame, textvariable=self.join_date_var, width=12)
        self.join_date_entry.grid(row=row_idx, column=3, sticky="w", pady=pady_fields)
        row_idx += 1

        # --- Dirección (puede ocupar todo el ancho bajo la foto) ---
        ttk.Label(main_frame, text="Dirección:").grid(row=row_idx, column=0, sticky="w", pady=pady_fields, padx=padx_labels)
        self.address1_entry = ttk.Entry(main_frame, textvariable=self.address1_var)
        self.address1_entry.grid(row=row_idx, column=1, columnspan=3, sticky="ew", pady=pady_fields)
        row_idx += 1

        # --- Fila para Ciudad y Código Postal ---
        ttk.Label(main_frame, text="Ciudad:").grid(row=row_idx, column=0, sticky="w", pady=pady_fields, padx=padx_labels)
        self.city_entry = ttk.Entry(main_frame, textvariable=self.city_var, width=25)
        self.city_entry.grid(row=row_idx, column=1, sticky="w", pady=pady_fields)
        
        ttk.Label(main_frame, text="Cód. Postal:").grid(row=row_idx, column=2, sticky="w", pady=pady_fields, padx=padx_fields_col2)
        self.postal_code_entry = ttk.Entry(main_frame, textvariable=self.postal_code_var, width=10)
        self.postal_code_entry.grid(row=row_idx, column=3, sticky="w", pady=pady_fields)
        row_idx += 1

        # --- Fila para Estado ---
        ttk.Label(main_frame, text="Estado (*):").grid(row=row_idx, column=0, sticky="w", pady=pady_fields, padx=padx_labels)
        self.status_combo = ttk.Combobox(main_frame, textvariable=self.status_var, values=MEMBER_STATUS_OPTIONS_LIST, state="readonly", width=17)
        self.status_combo.grid(row=row_idx, column=1, sticky="w", pady=pady_fields)
        if MEMBER_STATUS_OPTIONS_LIST : self.status_var.set(DEFAULT_NEW_MEMBER_STATUS_ON_CREATION)
        row_idx_before_notes = row_idx # Para saber dónde empieza el área de foto

        # --- Sección de Foto (a la derecha de los campos) ---
        # Usamos un LabelFrame para la foto y sus botones
        photo_section_frame = ttk.Labelframe(main_frame, text="Foto Miembro", style="TLabelframe", padding=5)
        photo_section_frame.grid(row=0, column=4, rowspan=row_idx_before_notes + 1, padx=(15,5), pady=pady_fields[1], sticky="nsew")
        photo_section_frame.columnconfigure(0, weight=1)
        photo_section_frame.rowconfigure(0, weight=1) # Label de foto se expande

        self.photo_label = ttk.Label(photo_section_frame, text="(150x150px aprox.)", anchor="center", borderwidth=1, relief="sunken")
        self.photo_label.grid(row=0, column=0, sticky="nsew", pady=(0,5)) 
        
        photo_buttons_subframe = ttk.Frame(photo_section_frame, style="TFrame")
        photo_buttons_subframe.grid(row=1, column=0, pady=(0,0), sticky="ew")
        photo_buttons_subframe.columnconfigure(0, weight=1); photo_buttons_subframe.columnconfigure(1, weight=1)
        ttk.Button(photo_buttons_subframe, text="Cargar...", command=self.select_photo_for_dialog, width=9).grid(row=0, column=0, sticky="ew", padx=(0,2))
        ttk.Button(photo_buttons_subframe, text="Quitar", command=self.remove_photo_for_dialog, width=7).grid(row=0, column=1, sticky="ew", padx=(2,0))
        
        row_idx += 1 # Para notas, debajo de todos los campos, excepto la foto que es lateral

        # --- Notas (tk.Text con Scrollbar) ---
        ttk.Label(main_frame, text="Notas:").grid(row=row_idx, column=0, sticky="nw", pady=(pady_fields[0]+8, pady_fields[1]), padx=padx_labels) 
        notes_container_frame = ttk.Frame(main_frame) # Frame para agrupar Text y Scrollbar
        notes_container_frame.grid(row=row_idx, column=1, columnspan=3, sticky="nsew", pady=pady_fields)
        notes_container_frame.rowconfigure(0, weight=1); notes_container_frame.columnconfigure(0, weight=1)
        
        self.notes_text = tk.Text(notes_container_frame, height=5, width=1, # width=1 y sticky para que se expanda con grid
                                  wrap="word", relief="solid", borderwidth=1,
                                  font=(UI_DEFAULT_FONT_FAMILY, UI_DEFAULT_FONT_SIZE_NORMAL)) # Fuente explícita para tk.Text
        self.notes_text_scrollbar = ttk.Scrollbar(notes_container_frame, orient="vertical", command=self.notes_text.yview)
        self.notes_text.configure(yscrollcommand=self.notes_text_scrollbar.set)
        
        self.notes_text.grid(row=0, column=0, sticky="nsew")
        self.notes_text_scrollbar.grid(row=0, column=1, sticky="ns")
        row_idx += 1

        # --- Botones de Acción del Formulario ---
        dialog_buttons_frame = ttk.Frame(main_frame, style="TFrame")
        dialog_buttons_frame.grid(row=row_idx, column=0, columnspan=5, pady=(20,0), sticky="e") # Abarca todas las columnas
        
        self.btn_save_member = ttk.Button(dialog_buttons_frame, text="Guardar Miembro", command=self.on_save)
        self.btn_save_member.pack(side="right", padx=(5,0))
        
        self.btn_cancel_dialog = ttk.Button(dialog_buttons_frame, text="Cancelar", command=self.on_cancel)
        self.btn_cancel_dialog.pack(side="right")

    def select_photo_for_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Seleccionar Foto del Miembro",
            filetypes=(("Imágenes JPG", "*.jpg;*.jpeg"), ("Imágenes PNG", "*.png"), ("Todos los archivos", "*.*"))
        )
        if filepath:
            self.parent_frame.temp_photo_path_for_dialog = filepath
            self.display_photo_in_dialog(filepath)

    def remove_photo_for_dialog(self):
        self.parent_frame.temp_photo_path_for_dialog = "REMOVE_PHOTO_FLAG"
        if hasattr(self, 'photo_label'):
             self.photo_label.config(image='') 
             self._photo_ref_dialog = None      
             self.photo_label.config(text="Foto Eliminada")

    def display_photo_in_dialog(self, filepath):
        try:
            img = Image.open(filepath)
            # Escalar manteniendo aspecto para caber en aprox 150x150 (o tamaño del label)
            # El photo_label (si se define con width y height en Chars) puede ser difícil de predecir en px.
            # Aquí apuntamos a unas dimensiones visuales razonables.
            label_width_px = self.photo_label.winfo_width() if self.photo_label.winfo_width() > 1 else 150
            label_height_px = self.photo_label.winfo_height() if self.photo_label.winfo_height() > 1 else 150
            
            target_width = min(img.width, label_width_px - 10) # -10 para un pequeño margen
            target_height = min(img.height, label_height_px - 10)

            img_aspect = img.width / img.height
            if target_width / target_height > img_aspect:
                new_height = target_height
                new_width = int(new_height * img_aspect)
            else:
                new_width = target_width
                new_height = int(new_width / img_aspect)
            
            # En caso de que una dimensión sea muy pequeña tras el aspect ratio, recalcular.
            if new_width == 0: new_width = 1
            if new_height == 0: new_height = 1
            
            img.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
            
            photo_image = ImageTk.PhotoImage(img)

            if hasattr(self, 'photo_label'):
                self.photo_label.config(image=photo_image, text="")
                self._photo_ref_dialog = photo_image 
            else:
                print("ADVERTENCIA: photo_label no encontrado al mostrar foto.")

        except FileNotFoundError:
            messagebox.showerror("Error Foto", f"Archivo no encontrado: {filepath}", parent=self)
            if hasattr(self, 'photo_label'): self.photo_label.config(image='', text="Error foto")
            self._photo_ref_dialog = None
            self.parent_frame.temp_photo_path_for_dialog = None # Resetear path temporal
        except Exception as e:
            messagebox.showerror("Error al Cargar Foto", f"No se pudo procesar la imagen.\n{e}\nAsegúrese de tener Pillow instalado y que la imagen es válida.", parent=self)
            if hasattr(self, 'photo_label'): self.photo_label.config(image='', text="Error foto")
            self._photo_ref_dialog = None
            self.parent_frame.temp_photo_path_for_dialog = None

    def load_member_data_for_dialog(self):
        member_id_to_load = self.member_internal_id 
        if not member_id_to_load:
            messagebox.showerror("Error Interno", "ID de miembro no especificado para cargar.", parent=self)
            self.destroy(); return
        
        member_data = get_member_by_internal_id(member_id_to_load)
        if not member_data:
            messagebox.showerror("Error al Cargar", f"No se cargaron datos para ID: {member_id_to_load}.", parent=self)
            self.destroy(); return

        self.full_name_var.set(member_data.get('full_name', ''))
        
        dob_obj = member_data.get('date_of_birth_obj')
        dob_str_ui = format_date_for_ui(dob_obj) if dob_obj else ""
        self.dob_var.set(dob_str_ui)
        if not dob_str_ui: self.restore_placeholder(self.dob_entry, "DD/MM/AAAA")
        else: self.dob_entry.config(foreground='black')

        self.gender_var.set(member_data.get('gender', ''))
        self.phone_var.set(member_data.get('phone_number', ''))
        self.address1_var.set(member_data.get('address_line1', ''))
        self.city_var.set(member_data.get('address_city', ''))
        self.postal_code_var.set(member_data.get('address_postal_code', ''))
        
        join_obj = member_data.get('join_date_obj')
        self.join_date_var.set(format_date_for_ui(join_obj if join_obj else date.today()))
        
        self.status_var.set(member_data.get('current_status', DEFAULT_NEW_MEMBER_STATUS_ON_CREATION))
        
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", member_data.get('notes', ''))
        
        self.parent_frame.member_photo_path = None 
        self._photo_ref_dialog = None 
        
        photo_fn = member_data.get('photo_filename')
        if photo_fn:
            photo_dir_path = os.path.join(APP_DATA_ROOT_DIR, MEMBER_PHOTOS_SUBDIR_NAME)
            full_photo_path = os.path.join(photo_dir_path, photo_fn)
            if os.path.exists(full_photo_path):
                self.display_photo_in_dialog(full_photo_path)
                self.parent_frame.member_photo_path = full_photo_path 
            else:
                if hasattr(self, 'photo_label'): self.photo_label.config(image='', text="Foto (no hallada)")
        else:
            if hasattr(self, 'photo_label'): self.photo_label.config(image='', text="Sin foto asignada")

    def on_save(self):
        full_name = sanitize_text_input(self.full_name_var.get())
        dob_str_ui = sanitize_text_input(self.dob_var.get())
        if dob_str_ui == "DD/MM/AAAA": dob_str_ui = None
        
        gender = self.gender_var.get()
        phone = sanitize_text_input(self.phone_var.get(), allow_empty=True)
        addr1 = sanitize_text_input(self.address1_var.get(), allow_empty=True)
        city = sanitize_text_input(self.city_var.get(), allow_empty=True)
        post_code = sanitize_text_input(self.postal_code_var.get(), allow_empty=True)
        join_date_str_ui = self.join_date_var.get()
        status = self.status_var.get()
        notes = self.notes_text.get("1.0", tk.END).strip()
        
        photo_final_filename_to_db = None

        if not full_name:
            messagebox.showerror("Error Validación", "Nombre completo obligatorio.", parent=self)
            self.full_name_entry.focus_set(); return
        
        parsed_join_date = parse_string_to_date(join_date_str_ui, permissive_formats=True)
        if not parsed_join_date:
             messagebox.showerror("Error Validación", "Fecha de ingreso inválida o vacía.", parent=self)
             self.join_date_entry.focus_set(); return
        
        parsed_dob_date = None
        if dob_str_ui:
            parsed_dob_date = parse_string_to_date(dob_str_ui, permissive_formats=True)
            if not parsed_dob_date:
                 messagebox.showerror("Error Validación", "Fecha de nacimiento inválida.", parent=self)
                 self.dob_entry.focus_set(); return
            if parsed_dob_date > date.today():
                 messagebox.showerror("Error Validación", "Fecha de nacimiento no puede ser futura.", parent=self)
                 self.dob_entry.focus_set(); return

        # Lógica para manejar la foto (como la teníamos, con REMOVE_PHOTO_FLAG)
        photo_action = "keep" 
        new_photo_source_path = None

        if hasattr(self.parent_frame, 'temp_photo_path_for_dialog'): # Comprobar si el atributo existe
            if self.parent_frame.temp_photo_path_for_dialog == "REMOVE_PHOTO_FLAG":
                photo_action = "remove"
            elif self.parent_frame.temp_photo_path_for_dialog is not None:
                photo_action = "new"
                new_photo_source_path = self.parent_frame.temp_photo_path_for_dialog
        
        if photo_action == "new" and new_photo_source_path:
            photos_dir = os.path.join(APP_DATA_ROOT_DIR, MEMBER_PHOTOS_SUBDIR_NAME)
            if not ensure_directory_exists(photos_dir):
                 messagebox.showerror("Error Sistema", "No se pudo acceder a dir de fotos.", parent=self); return
            _, file_extension = os.path.splitext(new_photo_source_path)
            prefix = self.member_internal_id if self.member_internal_id else generate_internal_id("MEMPHO")
            photo_final_filename_to_db = f"{prefix}_{int(datetime.now().timestamp())}{file_extension.lower()}"
            destination_full_path = os.path.join(photos_dir, photo_final_filename_to_db)
            try:
                shutil.copy2(new_photo_source_path, destination_full_path)
                print(f"INFO: Foto copiada a {destination_full_path}")
                if self.member_internal_id and hasattr(self.parent_frame, 'member_photo_path') and self.parent_frame.member_photo_path and \
                   os.path.basename(self.parent_frame.member_photo_path) != photo_final_filename_to_db and \
                   os.path.exists(self.parent_frame.member_photo_path):
                    try: os.remove(self.parent_frame.member_photo_path); print(f"INFO: Foto antigua eliminada: {self.parent_frame.member_photo_path}")
                    except OSError as e_del: print(f"ADVERTENCIA: No se eliminó foto antigua: {e_del}")
            except Exception as e_copy:
                messagebox.showerror("Error Guardar Foto", f"Fallo al copiar: {e_copy}", parent=self)
                photo_final_filename_to_db = os.path.basename(self.parent_frame.member_photo_path or "") or None if self.member_internal_id and hasattr(self.parent_frame, 'member_photo_path') else None
        
        elif photo_action == "remove":
            photo_final_filename_to_db = None
            if self.member_internal_id and hasattr(self.parent_frame, 'member_photo_path') and self.parent_frame.member_photo_path and \
               os.path.exists(self.parent_frame.member_photo_path):
                try: os.remove(self.parent_frame.member_photo_path); print(f"INFO: Foto eliminada: {self.parent_frame.member_photo_path}")
                except OSError as e_del_rem: print(f"ADVERTENCIA: No se eliminó foto al quitarla: {e_del_rem}")
        
        elif photo_action == "keep" and self.member_internal_id and hasattr(self.parent_frame, 'member_photo_path') and self.parent_frame.member_photo_path:
            photo_final_filename_to_db = os.path.basename(self.parent_frame.member_photo_path)

        # Pasar el string de fecha de UI para DOB, add_new_member/update_member_details lo parseará
        if self.member_internal_id:
            success, msg_or_id_backend = update_member_details(
                member_internal_id=self.member_internal_id, full_name=full_name, date_of_birth_str=dob_str_ui, 
                gender=gender, phone_number=phone, address_line1=addr1, address_city=city,
                address_postal_code=post_code, current_status=status, notes=notes,
                photo_filename=photo_final_filename_to_db )
        else:
            success, msg_or_id_backend = add_new_member(
                full_name=full_name, date_of_birth_str=dob_str_ui, gender=gender, phone_number=phone, 
                address_line1=addr1, address_city=city, address_postal_code=post_code, 
                join_date_str=join_date_str_ui, initial_status=status, notes=notes, 
                photo_filename=photo_final_filename_to_db )

        if success:
            self.result = {"success": True, "full_name": full_name, "id": msg_or_id_backend}
            self.destroy()
        else:
            messagebox.showerror("Error al Guardar Miembro", msg_or_id_backend, parent=self)

    def on_cancel(self):
        self.result = None
        self.destroy()

class MembershipManagementDialog(tk.Toplevel):
    def __init__(self, parent_frame, controller, member_internal_id: str):
        super().__init__(parent_frame)
        self.parent_frame = parent_frame
        self.controller = controller
        self.member_internal_id = member_internal_id
        self.result = {"data_changed": False}

        member_data = get_member_by_internal_id(self.member_internal_id) # Ya cierra su conexión
        member_name = member_data.get('full_name', 'Desconocido') if member_data else 'Desconocido'

        self.title(f"Gestionar Membresías de: {member_name}")
        self.transient(parent_frame)
        self.grab_set()
        self.geometry("750x550") # Un poco más ancho
        self.resizable(True, True)

        self.selected_plan_key_var = tk.StringVar()
        # Línea 436 (del error) donde se usa 'date.today()'
        self.purchase_date_var = tk.StringVar(value=format_date_for_ui(date.today())) # Uso de 'date'
        self.custom_price_var = tk.StringVar()

        self.create_membership_dialog_widgets() # Renombrar
        self.load_member_memberships_in_dialog() # Renombrar

        self.protocol("WM_DELETE_WINDOW", self.on_close_membership_dialog) # Renombrar
        self.center_dialog()
        self.wait_window()
        
    def center_dialog(self): # Método para centrar (copiar de MemberFormDialog o hacerla util global)
        self.update_idletasks()
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


    def create_membership_dialog_widgets(self): # Renombrar
        # (Sin cambios funcionales aquí, solo renombrar el método y los que llama)
        main_frame = ttk.Frame(self, padding=10, style="TFrame")
        main_frame.pack(fill="both", expand=True)
        main_frame.rowconfigure(0, weight=1) 
        main_frame.columnconfigure(0, weight=1) 
        
        hist_cols = ("id", "plan_name", "price", "start", "expiry", "sessions", "status_plan") # Cambiado nombre col status
        hist_names = ("ID Memb.", "Nombre Plan", "Pagado", "Inicio", "Expira", "Sesiones", "Estado")
        self.history_tree = ttk.Treeview(main_frame, columns=hist_cols, show="headings", selectmode="browse")
        for col, name in zip(hist_cols, hist_names):
             width = 100; anchor="w"
             if col == "plan_name": width = 180
             elif col == "id": width = 70; anchor="center"
             self.history_tree.heading(col, text=name, anchor=anchor)
             self.history_tree.column(col, width=width, stretch=tk.YES, anchor=anchor)
        self.history_tree.grid(row=0, column=0, sticky="nsew", pady=(0,10))
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=(0,10))

        add_form_frame = ttk.Labelframe(main_frame, text="Añadir Nueva Membresía", style="TLabelframe", padding=10)
        add_form_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        add_form_frame.columnconfigure(1, weight=1)
        add_form_frame.columnconfigure(3, weight=1)

        ttk.Label(add_form_frame, text="Plan:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.plan_display_names_map = {plan_info['nombre_visible_ui']: key for key, plan_info in DEFAULT_MEMBERSHIP_PLANS.items()}
        self.plan_combo = ttk.Combobox(
            add_form_frame, textvariable=self.selected_plan_key_var,
            values=list(self.plan_display_names_map.keys()), state="readonly", width=30
        )
        if list(self.plan_display_names_map.keys()): self.plan_combo.current(0)
        self.plan_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(add_form_frame, text="Fecha Inicio/Compra:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.purchase_date_entry = ttk.Entry(add_form_frame, textvariable=self.purchase_date_var, width=15)
        self.purchase_date_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(add_form_frame, text="Precio Pagado (opcional):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.custom_price_entry = ttk.Entry(add_form_frame, textvariable=self.custom_price_var, width=15)
        self.custom_price_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(add_form_frame, text=CURRENCY_DISPLAY_SYMBOL).grid(row=1, column=1, sticky="w", padx=(120, 0))


        self.btn_add_plan = ttk.Button(add_form_frame, text="Añadir Plan", command=self.save_new_membership_for_member) # Renombrar
        self.btn_add_plan.grid(row=1, column=2, columnspan=2, padx=5, pady=10, sticky="e")

        ttk.Button(main_frame, text="Cerrar", command=self.on_close_membership_dialog).grid(row=2, column=0, columnspan=2, pady=10) # Renombrar


    def load_member_memberships_in_dialog(self): # Renombrar
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        memberships = get_all_memberships_for_member(self.member_internal_id)
        if not memberships:
            self.history_tree.insert("", "end", values=("", "Sin membresías", "", "", "", "", ""))
            return
            
        today = date.today() # Uso de 'date'
        for mem in memberships:
            # (Resto como antes, asegurando que las conversiones de Decimal y Date se hacen)
            # Línea 510 y 514 (de error) estaban aquí o cerca.
            price_paid_decimal = mem.get('price_paid_decimal', Decimal('0')) # Ya debería ser Decimal
            expiry_dt_obj = mem.get('expiry_date_obj') # Ya debería ser objeto date
            
            status_plan_str = "Expirado"
            if expiry_dt_obj and expiry_dt_obj >= today: # Uso de 'date'
                status_plan_str = "Activo" if mem.get('is_current') else "Futuro"
            elif expiry_dt_obj and expiry_dt_obj < today and mem.get('is_current'):
                 status_plan_str = "Expirado (Error estado)"


            values = (
                mem.get('id'), mem.get('plan_name_at_purchase'), format_currency_for_display(price_paid_decimal),
                format_date_for_ui(mem.get('start_date_obj')), format_date_for_ui(expiry_dt_obj),
                f"{mem.get('sessions_remaining', 'N/A')} / {mem.get('sessions_total', 'N/A')}" if mem.get('sessions_total') is not None else "N/A",
                status_plan_str
            )
            self.history_tree.insert("", "end", values=values)


    def save_new_membership_for_member(self): # Renombrar
        selected_plan_display_name = self.selected_plan_key_var.get()
        if not selected_plan_display_name:
            messagebox.showerror("Error", "Seleccione un plan.", parent=self)
            return

        plan_key = self.plan_display_names_map.get(selected_plan_display_name)
        if not plan_key:
             messagebox.showerror("Error Interno", "Clave de plan no hallada.", parent=self)
             return

        purchase_date_str_val = self.purchase_date_var.get() # Renombrar variable
        custom_price_str_val = self.custom_price_var.get() # Renombrar variable

        success, msg = add_membership_to_member(
            member_internal_id=self.member_internal_id, plan_key=plan_key,
            purchase_date_str=purchase_date_str_val,
            custom_price_paid_str=custom_price_str_val if custom_price_str_val else None
        )

        if success:
            messagebox.showinfo("Membresía Añadida", f"ID Membresía BD: {msg}", parent=self)
            self.result["data_changed"] = True
            self.load_member_memberships_in_dialog()
            if list(self.plan_display_names_map.keys()): self.plan_combo.current(0)
            # Línea 561 (de error) donde se usa 'date.today()'
            self.purchase_date_var.set(format_date_for_ui(date.today())) # Uso de 'date'
            self.custom_price_var.set("")
        else:
            messagebox.showerror("Error al Añadir Membresía", msg, parent=self)


    def on_close_membership_dialog(self): # Renombrar
        self.destroy()

# --- (Fin del archivo member_management_frame.py) ---