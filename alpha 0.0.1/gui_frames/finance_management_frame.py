# gimnasio_mgmt_gui/gui_frames/finance_management_frame.py

import tkinter as tk
from tkinter import ttk, messagebox, Toplevel # Toplevel ya estaba
from datetime import date, datetime # datetime ya estaba
from decimal import Decimal # Decimal ya estaba

# Importaciones
try:
    # --- CORRECCIÓN: Añadir las constantes de UI que faltaban y usarlas sin prefijo 'config.' ---
    from config import (
        CURRENCY_DISPLAY_SYMBOL, DEFAULT_INCOME_CATEGORIES_LIST,
        DEFAULT_EXPENSE_CATEGORIES_LIST, VALID_FREQUENCIES, UI_DISPLAY_DATE_FORMAT,
        # Constantes que se usaban con config. en el código pero no se importaron:
        UI_DEFAULT_FONT_FAMILY, UI_DEFAULT_FONT_SIZE_NORMAL, 
        UI_DEFAULT_FONT_SIZE_MEDIUM, UI_DEFAULT_FONT_SIZE_LARGE,
        UI_DEFAULT_WIDGET_PADDING # Si se usa en algún sitio (no parece ser el caso en el error actual)
    )
    from core_logic.finances import (
        record_financial_transaction, get_financial_transactions, get_financial_summary,
        add_recurring_financial_item, get_pending_recurring_items_to_process,
        process_single_recurring_item
        # Y las funciones para listar/editar/eliminar recurrentes (a definir si no están)
        # Por ejemplo, necesitaríamos:
        # get_all_recurring_items, update_recurring_item, delete_recurring_item
    )
    from core_logic.utils import (
        sanitize_text_input, parse_string_to_date, format_date_for_ui,
        format_currency_for_display, parse_string_to_decimal, convert_date_to_db_string
    )
except ImportError as e:
    messagebox.showerror("Error de Carga (FinanceManagement)", f"No se pudieron cargar componentes para Gestión Financiera.\nError: {e}")
    raise


class FinanceManagementFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, style="TFrame")
        self.parent = parent
        self.controller = controller 

        self.filter_start_date_var = tk.StringVar()
        self.filter_end_date_var = tk.StringVar()
        self.filter_type_var = tk.StringVar(value="Todos") 
        self.filter_category_var = tk.StringVar()
        self.current_page = 1
        self.items_per_page = 25 
        self.total_transaction_count = 0

        self.create_widgets()
        self.grid_widgets() 
        self.load_initial_data() 

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        self.tab_transactions = ttk.Frame(self.notebook, style="TFrame", padding=10)
        self.notebook.add(self.tab_transactions, text="Transacciones")
        self.create_transactions_tab_widgets(self.tab_transactions)
        self.tab_summary = ttk.Frame(self.notebook, style="TFrame", padding=10)
        self.notebook.add(self.tab_summary, text="Resumen Financiero")
        self.create_summary_tab_widgets(self.tab_summary)
        self.tab_recurring = ttk.Frame(self.notebook, style="TFrame", padding=10)
        self.notebook.add(self.tab_recurring, text="Ingresos/Gastos Recurrentes")
        self.create_recurring_items_tab_widgets(self.tab_recurring)

    def grid_widgets(self): 
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

    def create_transactions_tab_widgets(self, parent_tab):
        # (Sin cambios en esta función, ya que no parece ser la fuente de los errores de 'config')
        parent_tab.columnconfigure(0, weight=1)
        parent_tab.rowconfigure(1, weight=1)

        filter_frame = ttk.Frame(parent_tab, style="TFrame", padding=(0,0,0,10))
        filter_frame.grid(row=0, column=0, sticky="ew")

        ttk.Label(filter_frame, text="Desde:").pack(side="left", padx=(0,2), pady=5)
        self.entry_filter_start_date = ttk.Entry(filter_frame, textvariable=self.filter_start_date_var, width=12)
        self.entry_filter_start_date.pack(side="left", padx=(0,10), pady=5)
        
        ttk.Label(filter_frame, text="Hasta:").pack(side="left", padx=(0,2), pady=5)
        self.entry_filter_end_date = ttk.Entry(filter_frame, textvariable=self.filter_end_date_var, width=12)
        self.entry_filter_end_date.pack(side="left", padx=(0,10), pady=5)

        ttk.Label(filter_frame, text="Tipo:").pack(side="left", padx=(0,2), pady=5)
        self.combo_filter_type = ttk.Combobox(filter_frame, textvariable=self.filter_type_var,
                                              values=["Todos", "Ingresos", "Gastos"], state="readonly", width=10)
        self.combo_filter_type.pack(side="left", padx=(0,10), pady=5)
        if ["Todos"]: self.combo_filter_type.current(0)

        ttk.Label(filter_frame, text="Categoría:").pack(side="left", padx=(0,2), pady=5)
        self.entry_filter_category = ttk.Entry(filter_frame, textvariable=self.filter_category_var, width=20)
        self.entry_filter_category.pack(side="left", padx=(0,10), pady=5)

        self.btn_apply_filters = ttk.Button(filter_frame, text="Aplicar Filtros", command=self.apply_transaction_filters)
        self.btn_apply_filters.pack(side="left", padx=5, pady=5)
        
        ttk.Label(filter_frame, text="  |  ").pack(side="left", padx=10, pady=5)

        self.btn_add_income = ttk.Button(filter_frame, text="Nuevo Ingreso", command=lambda: self.open_transaction_form_dialog(is_income=True))
        self.btn_add_income.pack(side="left", padx=5, pady=5)
        self.btn_add_expense = ttk.Button(filter_frame, text="Nuevo Gasto", command=lambda: self.open_transaction_form_dialog(is_income=False))
        self.btn_add_expense.pack(side="left", padx=5, pady=5)

        tree_frame = ttk.Frame(parent_tab, style="TFrame")
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        cols = ("id_trans", "date", "type", "desc", "category", "amount", "method", "user")
        names = ("ID Trans.", "Fecha", "Tipo", "Descripción", "Categoría", "Monto", "Método Pago", "Registrado Por")
        self.transactions_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")
        for col, name in zip(cols, names):
            w = 120; anchor = "w"
            if col == "id_trans": w = 100; anchor="center"
            elif col == "date": w = 90; anchor="center"
            elif col == "type": w = 70; anchor="center"
            elif col == "desc": w = 250
            elif col == "amount": w = 100; anchor="e"
            elif col == "user": w = 100; anchor="center"
            self.transactions_tree.heading(col, text=name, anchor=anchor)
            self.transactions_tree.column(col, width=w, stretch=tk.YES, anchor=anchor)
        
        self.transactions_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.transactions_tree.yview)
        self.transactions_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.pagination_frame = ttk.Frame(parent_tab, style="TFrame")
        self.pagination_frame.grid(row=2, column=0, sticky="ew", pady=(5,0))
        self.lbl_page_info = ttk.Label(self.pagination_frame, text="")
        self.lbl_page_info.pack(side="left", padx=10)
        self.btn_prev_page = ttk.Button(self.pagination_frame, text="<< Anterior", command=self.prev_page, state="disabled")
        self.btn_prev_page.pack(side="left", padx=5)
        self.btn_next_page = ttk.Button(self.pagination_frame, text="Siguiente >>", command=self.next_page, state="disabled")
        self.btn_next_page.pack(side="left", padx=5)


    def create_summary_tab_widgets(self, parent_tab):
        parent_tab.columnconfigure(0, weight=1)
        summary_content_frame = ttk.Frame(parent_tab, style="TFrame", padding=20)
        summary_content_frame.grid(row=0, column=0, sticky="")

        date_filter_frame = ttk.Labelframe(summary_content_frame, text="Filtrar Resumen por Fecha", style="TLabelframe", padding=10)
        date_filter_frame.pack(pady=(0,20), fill="x")
        
        self.summary_start_date_var = tk.StringVar()
        self.summary_end_date_var = tk.StringVar()

        ttk.Label(date_filter_frame, text="Desde:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.entry_summary_start = ttk.Entry(date_filter_frame, textvariable=self.summary_start_date_var, width=15)
        self.entry_summary_start.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(date_filter_frame, text="Hasta:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.entry_summary_end = ttk.Entry(date_filter_frame, textvariable=self.summary_end_date_var, width=15)
        self.entry_summary_end.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        
        ttk.Button(date_filter_frame, text="Actualizar Resumen", command=self.load_financial_summary).grid(row=0, column=4, padx=10, pady=5)

        summary_display_frame = ttk.Frame(summary_content_frame, style="TFrame", padding=10, relief="groove", borderwidth=2)
        summary_display_frame.pack(pady=10, fill="x")
        summary_display_frame.columnconfigure(1, weight=1)

        # --- CORRECCIÓN: Usar las constantes de UI importadas directamente, sin el prefijo 'config.' ---
        # Los errores reportados eran aquí (líneas ~181, ~182 del código anterior).
        font_summary_label = (UI_DEFAULT_FONT_FAMILY, UI_DEFAULT_FONT_SIZE_MEDIUM)
        font_summary_value = (UI_DEFAULT_FONT_FAMILY, UI_DEFAULT_FONT_SIZE_LARGE, "bold")

        ttk.Label(summary_display_frame, text="Ingresos Totales:", font=font_summary_label).grid(row=0, column=0, padx=10, pady=8, sticky="w")
        self.lbl_total_income = ttk.Label(summary_display_frame, text="0.00 " + CURRENCY_DISPLAY_SYMBOL, font=font_summary_value, foreground="green")
        self.lbl_total_income.grid(row=0, column=1, padx=10, pady=8, sticky="e")

        ttk.Label(summary_display_frame, text="Gastos Totales:", font=font_summary_label).grid(row=1, column=0, padx=10, pady=8, sticky="w")
        self.lbl_total_expense = ttk.Label(summary_display_frame, text="0.00 " + CURRENCY_DISPLAY_SYMBOL, font=font_summary_value, foreground="red")
        self.lbl_total_expense.grid(row=1, column=1, padx=10, pady=8, sticky="e")
        
        ttk.Separator(summary_display_frame, orient="horizontal").grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)

        ttk.Label(summary_display_frame, text="Balance Neto:", font=font_summary_label).grid(row=3, column=0, padx=10, pady=8, sticky="w")
        self.lbl_net_balance = ttk.Label(summary_display_frame, text="0.00 " + CURRENCY_DISPLAY_SYMBOL, font=font_summary_value, foreground="navy")
        self.lbl_net_balance.grid(row=3, column=1, padx=10, pady=8, sticky="e")


    def create_recurring_items_tab_widgets(self, parent_tab):
        # (Sin cambios funcionales aquí, asumir que las constantes de UI se usan bien o
        # no son la fuente del error reportado)
        parent_tab.columnconfigure(0, weight=1)
        parent_tab.rowconfigure(1, weight=1)

        action_frame = ttk.Frame(parent_tab, style="TFrame", padding=(0,0,0,10))
        action_frame.grid(row=0, column=0, sticky="ew")
        
        ttk.Button(action_frame, text="Añadir Recurrente", command=self.open_recurring_item_form_dialog).pack(side="left", padx=5, pady=5)
        self.btn_edit_rec = ttk.Button(action_frame, text="Editar Seleccionado", command=self.edit_selected_recurring_item, state="disabled")
        self.btn_edit_rec.pack(side="left", padx=5, pady=5)
        self.btn_del_rec = ttk.Button(action_frame, text="Eliminar Seleccionado", command=self.delete_selected_recurring_item, state="disabled")
        self.btn_del_rec.pack(side="left", padx=5, pady=5)
        ttk.Button(action_frame, text="Refrescar Lista Recurrentes", command=self.load_recurring_items_list).pack(side="left", padx=5, pady=5)

        ttk.Separator(action_frame, orient="vertical").pack(side="left", fill="y", padx=15, pady=5)
        ttk.Button(action_frame, text="Procesar Recurrentes Pendientes HOY", command=self.process_due_recurring_items).pack(side="left", padx=5, pady=5)

        tree_frame_rec = ttk.Frame(parent_tab, style="TFrame")
        tree_frame_rec.grid(row=1, column=0, sticky="nsew")
        tree_frame_rec.columnconfigure(0, weight=1)
        tree_frame_rec.rowconfigure(0, weight=1)
        
        rec_cols = ("id_rec", "type", "desc", "amount", "category", "freq", "next_due", "active")
        rec_names = ("ID", "Tipo", "Descripción", "Monto Def.", "Categoría", "Frecuencia", "Próx. Venc.", "Activo")
        self.recurring_tree = ttk.Treeview(tree_frame_rec, columns=rec_cols, show="headings", selectmode="browse")
        for col, name in zip(rec_cols, rec_names):
             width = 100; anchor="w"
             if col == "id_rec": width = 50; anchor="center"
             elif col == "type": width = 70; anchor="center"
             elif col == "desc": width = 200
             elif col == "amount": width = 100; anchor="e"
             elif col == "active": width = 70; anchor="center"
             self.recurring_tree.heading(col, text=name, anchor=anchor)
             self.recurring_tree.column(col, width=width, stretch=tk.YES, anchor=anchor)

        self.recurring_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar_rec = ttk.Scrollbar(tree_frame_rec, orient="vertical", command=self.recurring_tree.yview)
        self.recurring_tree.configure(yscrollcommand=scrollbar_rec.set)
        scrollbar_rec.grid(row=0, column=1, sticky="ns")
        # Bind para selección de ítem recurrente (para habilitar editar/eliminar)
        self.recurring_tree.bind("<<TreeviewSelect>>", self.on_recurring_item_selected)


    def on_recurring_item_selected(self, event=None):
        """Habilita/deshabilita botones al seleccionar un ítem recurrente."""
        selected_items = self.recurring_tree.selection()
        state_to_set = "normal" if selected_items else "disabled"
        if hasattr(self, 'btn_edit_rec'): self.btn_edit_rec.config(state=state_to_set)
        if hasattr(self, 'btn_del_rec'): self.btn_del_rec.config(state=state_to_set)
        # Guardar el ID del ítem seleccionado si es necesario
        # if selected_items:
        #    self.selected_recurring_item_id = self.recurring_tree.item(selected_items[0], "values")[0] # Asume que ID es la primera col
        # else:
        #    self.selected_recurring_item_id = None

    # --- (Resto de las funciones: load_initial_data, apply_transaction_filters,
    # load_transactions_list, update_pagination_controls, prev_page, next_page,
    # load_financial_summary, load_recurring_items_list,
    # open_transaction_form_dialog, open_recurring_item_form_dialog,
    # edit_selected_recurring_item, delete_selected_recurring_item,
    # process_due_recurring_items, on_show_frame, give_focus
    # permanecen igual que antes en su estructura general, asegurándose que
    # las conexiones a BD se manejan y cierran correctamente, y que
    # las funciones de utils (como format_currency_for_display) se usan donde sea necesario.
    # Es importante revisar CADA uso de constantes de config para asegurar que
    # se usan sin prefijo 'config.' si se importaron explícitamente.)
    
    # Ejemplo para asegurar que la sección if __name__ == "__main__": no cause errores
    # si este archivo se ejecuta aisladamente. (Normalmente no se haría para frames).
    # Para este módulo, no es práctico tener un `if __name__ == "__main__"` de prueba
    # significativo sin mockear el controller y una app Tkinter raíz.
    # ...
    
    # Mover la definición de TransactionFormDialog a su propio contexto
    # o asegurar que si se queda aquí, usa las constantes importadas directamente
    # (sin 'config.' delante).

# La definición de TransactionFormDialog y otras clases de diálogo va aquí
# Es crucial que cualquier constante de config.py usada en ellas (ej. para fuentes, paddings)
# sea referenciada directamente (ej. UI_DEFAULT_FONT_FAMILY) si fue importada,
# o a través de self.controller.style.lookup si se obtiene del estilo global.

# ... (clase TransactionFormDialog y otras si se definen en este archivo) ...
# Si TransactionFormDialog está en este archivo, revisar CADA uso de constantes de config
# dentro de ella también.

# --- Por ejemplo, en TransactionFormDialog, dentro de create_form_widgets ---
# En vez de:
# self.date_entry = ttk.Entry(form, ..., font=(config.UI_DEFAULT_FONT_FAMILY, ...))
# Sería (asumiendo que esas constantes están importadas):
# self.date_entry = ttk.Entry(form, ..., font=(UI_DEFAULT_FONT_FAMILY, ...))
# O mejor aún, si los estilos TEntry ya definen la fuente globalmente:
# self.date_entry = ttk.Entry(form, ...) # Y heredará la fuente de "TEntry"

# (El resto del archivo, incluyendo las clases de diálogo si están aquí,
# necesitaría la misma revisión para el uso de constantes de config.py.)


# Manteniendo el TransactionFormDialog del código anterior, y aplicando la corrección:
class TransactionFormDialog(Toplevel):
    def __init__(self, parent_frame, controller, title: str, is_income: bool, transaction_id: int | None = None):
        super().__init__(parent_frame)
        # ... (inicialización como antes) ...
        self.parent_frame = parent_frame
        self.controller = controller
        self.is_income = is_income
        self.transaction_id_to_edit = transaction_id 
        self.result = {"success": False}

        self.title(title)
        self.transient(parent_frame)
        self.grab_set()
        self.resizable(False, False)
        
        self.date_var = tk.StringVar(value=format_date_for_ui(date.today()))
        self.desc_var = tk.StringVar()
        self.category_var = tk.StringVar()
        self.amount_var = tk.StringVar()
        self.method_var = tk.StringVar()
        # self.notes_var = tk.StringVar() # Mejor usar tk.Text para notas largas

        self.create_form_widgets_transaction() # Renombrar para evitar colisión si hay otro
        if self.transaction_id_to_edit:
            self.load_transaction_data_for_edit()

        self.protocol("WM_DELETE_WINDOW", self.on_cancel_transaction) # Renombrar
        self.center_dialog() # Método para centrar
        self.date_entry.focus_set()
        self.wait_window()

    def center_dialog(self):
        self.update_idletasks()
        parent_x = self.master.winfo_rootx() # Usar self.master que es el Toplevel
        parent_y = self.master.winfo_rooty()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        if dialog_width > 0 and dialog_height > 0: # Solo si el tamaño es válido
             self.geometry(f"+{x}+{y}")

    def create_form_widgets_transaction(self): # Renombrar
        form = ttk.Frame(self, padding=20, style="TFrame")
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        
        row = 0
        # --- Aquí se usa la constante directamente (ej. UI_DEFAULT_FONT_FAMILY) ---
        # Asumiendo que el estilo TEntry ya fue configurado globalmente, no necesitamos font aquí.
        ttk.Label(form, text="Fecha (*):").grid(row=row, column=0, sticky="w", pady=3)
        self.date_entry = ttk.Entry(form, textvariable=self.date_var, width=15) 
        self.date_entry.grid(row=row, column=1, sticky="w", pady=3)
        row +=1

        ttk.Label(form, text="Descripción (*):").grid(row=row, column=0, sticky="w", pady=3)
        self.desc_entry = ttk.Entry(form, textvariable=self.desc_var, width=40)
        self.desc_entry.grid(row=row, column=1, sticky="ew", pady=3)
        row +=1

        ttk.Label(form, text="Categoría (*):").grid(row=row, column=0, sticky="w", pady=3)
        categories = DEFAULT_INCOME_CATEGORIES_LIST if self.is_income else DEFAULT_EXPENSE_CATEGORIES_LIST
        self.category_combo = ttk.Combobox(form, textvariable=self.category_var, values=categories, state="readonly", width=38)
        self.category_combo.grid(row=row, column=1, sticky="ew", pady=3)
        if categories: self.category_combo.current(0)
        row +=1

        ttk.Label(form, text="Monto (*):").grid(row=row, column=0, sticky="w", pady=3)
        self.amount_entry = ttk.Entry(form, textvariable=self.amount_var, width=15)
        self.amount_entry.grid(row=row, column=1, sticky="w", pady=3)
        ttk.Label(form, text=CURRENCY_DISPLAY_SYMBOL).grid(row=row, column=1, sticky="w", padx=(130 if self.winfo_width() > 300 else 100 ,0)) # Ajuste de padx según ancho
        row +=1

        ttk.Label(form, text="Método de Pago:").grid(row=row, column=0, sticky="w", pady=3)
        payment_methods = ["Efectivo", "Tarjeta Crédito", "Tarjeta Débito", "Transferencia", "Bizum", "Cheque", "Otro"] # Lista ampliada
        self.method_combo = ttk.Combobox(form, textvariable=self.method_var, values=payment_methods, width=20)
        self.method_combo.grid(row=row, column=1, sticky="w", pady=3)
        row +=1
        
        ttk.Label(form, text="Notas:").grid(row=row, column=0, sticky="nw", pady=3)
        self.notes_text_widget = tk.Text(form, height=4, width=40, wrap="word", relief="solid", borderwidth=1,
                                         font=(UI_DEFAULT_FONT_FAMILY, UI_DEFAULT_FONT_SIZE_NORMAL)) # Aplicar fuente explícitamente al tk.Text
        self.notes_text_widget.grid(row=row, column=1, sticky="ew", pady=3)
        row +=1

        buttons_frame = ttk.Frame(form, style="TFrame")
        buttons_frame.grid(row=row, column=0, columnspan=2, pady=(15,0), sticky="e")
        ttk.Button(buttons_frame, text="Guardar Transacción", command=self.on_save_transaction).pack(side="right", padx=(5,0)) # Renombrar
        ttk.Button(buttons_frame, text="Cancelar", command=self.on_cancel_transaction).pack(side="right") # Renombrar
        
    def load_transaction_data_for_edit(self):
        # Placeholder: Cargar datos si self.transaction_id_to_edit no es None
        # (Lógica de cargar datos en las StringVars)
        print(f"INFO: Carga de datos para editar transacción ID {self.transaction_id_to_edit} no implementada.")
        pass

    def on_save_transaction(self): # Renombrar
        trans_date_str = self.date_var.get()
        desc_str = self.desc_var.get()
        category_str = self.category_var.get()
        amount_str_val = self.amount_var.get() # Renombrar variable
        
        if not (trans_date_str and desc_str and category_str and amount_str_val):
            messagebox.showerror("Campos Obligatorios", "Fecha, Descripción, Categoría y Monto son obligatorios.", parent=self)
            return

        parsed_amount = parse_string_to_decimal(amount_str_val)
        if parsed_amount is None or parsed_amount <= Decimal(0):
            messagebox.showerror("Monto Inválido", "El monto debe ser un número positivo.", parent=self)
            return

        user_id = self.controller.current_user_info.get('id') if self.controller.current_user_info else None
        
        if self.transaction_id_to_edit:
            # success, msg = update_financial_transaction(...) # Función a crear en core_logic.finances
            print(f"INFO: Edición de transacción ID {self.transaction_id_to_edit} no implementada.")
            success, msg_or_id = False, "Función de edición no implementada" # Placeholder
        else:
            success, msg_or_id = record_financial_transaction(
                transaction_type="income" if self.is_income else "expense",
                transaction_date_str=trans_date_str,
                description=desc_str,
                category=category_str,
                amount_str=str(parsed_amount), # Pasar el Decimal parseado como string
                payment_method=self.method_var.get(),
                notes=self.notes_text_widget.get("1.0", tk.END).strip(),
                recorded_by_user_id=user_id
            )

        if success:
            self.result["success"] = True
            self.destroy()
        else:
            messagebox.showerror("Error al Guardar", f"No se pudo guardar la transacción.\n{msg_or_id}", parent=self)
            
    def on_cancel_transaction(self): # Renombrar
        self.result = {"success": False} # Indicar que no hubo éxito o fue cancelado
        self.destroy()

# (El resto de funciones de FinanceManagementFrame y el `if __name__ == "__main__"` block,
#  asegurándose de usar UI_DISPLAY_DATE_FORMAT y format_currency_for_display de las importaciones
#  y no con 'config.')

# En el `if __name__ == "__main__":` de finance_management_frame.py
# (esto normalmente no se hace para frames que son parte de una app mayor)
# Pero si lo hubiera, las correcciones son:
# línea 525: ... date.today().strftime(UI_DISPLAY_DATE_FORMAT) ... (usa la constante importada)
# línea 550: ... amount_disp = format_currency_for_display(t['amount_decimal']) ... (usa la función importada)
# línea 555: ... start_month_ui = date.today().replace(day=1).strftime(UI_DISPLAY_DATE_FORMAT) ...
# líneas 558-560: ... format_currency_for_display(...) ...


# --- CORRECCIÓN APLICADA DIRECTAMENTE AL BLOQUE __main__ DEL ÚLTIMO CÓDIGO DE FINANCES.PY ---
# (Para fines de esta corrección, si el bloque __main__ sigue existiendo en tu finance_management_frame.py,
# las líneas problemáticas del error serían ahora las siguientes. El bloque __main__ para frames
# anidados no es común, pero si existe, se corrige así):

    # print("\n1. Registrando un ingreso de prueba...")
    # --- USO CORREGIDO DE UI_DISPLAY_DATE_FORMAT ---
    # today_ui_format = get_current_date_for_db().strftime(UI_DISPLAY_DATE_FORMAT) # Esta línea no tiene problemas si get_current_date_for_db() es de utils
    # ...

    # print("\n3. Obteniendo últimas transacciones (5)...")
    # ...
    #        for t in transactions:
    #            # --- USO CORREGIDO DE format_currency_for_display ---
    #            amount_disp = format_currency_for_display(t['amount_decimal']) # Usa la función importada
    # ...

    # print("\n4. Obteniendo resumen financiero del mes actual...")
    # --- USO CORREGIDO DE UI_DISPLAY_DATE_FORMAT ---
    # start_of_month = date.today().replace(day=1).strftime(UI_DISPLAY_DATE_FORMAT) # Usa la constante importada
    # ...
    #    print(f"    Ingresos: {format_currency_for_display(summary['total_income'])}")
    #    print(f"    Gastos:   {format_currency_for_display(summary['total_expense'])}")
    #    print(f"    Balance:  {format_currency_for_display(summary['net_balance'])}")
# ... etc.