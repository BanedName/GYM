# gimnasio_mgmt_gui/gui_frames/member_management_frame.py
# Frame para la gestión completa de miembros (socios) del gimnasio.

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk 
import os
import shutil
from datetime import date, datetime 
from decimal import Decimal

# Importaciones de la aplicación
try:
    from config import (
        MEMBER_STATUS_OPTIONS_LIST, DEFAULT_MEMBERSHIP_PLANS, APP_DATA_ROOT_DIR,
        MEMBER_PHOTOS_SUBDIR_NAME, CURRENCY_DISPLAY_SYMBOL,
        DEFAULT_NEW_MEMBER_STATUS_ON_CREATION, UI_DISPLAY_DATE_FORMAT,
        UI_DEFAULT_FONT_FAMILY, UI_DEFAULT_FONT_SIZE_NORMAL # Para el tk.Text en diálogo
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
        self.member_photo_path = None
        self.temp_photo_path_for_dialog = None 

        self.create_and_grid_widgets() # Unificar creación y layout inicial
        self.load_member_list()

    def create_and_grid_widgets(self): # Método combinado
        # Configurar layout del frame principal
        self.columnconfigure(0, weight=1) # Columna principal
        self.rowconfigure(0, weight=0)  # Fila para top_actions
        self.rowconfigure(1, weight=1)  # Fila para member_list_frame (se expande)
        self.rowconfigure(2, weight=0)  # Fila para member_actions_frame
        self.rowconfigure(3, weight=0)  # ### NUEVO ### Fila para bottom_nav_frame

        # --- Frame Superior: Búsqueda y Acciones Principales ---
        self.top_action_frame = ttk.Frame(self, style="TFrame", padding=(10,10,10,5)) # Ajustar padding
        self.top_action_frame.grid(row=0, column=0, sticky="ew", padx=5)
        
        self.search_var = tk.StringVar()
        ttk.Label(self.top_action_frame, text="Buscar Miembro:").pack(side="left", padx=(0,5), pady=5)
        self.search_entry = ttk.Entry(self.top_action_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side="left", padx=5, pady=5)
        self.search_entry.bind("<Return>", lambda e: self.load_member_list())
        ttk.Button(self.top_action_frame, text="Buscar", command=self.load_member_list).pack(side="left", padx=5, pady=5)
        ttk.Button(self.top_action_frame, text="Limpiar", command=self.clear_search_and_reload).pack(side="left", padx=(0,20), pady=5)
        ttk.Button(self.top_action_frame, text="Nuevo Miembro", command=self.open_member_form_dialog).pack(side="left", padx=5, pady=5)
        ttk.Button(self.top_action_frame, text="Refrescar Lista", command=self.load_member_list).pack(side="left", padx=5, pady=5)

        # --- Frame Central: Lista de Miembros ---
        self.member_list_frame = ttk.Frame(self, style="TFrame", padding=(0,0,0,5)) # Quitar padding superior, añadir inferior
        self.member_list_frame.grid(row=1, column=0, sticky="nsew", padx=10) # padx para el frame
        self.member_list_frame.columnconfigure(0, weight=1)
        self.member_list_frame.rowconfigure(0, weight=1)
        
        self.tree_columns = ("internal_id", "full_name", "status", "join_date", "active_plan")
        self.tree_column_names = ("ID Miembro", "Nombre Completo", "Estado", "Fecha Ingreso", "Plan Activo")
        
        self.members_treeview = ttk.Treeview(
            self.member_list_frame, columns=self.tree_columns, show="headings", selectmode="browse"
        )
        for col, name in zip(self.tree_columns, self.tree_column_names):
            # ... (configuración de columnas como antes) ...
            width = 180; anchor = "w"
            if col == "internal_id": width = 120
            elif col == "status": width = 100; anchor = "center"
            elif col == "join_date": width = 120; anchor = "center"
            elif col == "active_plan": width = 220 # Un poco más para el plan y expiración
            self.members_treeview.heading(col, text=name, anchor=anchor)
            self.members_treeview.column(col, width=width, stretch=tk.YES, anchor=anchor)

        self.members_treeview.bind("<<TreeviewSelect>>", self.on_member_selected)
        self.members_treeview.bind("<Double-1>", self.on_member_double_click)
        self.members_treeview.grid(row=0, column=0, sticky="nsew")

        self.tree_scrollbar_y = ttk.Scrollbar(self.member_list_frame, orient="vertical", command=self.members_treeview.yview)
        self.members_treeview.configure(yscrollcommand=self.tree_scrollbar_y.set)
        self.tree_scrollbar_y.grid(row=0, column=1, sticky="ns")

        # --- Frame Inferior: Acciones sobre Miembro Seleccionado ---
        self.member_actions_frame = ttk.Frame(self, style="TFrame", padding=(10,5,10,5))
        self.member_actions_frame.grid(row=2, column=0, sticky="ew", padx=5)
        
        self.btn_view_details = ttk.Button(self.member_actions_frame, text="Ver/Editar Detalles", command=self.open_member_form_dialog_for_edit, state="disabled")
        self.btn_view_details.pack(side="left", padx=5, pady=5)
        self.btn_manage_memberships = ttk.Button(self.member_actions_frame, text="Gestionar Membresías", command=self.open_membership_management_dialog, state="disabled")
        self.btn_manage_memberships.pack(side="left", padx=5, pady=5)
        # Aquí podrían ir más botones como "Registrar Asistencia Directa", "Ver Historial", etc.

        # --- ### NUEVO ### Frame y Botón de Volver ---
        self.bottom_nav_frame = ttk.Frame(self, style="TFrame", padding=(10,5,10,10)) # Padding L,T,R,B
        self.bottom_nav_frame.grid(row=3, column=0, sticky="ew", padx=5) # Nueva fila 3
        
        self.btn_back_to_main = ttk.Button(
            self.bottom_nav_frame, 
            text="<< Volver al Menú Principal", 
            command=self.go_back_to_main_menu # Método que añadiremos
        )
        self.btn_back_to_main.pack(side="left", padx=0, pady=0) # Alineado a la izquierda, sin padding extra si ya lo tiene el frame

    # El método grid_widgets() separado ya no es tan necesario si hacemos el layout en create_and_grid_widgets

    def load_member_list(self, event=None):
        # (Sin cambios funcionales, pero asegurar uso de 'date' importado)
        for item in self.members_treeview.get_children():
            self.members_treeview.delete(item)
        
        search_term = sanitize_text_input(self.search_var.get())
        members_data = get_all_members_summary(search_term=search_term if search_term else None)

        for member_item in members_data:
            internal_id = member_item.get('internal_member_id', 'N/A')
            full_name = member_item.get('full_name', 'N/A')
            status = member_item.get('current_status', 'N/A')
            join_date_ui = member_item.get('join_date_ui', 'N/A')
            
            active_plan_info = get_member_active_membership(internal_id)
            plan_display = "Ninguno Activo" # Texto más claro
            if active_plan_info:
                expiry_dt_obj = active_plan_info.get('expiry_date_obj') 
                if expiry_dt_obj and expiry_dt_obj >= date.today(): # 'date' importado globalmente
                     plan_display = f"{active_plan_info['plan_name_at_purchase']} (Vence: {format_date_for_ui(expiry_dt_obj)})"
                else: # Ya expiró o es None
                    plan_display = f"{active_plan_info['plan_name_at_purchase']} (Expirado)"
            
            values = (internal_id, full_name, status, join_date_ui, plan_display)
            self.members_treeview.insert("", "end", values=values, iid=internal_id)
        self.deselect_member()

    # (Resto de los métodos como on_member_selected, on_member_double_click, deselect_member,
    #  open_member_form_dialog, open_member_form_dialog_for_edit,
    #  open_membership_management_dialog, on_show_frame, give_focus, clear_search_and_reload
    #  permanecen estructuralmente igual)

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
        if self.members_treeview.selection(): # Si algo sigue seleccionado, deseleccionarlo
            self.members_treeview.selection_remove(self.members_treeview.selection())


    def open_member_form_dialog(self, for_editing: bool = False):
        member_id_to_edit = self.selected_member_internal_id if for_editing else None
        if for_editing and not member_id_to_edit:
            messagebox.showwarning("Selección Requerida", "Seleccione un miembro para editar.", parent=self)
            return
        title = "Editar Detalles del Miembro" if for_editing else "Registrar Nuevo Miembro"
        self.temp_photo_path_for_dialog = None 
        dialog = MemberFormDialog(self, controller=self.controller, title=title, member_internal_id=member_id_to_edit)
        if dialog.result and dialog.result.get("success", False):
            self.load_member_list() 
            action_msg = "actualizado" if for_editing else "registrado"
            messagebox.showinfo(f"Miembro {action_msg.capitalize()}",
                                f"Miembro '{dialog.result.get('full_name', 'N/A')}' {action_msg} exitosamente.", parent=self)
        self.temp_photo_path_for_dialog = None

    def open_member_form_dialog_for_edit(self):
        self.open_member_form_dialog(for_editing=True)

    def open_membership_management_dialog(self):
        if not self.selected_member_internal_id:
            messagebox.showwarning("Selección Requerida", "Seleccione miembro para gestionar membresías.", parent=self)
            return
        dialog = MembershipManagementDialog(self, controller=self.controller, member_internal_id=self.selected_member_internal_id)
        if dialog.result and dialog.result.get("data_changed", False):
             self.load_member_list()

    def clear_search_and_reload(self):
        self.search_var.set("")
        self.load_member_list()

    def on_show_frame(self, data_to_pass: dict | None = None):
        self.load_member_list()
        self.give_focus()

    def give_focus(self):
        self.search_entry.focus_set()

    # --- ### NUEVO ### Método para el botón "Volver" ---
    def go_back_to_main_menu(self):
        """Navega de vuelta al MainMenuFrame."""
        self.deselect_member() # Buena práctica deseleccionar antes de salir del frame
        self.controller.show_frame_by_name("MainMenuFrame")


# --- CLASES DE DIÁLOGO (MemberFormDialog, MembershipManagementDialog) ---
# (El código de estas clases permanece igual que en la última versión que te di,
#  asumiendo que las correcciones de importación de `date` y `Decimal` y
#  el uso de constantes de `config` ya están aplicadas dentro de ellas).

# Aquí mantendré las definiciones de las clases de diálogo para completitud,
# asegurando que usan 'date' y 'Decimal' importados.

class MemberFormDialog(tk.Toplevel):
    def __init__(self, parent_frame, controller, title: str, member_internal_id: str | None = None):
        super().__init__(parent_frame)
        self.parent_frame = parent_frame 
        self.controller = controller
        self.member_internal_id = member_internal_id
        self.result = None
        # self.parent_frame.temp_photo_path_for_dialog será usado
        
        self.title(title)
        self.transient(parent_frame)
        self.grab_set()
        self.resizable(False, False)

        self.full_name_var = tk.StringVar()
        self.dob_var = tk.StringVar() 
        self.gender_var = tk.StringVar()
        self.phone_var = tk.StringVar()
        self.address1_var = tk.StringVar()
        self.city_var = tk.StringVar()
        self.postal_code_var = tk.StringVar()
        self.join_date_var = tk.StringVar(value=format_date_for_ui(date.today())) 
        self.status_var = tk.StringVar(value=DEFAULT_NEW_MEMBER_STATUS_ON_CREATION) 

        self.create_member_form_dialog_widgets()
        if self.member_internal_id:
            self.load_member_data_for_dialog()

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.center_dialog()
        self.full_name_entry.focus_set()
        self.wait_window()

    def center_dialog(self):
        # ... (código de centrado) ...
        self.update_idletasks()
        parent_x = self.master.winfo_rootx()
        parent_y = self.master.winfo_rooty()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        if dialog_width > 0 and dialog_height > 0: # Solo si ya tiene dimensiones
             self.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}") # Especificar tamaño también


    def create_member_form_dialog_widgets(self):
        # (Código como antes, asegurar que la fuente de tk.Text usa las constantes importadas)
        # ...
        main_frame = ttk.Frame(self, padding=20, style="TFrame")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(1, weight=1) 
        main_frame.columnconfigure(2, weight=0, minsize=160) # Ancho mínimo para foto
        main_frame.columnconfigure(3, weight=0) # Para botón de quitar foto

        row = 0
        ttk.Label(main_frame, text="Nombre Completo (*):").grid(row=row, column=0, sticky="w", pady=3)
        self.full_name_entry = ttk.Entry(main_frame, textvariable=self.full_name_var, width=40)
        self.full_name_entry.grid(row=row, column=1, sticky="ew", pady=3)
        row+=1

        self.photo_label = ttk.Label(main_frame, text="Foto (150x150px)", anchor="center", borderwidth=1, relief="solid", width=20, height=10) # Ajustar h/w según UI_DEFAULT_FONT_SIZE_NORMAL para ~150px
        self.photo_label.grid(row=0, column=2, rowspan=5, padx=(10,0), pady=3, sticky="nsew")
        
        photo_buttons_frame = ttk.Frame(main_frame, style="TFrame")
        photo_buttons_frame.grid(row=5, column=2, padx=(10,0), pady=0, sticky="ew") # Debajo de la foto
        ttk.Button(photo_buttons_frame, text="Cargar...", command=self.select_photo_for_dialog, width=9).pack(side="left",pady=0)
        ttk.Button(photo_buttons_frame, text="Quitar", command=self.remove_photo_for_dialog, width=7).pack(side="left", padx=(3,0), pady=0)


        ttk.Label(main_frame, text="Fecha Nac.:").grid(row=row, column=0, sticky="w", pady=3)
        self.dob_entry = ttk.Entry(main_frame, textvariable=self.dob_var, width=15)
        self.dob_entry.grid(row=row, column=1, sticky="w", pady=3)
        self.dob_entry.insert(0, "DD/MM/AAAA") # Placeholder
        self.dob_entry.bind("<FocusIn>", lambda e: self.clear_placeholder(e.widget, "DD/MM/AAAA"))
        self.dob_entry.bind("<FocusOut>", lambda e: self.restore_placeholder(e.widget, "DD/MM/AAAA"))

        row+=1

        ttk.Label(main_frame, text="Género:").grid(row=row, column=0, sticky="w", pady=3)
        self.gender_combo = ttk.Combobox(main_frame, textvariable=self.gender_var, values=["", "Masculino", "Femenino", "Otro", "Prefiero no decirlo"], state="readonly", width=18)
        self.gender_combo.grid(row=row, column=1, sticky="w", pady=3)
        row+=1
        
        ttk.Label(main_frame, text="Teléfono:").grid(row=row, column=0, sticky="w", pady=3)
        self.phone_entry = ttk.Entry(main_frame, textvariable=self.phone_var, width=20)
        self.phone_entry.grid(row=row, column=1, sticky="w", pady=3)
        row+=1
        
        ttk.Label(main_frame, text="Dirección:").grid(row=row, column=0, sticky="w", pady=3)
        self.address1_entry = ttk.Entry(main_frame, textvariable=self.address1_var, width=40)
        self.address1_entry.grid(row=row, column=1, sticky="ew", pady=3)
        row+=1
        ttk.Label(main_frame, text="Ciudad:").grid(row=row, column=0, sticky="w", pady=3)
        self.city_entry = ttk.Entry(main_frame, textvariable=self.city_var, width=30)
        self.city_entry.grid(row=row, column=1, sticky="w", pady=3)
        row+=1
        ttk.Label(main_frame, text="Cód. Postal:").grid(row=row, column=0, sticky="w", pady=3)
        self.postal_code_entry = ttk.Entry(main_frame, textvariable=self.postal_code_var, width=10)
        self.postal_code_entry.grid(row=row, column=1, sticky="w", pady=3)
        row+=1

        ttk.Label(main_frame, text="Fecha Ingreso (*):").grid(row=row, column=0, sticky="w", pady=3)
        self.join_date_entry = ttk.Entry(main_frame, textvariable=self.join_date_var, width=15)
        self.join_date_entry.grid(row=row, column=1, sticky="w", pady=3)
        row+=1

        ttk.Label(main_frame, text="Estado (*):").grid(row=row, column=0, sticky="w", pady=3)
        self.status_combo = ttk.Combobox(main_frame, textvariable=self.status_var, values=MEMBER_STATUS_OPTIONS_LIST, state="readonly", width=18)
        self.status_combo.grid(row=row, column=1, sticky="w", pady=3)
        if MEMBER_STATUS_OPTIONS_LIST : self.status_var.set(DEFAULT_NEW_MEMBER_STATUS_ON_CREATION)
        row+=1
        
        ttk.Label(main_frame, text="Notas:").grid(row=row, column=0, sticky="nw", pady=(3,0)) 
        self.notes_text_scrollbar = ttk.Scrollbar(main_frame, orient="vertical")
        self.notes_text = tk.Text(main_frame, height=4, width=40, wrap="word", relief="solid", borderwidth=1,
                                  font=(UI_DEFAULT_FONT_FAMILY, UI_DEFAULT_FONT_SIZE_NORMAL), yscrollcommand=self.notes_text_scrollbar.set)
        self.notes_text_scrollbar.config(command=self.notes_text.yview)
        self.notes_text.grid(row=row, column=1, sticky="ew", pady=3) 
        self.notes_text_scrollbar.grid(row=row, column=2, sticky="nsw", padx=(0,5), pady=3) # Columna junto a notas
        row+=1

        buttons_frame = ttk.Frame(main_frame, style="TFrame")
        buttons_frame.grid(row=row, column=0, columnspan=3, pady=(15,0), sticky="e")
        ttk.Button(buttons_frame, text="Guardar Miembro", command=self.on_save).pack(side="right", padx=(5,0))
        ttk.Button(buttons_frame, text="Cancelar", command=self.on_cancel).pack(side="right")

    def clear_placeholder(self, widget, placeholder_text):
        if widget.get() == placeholder_text:
            widget.delete(0, tk.END)
            widget.config(foreground='black') # O el color normal del texto

    def restore_placeholder(self, widget, placeholder_text):
        if not widget.get():
            widget.insert(0, placeholder_text)
            widget.config(foreground='grey')


    def select_photo_for_dialog(self):
        # (Como antes, pero usando self.parent_frame.temp_photo_path_for_dialog)
        filepath = filedialog.askopenfilename(
            title="Seleccionar Foto",
            filetypes=(("JPG", "*.jpg;*.jpeg"), ("PNG", "*.png"), ("Todos", "*.*"))
        )
        if filepath:
            self.parent_frame.temp_photo_path_for_dialog = filepath
            self.display_photo_in_dialog(filepath)

    def remove_photo_for_dialog(self):
        self.parent_frame.temp_photo_path_for_dialog = "REMOVE_PHOTO_FLAG" # Usar un flag especial
        self.photo_label.config(image='', text="Foto Eliminada")
        self.photo_label.image = None


    def display_photo_in_dialog(self, filepath):
        # (Como antes)
        try:
            img = Image.open(filepath)
            target_width, target_height = 140, 140 # Tamaño del label de foto
            img_aspect = img.width / img.height
            
            if img.width > img.height: # Más ancha que alta
                new_width = target_width
                new_height = int(target_width / img_aspect)
            else: # Más alta que ancha o cuadrada
                new_height = target_height
                new_width = int(target_height * img_aspect)
            
            # Asegurar que no exceda las dimensiones máximas si un lado es mucho más pequeño
            if new_width > target_width: new_width = target_width
            if new_height > target_height: new_height = target_height
            
            img.thumbnail((new_width, new_height), Image.Resampling.LANCZOS)
            
            self.photo_image_tk_dialog = ImageTk.PhotoImage(img)
            self.photo_label.config(image=self.photo_image_tk_dialog, text="")
            self.photo_label.image = self.photo_image_tk_dialog 
        except Exception as e:
            messagebox.showerror("Error de Foto", f"No se pudo cargar imagen: {e}", parent=self)
            self.photo_label.config(image='', text="Error foto")
            self.parent_frame.temp_photo_path_for_dialog = None


    def load_member_data_for_dialog(self):
        # (Como antes, pero usando parent_frame para member_photo_path original)
        member_data = get_member_by_internal_id(self.member_internal_id)
        if not member_data:
            messagebox.showerror("Error", "No se cargaron datos del miembro.", parent=self); self.destroy(); return
        
        self.full_name_var.set(member_data.get('full_name', ''))
        dob_obj = member_data.get('date_of_birth_obj')
        dob_str_ui = format_date_for_ui(dob_obj) if dob_obj else ""
        self.dob_var.set(dob_str_ui)
        if not dob_str_ui : self.restore_placeholder(self.dob_entry, "DD/MM/AAAA") 
        else: self.dob_entry.config(foreground='black')

        self.gender_var.set(member_data.get('gender', ''))
        self.phone_var.set(member_data.get('phone_number', ''))
        self.address1_var.set(member_data.get('address_line1', ''))
        self.city_var.set(member_data.get('address_city', ''))
        self.postal_code_var.set(member_data.get('address_postal_code', ''))
        
        join_obj = member_data.get('join_date_obj')
        self.join_date_var.set(format_date_for_ui(join_obj) if join_obj else format_date_for_ui(date.today()))
        
        self.status_var.set(member_data.get('current_status', DEFAULT_NEW_MEMBER_STATUS_ON_CREATION))
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", member_data.get('notes', ''))
        
        self.parent_frame.member_photo_path = None # Path original
        photo_fn = member_data.get('photo_filename')
        if photo_fn:
            photo_dir = os.path.join(APP_DATA_ROOT_DIR, MEMBER_PHOTOS_SUBDIR_NAME)
            full_photo_path = os.path.join(photo_dir, photo_fn)
            if os.path.exists(full_photo_path):
                self.display_photo_in_dialog(full_photo_path)
                self.parent_frame.member_photo_path = full_photo_path 
            else:
                self.photo_label.config(image='', text="Foto no hallada")


    def on_save(self):
        # (Como antes, pero usa parent_frame.temp_photo_path_for_dialog)
        full_name = sanitize_text_input(self.full_name_var.get())
        dob_str_ui = sanitize_text_input(self.dob_var.get())
        # Si el campo DOB sigue con el placeholder, tratarlo como vacío
        if dob_str_ui == "DD/MM/AAAA": dob_str_ui = None
        
        # ... (obtener resto de variables)
        gender = self.gender_var.get()
        phone = sanitize_text_input(self.phone_var.get(), allow_empty=True)
        addr1 = sanitize_text_input(self.address1_var.get(), allow_empty=True)
        city = sanitize_text_input(self.city_var.get(), allow_empty=True)
        post_code = sanitize_text_input(self.postal_code_var.get(), allow_empty=True)
        join_date_str_ui = self.join_date_var.get()
        status = self.status_var.get()
        notes = self.notes_text.get("1.0", tk.END).strip()

        if not full_name:
            messagebox.showerror("Error Validación", "Nombre completo obligatorio.", parent=self); return
        if not parse_string_to_date(join_date_str_ui, permissive_formats=True):
             messagebox.showerror("Error Validación", "Fecha de ingreso inválida.", parent=self); return
        if dob_str_ui and not parse_string_to_date(dob_str_ui, permissive_formats=True): # Validar DOB si se ingresó algo
             messagebox.showerror("Error Validación", "Fecha de nacimiento inválida.", parent=self); return

        photo_to_save_filename = None # Nombre del archivo final si se guarda o actualiza la foto

        if self.parent_frame.temp_photo_path_for_dialog == "REMOVE_PHOTO_FLAG":
            photo_to_save_filename = None # Esto resultará en NULL en la BD
            # Si había una foto antes (self.parent_frame.member_photo_path), se podría borrar del disco aquí.
            if self.parent_frame.member_photo_path and os.path.exists(self.parent_frame.member_photo_path):
                try: os.remove(self.parent_frame.member_photo_path)
                except OSError as e_del_photo: print(f"WARN: No se pudo borrar foto anterior: {e_del_photo}")

        elif self.parent_frame.temp_photo_path_for_dialog: # Se cargó una nueva foto
            photos_dir = os.path.join(APP_DATA_ROOT_DIR, MEMBER_PHOTOS_SUBDIR_NAME)
            ensure_directory_exists(photos_dir) 
            _, ext = os.path.splitext(self.parent_frame.temp_photo_path_for_dialog)
            photo_id_prefix = self.member_internal_id if self.member_internal_id else generate_internal_id(prefix="PHOTO")
            photo_to_save_filename = f"{photo_id_prefix}_{int(datetime.now().timestamp())}{ext}" # Añadir timestamp para unicidad si se sube misma foto para mismo miembro
            destination_path = os.path.join(photos_dir, photo_to_save_filename)
            try:
                shutil.copy2(self.parent_frame.temp_photo_path_for_dialog, destination_path)
            except Exception as e_photo:
                messagebox.showerror("Error Guardar Foto", f"Fallo al guardar imagen: {e_photo}", parent=self)
                photo_to_save_filename = os.path.basename(self.parent_frame.member_photo_path) if self.parent_frame.member_photo_path else None # Mantener la antigua si la copia falla
        elif self.member_internal_id and self.parent_frame.member_photo_path: # Editando, no se cargó nueva foto, pero había una
            photo_to_save_filename = os.path.basename(self.parent_frame.member_photo_path)


        if self.member_internal_id: # Editando
            success, msg = update_member_details(
                member_internal_id=self.member_internal_id, full_name=full_name, date_of_birth_str=dob_str_ui, 
                gender=gender, phone_number=phone, address_line1=addr1, address_city=city,
                address_postal_code=post_code, current_status=status, notes=notes,
                photo_filename=photo_to_save_filename 
            )
        else: # Creando
            success, msg = add_new_member(
                full_name=full_name, date_of_birth_str=dob_str_ui, gender=gender,
                phone_number=phone, address_line1=addr1, address_city=city,
                address_postal_code=post_code, join_date_str=join_date_str_ui,
                initial_status=status, notes=notes, photo_filename=photo_to_save_filename
            )

        if success:
            self.result = {"success": True, "full_name": full_name, 
                           "id": msg if not self.member_internal_id else self.member_internal_id}
            self.destroy()
        else:
            messagebox.showerror("Error al Guardar", msg, parent=self)

    def on_cancel(self):
        self.result = None; self.destroy()


