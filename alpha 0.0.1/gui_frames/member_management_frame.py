# gimnasio_mgmt_gui/gui_frames/member_management_frame.py
# Frame para la gestión completa de miembros (socios) del gimnasio.

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk # Requiere: pip install Pillow
import os
import shutil
from datetime import date, datetime # <-- CORRECCIÓN: Importar 'date' y 'datetime'
from decimal import Decimal # <-- CORRECCIÓN: Importar 'Decimal'
import config
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
    def __init__(self, parent_frame, controller, title: str, member_internal_id: str | None = None):
        super().__init__(parent_frame)
        self.parent_frame = parent_frame # Esta es la instancia de MemberManagementFrame
        self.controller = controller
        self.member_internal_id = member_internal_id
        self.result = None
        # self.temp_photo_path ya no es atributo de MemberFormDialog, sino del parent_frame
        
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
        # Línea 235 (del error) donde se usa 'date.today()'
        self.join_date_var = tk.StringVar(value=format_date_for_ui(date.today())) # Uso de 'date'
        self.status_var = tk.StringVar(value=DEFAULT_NEW_MEMBER_STATUS_ON_CREATION) # Usar la constante de config
        # self.notes_text_var no es necesario si accedemos directamente al widget tk.Text

        self.create_member_form_dialog_widgets() # Renombrar para claridad
        if self.member_internal_id:
            self.load_member_data_for_dialog() # Renombrar

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        # (Código de centrado...)
        self.center_dialog()
        self.full_name_entry.focus_set()
        self.wait_window()

    def center_dialog(self): # Añadir método para centrar
        self.update_idletasks()
        parent_x = self.master.winfo_rootx()
        parent_y = self.master.winfo_rooty()
        # ... (resto del código de centrado como en TransactionFormDialog)
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        if dialog_width > 0 and dialog_height > 0:
             self.geometry(f"+{x}+{y}")


    def create_member_form_dialog_widgets(self): # Renombrar
        # (Código de create_form_widgets sin cambios funcionales aquí,
        # pero renombrado el método y los métodos que llama)
        main_frame = ttk.Frame(self, padding=20, style="TFrame")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(1, weight=1) 
        main_frame.columnconfigure(2, weight=0, minsize=160)

        row = 0
        ttk.Label(main_frame, text="Nombre Completo (*):").grid(row=row, column=0, sticky="w", pady=3)
        self.full_name_entry = ttk.Entry(main_frame, textvariable=self.full_name_var, width=40)
        self.full_name_entry.grid(row=row, column=1, sticky="ew", pady=3)
        row+=1

        self.photo_label = ttk.Label(main_frame, text="Foto (150x150px)", anchor="center", borderwidth=1, relief="solid", width=20, height=10)
        self.photo_label.grid(row=0, column=2, rowspan=5, padx=(10,0), pady=3, sticky="nsew") 
        ttk.Button(main_frame, text="Cargar Foto...", command=self.select_photo_for_dialog).grid(row=5, column=2, padx=(10,0), pady=3, sticky="ew") # Renombrar

        ttk.Label(main_frame, text="Fecha Nac. (DD/MM/AAAA):").grid(row=row, column=0, sticky="w", pady=3)
        self.dob_entry = ttk.Entry(main_frame, textvariable=self.dob_var, width=15)
        self.dob_entry.grid(row=row, column=1, sticky="w", pady=3)
        row+=1

        ttk.Label(main_frame, text="Género:").grid(row=row, column=0, sticky="w", pady=3)
        self.gender_combo = ttk.Combobox(main_frame, textvariable=self.gender_var, values=["Masculino", "Femenino", "Otro", "Prefiero no decirlo"], state="readonly", width=18)
        self.gender_combo.grid(row=row, column=1, sticky="w", pady=3)
        row+=1
        
        ttk.Label(main_frame, text="Teléfono:").grid(row=row, column=0, sticky="w", pady=3)
        self.phone_entry = ttk.Entry(main_frame, textvariable=self.phone_var, width=20)
        self.phone_entry.grid(row=row, column=1, sticky="w", pady=3)
        row+=1
        
        # ... (campos de dirección)
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
        
        ttk.Label(main_frame, text="Notas Adicionales:").grid(row=row, column=0, sticky="nw", pady=3)
        self.notes_text = tk.Text(main_frame, height=4, width=40, wrap="word", relief="solid", borderwidth=1,
                                  font=(UI_DEFAULT_FONT_FAMILY, UI_DEFAULT_FONT_SIZE_NORMAL)) # Aplicar fuente al tk.Text
        self.notes_text.grid(row=row, column=1, columnspan=2, sticky="ew", pady=3, padx=(0,0)) 
        row+=1

        buttons_frame = ttk.Frame(main_frame, style="TFrame")
        buttons_frame.grid(row=row, column=0, columnspan=3, pady=(15,0), sticky="e")
        ttk.Button(buttons_frame, text="Guardar Miembro", command=self.on_save).pack(side="right", padx=(5,0))
        ttk.Button(buttons_frame, text="Cancelar", command=self.on_cancel).pack(side="right")


    def select_photo_for_dialog(self): # Renombrar
        filepath = filedialog.askopenfilename(
            title="Seleccionar Foto del Miembro",
            filetypes=(("Imágenes JPG", "*.jpg;*.jpeg"), ("Imágenes PNG", "*.png"), ("Todos los archivos", "*.*"))
        )
        if filepath:
            # Guardar el path temporal en el PARENT frame (MemberManagementFrame)
            # para que sepa que esta es la foto a procesar al guardar.
            self.parent_frame.temp_photo_path_for_dialog = filepath
            self.display_photo_in_dialog(filepath) # Renombrar


    def display_photo_in_dialog(self, filepath): # Renombrar
        try:
            img = Image.open(filepath)
            img.thumbnail((150, 150))
            self.photo_image_tk_dialog = ImageTk.PhotoImage(img) # Diferente variable para evitar conflictos
            self.photo_label.config(image=self.photo_image_tk_dialog, text="")
            self.photo_label.image = self.photo_image_tk_dialog 
        except Exception as e:
            messagebox.showerror("Error de Foto", f"No se pudo cargar la imagen.\n{e}", parent=self)
            self.photo_label.config(image='', text="Error foto")
            self.parent_frame.temp_photo_path_for_dialog = None


    def load_member_data_for_dialog(self): # Renombrar
        # (Similar a load_member_data, pero asegura que las variables y widgets son de este diálogo)
        member_data = get_member_by_internal_id(self.member_internal_id)
        if not member_data:
            messagebox.showerror("Error", "No se pudieron cargar los datos.", parent=self)
            self.destroy()
            return
        
        self.full_name_var.set(member_data.get('full_name', ''))
        dob_obj = member_data.get('date_of_birth_obj') # Ya es objeto date si get_member_by_internal_id lo devuelve
        self.dob_var.set(format_date_for_ui(dob_obj) if dob_obj else "")
        
        self.gender_var.set(member_data.get('gender', ''))
        self.phone_var.set(member_data.get('phone_number', ''))
        self.address1_var.set(member_data.get('address_line1', ''))
        self.city_var.set(member_data.get('address_city', ''))
        self.postal_code_var.set(member_data.get('address_postal_code', ''))
        
        join_date_obj = member_data.get('join_date_obj')
        self.join_date_var.set(format_date_for_ui(join_date_obj) if join_date_obj else "")
        
        self.status_var.set(member_data.get('current_status', DEFAULT_NEW_MEMBER_STATUS_ON_CREATION))
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", member_data.get('notes', ''))
        
        photo_fn = member_data.get('photo_filename')
        self.parent_frame.member_photo_path = None # Path original de la foto
        if photo_fn:
            photo_dir = os.path.join(APP_DATA_ROOT_DIR, MEMBER_PHOTOS_SUBDIR_NAME)
            full_photo_path = os.path.join(photo_dir, photo_fn)
            if os.path.exists(full_photo_path):
                self.display_photo_in_dialog(full_photo_path)
                self.parent_frame.member_photo_path = full_photo_path # Guardar el path de la foto existente


    def on_save(self):
        # (Lógica de on_save como antes, pero usa self.parent_frame.temp_photo_path_for_dialog)
        full_name = self.full_name_var.get()
        dob_str = self.dob_var.get()
        gender = self.gender_var.get()
        phone = self.phone_var.get()
        addr1 = self.address1_var.get()
        city = self.city_var.get()
        post_code = self.postal_code_var.get()
        join_date_str = self.join_date_var.get()
        status = self.status_var.get()
        notes = self.notes_text.get("1.0", tk.END).strip()
        
        photo_to_save_filename = None # Nombre del archivo final si se guarda una foto

        if not sanitize_text_input(full_name):
            messagebox.showerror("Error de Validación", "El nombre completo es obligatorio.", parent=self)
            return
        if not parse_string_to_date(join_date_str, permissive_formats=True): # Validar fecha de ingreso
             messagebox.showerror("Error de Validación", "Fecha de ingreso no válida.", parent=self)
             return

        # Guardar/Copiar foto si se seleccionó una nueva
        if self.parent_frame.temp_photo_path_for_dialog:
            photos_dir = os.path.join(APP_DATA_ROOT_DIR, MEMBER_PHOTOS_SUBDIR_NAME)
            ensure_directory_exists(photos_dir)
            _, ext = os.path.splitext(self.parent_frame.temp_photo_path_for_dialog)
            # Usar ID de miembro (si existe) o un UUID para nombre de foto más consistente si se edita la foto luego
            photo_id_prefix = self.member_internal_id if self.member_internal_id else generate_internal_id(prefix="PHOTO")
            photo_to_save_filename = f"{photo_id_prefix}{ext}" # Podría sobrescribir foto anterior si se edita. Manejar esto.
            destination_path = os.path.join(photos_dir, photo_to_save_filename)
            try:
                shutil.copy2(self.parent_frame.temp_photo_path_for_dialog, destination_path)
            except Exception as e_photo:
                messagebox.showerror("Error al Guardar Foto", f"No se pudo guardar la imagen: {e_photo}", parent=self)
                photo_to_save_filename = None 
                # Decidir si continuar sin foto o no. Aquí continuamos.
        elif self.member_internal_id and self.parent_frame.member_photo_path:
            # Si estamos editando y NO se cargó una nueva foto, pero SÍ había una foto antes, mantenerla.
            photo_to_save_filename = os.path.basename(self.parent_frame.member_photo_path)


        if self.member_internal_id: # Editando
            success, msg = update_member_details(
                member_internal_id=self.member_internal_id,
                full_name=full_name, date_of_birth_str=dob_str, gender=gender,
                phone_number=phone, address_line1=addr1, address_city=city,
                address_postal_code=post_code, current_status=status, notes=notes,
                photo_filename=photo_to_save_filename 
            )
        else: # Creando
            success, msg = add_new_member(
                full_name=full_name, date_of_birth_str=dob_str, gender=gender,
                phone_number=phone, address_line1=addr1, address_city=city,
                address_postal_code=post_code, join_date_str=join_date_str,
                initial_status=status, notes=notes, photo_filename=photo_to_save_filename
            )

        if success:
            self.result = {"success": True, "full_name": full_name, 
                           "id": msg if not self.member_internal_id else self.member_internal_id}
            self.destroy()
        else:
            messagebox.showerror("Error al Guardar Miembro", msg, parent=self)

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