class MembershipManagementDialog(tk.Toplevel):
    def __init__(self, parent_frame, controller, member_internal_id: str):
        # (Similar al último código, solo asegurar importaciones y uso de date/Decimal)
        super().__init__(parent_frame)
        self.parent_frame = parent_frame
        self.controller = controller
        self.member_internal_id = member_internal_id
        self.result = {"data_changed": False} 

        member_data = get_member_by_internal_id(self.member_internal_id) 
        member_name = member_data.get('full_name', 'N/A') if member_data else 'N/A'

        self.title(f"Membresías de: {member_name}")
        self.transient(parent_frame); self.grab_set()
        self.geometry("750x550"); self.resizable(True, True)

        self.selected_plan_key_var = tk.StringVar()
        self.purchase_date_var = tk.StringVar(value=format_date_for_ui(date.today()))
        self.custom_price_var = tk.StringVar()

        self.create_membership_dialog_widgets()
        self.load_member_memberships_in_dialog()

        self.protocol("WM_DELETE_WINDOW", self.on_close_membership_dialog)
        self.center_dialog_membership() # Nuevo método para centrar
        self.wait_window()

    def center_dialog_membership(self):
        self.update_idletasks()
        # ... (código de centrado)
        parent_x=self.master.winfo_rootx();parent_y=self.master.winfo_rooty()
        parent_w=self.master.winfo_width();parent_h=self.master.winfo_height()
        dw=self.winfo_width();dh=self.winfo_height()
        x=parent_x+(parent_w-dw)//2;y=parent_y+(parent_h-dh)//2
        if dw>0 and dh>0: self.geometry(f"+{x}+{y}")

    def create_membership_dialog_widgets(self):
        # (Código como antes)
        # ...
        main_frame = ttk.Frame(self, padding=10, style="TFrame")
        main_frame.pack(fill="both", expand=True); main_frame.rowconfigure(0, weight=1); main_frame.columnconfigure(0, weight=1)
        
        hist_cols = ("id", "plan_name", "price", "start", "expiry", "sessions", "status_plan")
        hist_names = ("ID Memb.", "Plan", "Pagado", "Inicio", "Expira", "Sesiones", "Estado")
        self.history_tree = ttk.Treeview(main_frame, columns=hist_cols, show="headings", selectmode="browse")
        for col, name in zip(hist_cols, hist_names):
             width = 100; anchor = "w"
             if col == "plan_name": width = 180
             elif col == "id": width = 70; anchor = "center"
             self.history_tree.heading(col, text=name, anchor=anchor); self.history_tree.column(col, width=width, stretch=tk.YES, anchor=anchor)
        self.history_tree.grid(row=0, column=0, sticky="nsew", pady=(0,10))
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set); scrollbar.grid(row=0, column=1, sticky="ns", pady=(0,10))

        add_form_frame = ttk.Labelframe(main_frame, text="Añadir Nueva Membresía", style="TLabelframe", padding=10)
        add_form_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5); add_form_frame.columnconfigure(1, weight=1); add_form_frame.columnconfigure(3, weight=1)

        ttk.Label(add_form_frame, text="Plan:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.plan_display_names_map = {info['nombre_visible_ui']: key for key, info in DEFAULT_MEMBERSHIP_PLANS.items()}
        self.plan_combo = ttk.Combobox(add_form_frame, textvariable=self.selected_plan_key_var,
            values=list(self.plan_display_names_map.keys()), state="readonly", width=30)
        if list(self.plan_display_names_map.keys()): self.plan_combo.current(0)
        self.plan_combo.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(add_form_frame, text="Fecha Inicio/Compra:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.purchase_date_entry = ttk.Entry(add_form_frame, textvariable=self.purchase_date_var, width=15)
        self.purchase_date_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(add_form_frame, text="Precio Pagado (opcional):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.custom_price_entry = ttk.Entry(add_form_frame, textvariable=self.custom_price_var, width=15)
        self.custom_price_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(add_form_frame, text=CURRENCY_DISPLAY_SYMBOL).grid(row=1, column=1, sticky="w", padx=(self.custom_price_entry.winfo_reqwidth() + 10, 0))

        self.btn_add_plan = ttk.Button(add_form_frame, text="Añadir Plan", command=self.save_new_membership_for_member)
        self.btn_add_plan.grid(row=1, column=2, columnspan=2, padx=5, pady=10, sticky="e")

        ttk.Button(main_frame, text="Cerrar", command=self.on_close_membership_dialog).grid(row=2, column=0, columnspan=2, pady=10)

    def load_member_memberships_in_dialog(self):
        for item in self.history_tree.get_children(): self.history_tree.delete(item)
        memberships = get_all_memberships_for_member(self.member_internal_id)
        if not memberships: self.history_tree.insert("", "end", values=("", "Sin membresías", "", "", "", "", "")); return
        
        today_obj = date.today() # 'date' importado
        for mem in memberships:
            price_dec = mem.get('price_paid_decimal', Decimal('0')) # Ya es Decimal
            expiry_dt = mem.get('expiry_date_obj') # Ya es date
            
            status_plan = "Expirado"
            if expiry_dt and expiry_dt >= today_obj:
                status_plan = "Activo" if mem.get('is_current') else "Futuro/Vigente"
            elif expiry_dt and expiry_dt < today_obj and mem.get('is_current'):
                 status_plan = "Expirado (Pero activo)"
            
            values = (mem.get('id'), mem.get('plan_name_at_purchase'), format_currency_for_display(price_dec),
                      format_date_for_ui(mem.get('start_date_obj')), format_date_for_ui(expiry_dt),
                      f"{mem.get('sessions_remaining', 'N/A')} / {mem.get('sessions_total', 'N/A')}" if mem.get('sessions_total') is not None else "N/A",
                      status_plan )
            self.history_tree.insert("", "end", values=values)

    def save_new_membership_for_member(self):
        # (Como antes)
        # ...
        selected_plan_display_name = self.selected_plan_key_var.get()
        if not selected_plan_display_name: messagebox.showerror("Error", "Seleccione un plan.", parent=self); return
        plan_key = self.plan_display_names_map.get(selected_plan_display_name)
        if not plan_key: messagebox.showerror("Error Interno", "Clave de plan no hallada.", parent=self); return

        purchase_date_val = self.purchase_date_var.get()
        custom_price_val = self.custom_price_var.get()

        success, msg = add_membership_to_member(
            member_internal_id=self.member_internal_id, plan_key=plan_key,
            purchase_date_str=purchase_date_val,
            custom_price_paid_str=custom_price_val if custom_price_val else None
        )
        if success:
            messagebox.showinfo("Membresía Añadida", f"ID Membresía BD: {msg}", parent=self)
            self.result["data_changed"] = True; self.load_member_memberships_in_dialog()
            if list(self.plan_display_names_map.keys()): self.plan_combo.current(0)
            self.purchase_date_var.set(format_date_for_ui(date.today())) # 'date' importado
            self.custom_price_var.set("")
        else: messagebox.showerror("Error al Añadir Membresía", msg, parent=self)

    def on_close_membership_dialog(self): self.destroy()