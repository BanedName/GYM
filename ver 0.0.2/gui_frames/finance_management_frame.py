# gimnasio_mgmt_gui/gui_frames/finance_management_frame.py
# Frame para la gestión financiera: transacciones, resumen e ítems recurrentes.

import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from datetime import date, datetime # Asegurar que datetime esté importado
from decimal import Decimal

# Importaciones
try:
    from config import (
        CURRENCY_DISPLAY_SYMBOL, DEFAULT_INCOME_CATEGORIES_LIST,
        DEFAULT_EXPENSE_CATEGORIES_LIST, VALID_FREQUENCIES, UI_DISPLAY_DATE_FORMAT,
        UI_DEFAULT_FONT_FAMILY, UI_DEFAULT_FONT_SIZE_NORMAL, UI_DEFAULT_FONT_SIZE_LARGE, UI_DEFAULT_FONT_SIZE_MEDIUM # Si TransactionFormDialog los usa directamente
    )
    from core_logic.finances import (
        record_financial_transaction, get_financial_transactions, get_financial_summary,
        add_recurring_financial_item, get_pending_recurring_items_to_process,
        process_single_recurring_item, # get_all_recurring_items (necesitarás esta)
        # update_recurring_item, delete_recurring_item (necesitarás estas)
    )
    from core_logic.utils import (
        sanitize_text_input, parse_string_to_date, format_date_for_ui,
        format_currency_for_display, parse_string_to_decimal, convert_date_to_db_string
    )
except ImportError as e:
    messagebox.showerror("Error de Carga (FinanceManagement)", f"Componentes no cargados.\nError: {e}")
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
        self.selected_recurring_item_id = None # Para el treeview de recurrentes

        # Los métodos se definirán ANTES de create_widgets si se usan en commands
        self.create_widgets() 
        # self.grid_widgets() ahora se maneja dentro de __init__ o al final de create_widgets
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5) # Empaquetar notebook
        self.load_initial_data() # Llamada después de que todos los widgets estén creados


    # --- Definición de Métodos ANTES de que se usen en 'command' dentro de create_widgets ---

    def apply_transaction_filters(self):
        self.current_page = 1
        self.load_transactions_list()

    def load_transactions_list(self):
        # (Código de load_transactions_list como lo tenías)
        for item in self.transactions_tree.get_children(): self.transactions_tree.delete(item)
        start_str = sanitize_text_input(self.filter_start_date_var.get())
        end_str = sanitize_text_input(self.filter_end_date_var.get())
        type_val = self.filter_type_var.get(); type_param = "income" if type_val=="Ingresos" else "expense" if type_val=="Gastos" else None
        cat_val = sanitize_text_input(self.filter_category_var.get())
        offset = (self.current_page - 1) * self.items_per_page
        trans, total = get_financial_transactions(start_str, end_str, type_param, cat_val, self.items_per_page, offset)
        self.total_transaction_count = total
        for t in trans:
            amt_disp = format_currency_for_display(t.get('amount_decimal'))
            date_disp = t.get('transaction_date_ui', format_date_for_ui(parse_string_to_date(t.get('transaction_date'))))
            values = (t.get('internal_transaction_id', 'N/A'), date_disp,
                      t.get('transaction_type', '').capitalize(), t.get('description', ''),
                      t.get('category', ''), amt_disp, t.get('payment_method', ''), 
                      t.get('recorded_by_username', 'Sistema'))
            self.transactions_tree.insert("", "end", values=values, iid=t.get('id'))
        self.update_pagination_controls()

    def open_transaction_form_dialog(self, is_income: bool, transaction_id_to_edit: int | None = None):
        # (Código de open_transaction_form_dialog como lo tenías)
        title = "Registrar Ingreso" if is_income else "Registrar Gasto"
        if transaction_id_to_edit: title = f"Editar Transacción #{transaction_id_to_edit}"
        
        dialog = TransactionFormDialog(self, self.controller, title=title, is_income=is_income, transaction_id=transaction_id_to_edit)
        if dialog.result and dialog.result.get("success"):
            self.load_transactions_list()
            self.load_financial_summary()
            action = "actualizada" if transaction_id_to_edit else "registrada"
            messagebox.showinfo(f"Transacción {action.capitalize()}", f"Transacción {action} exitosamente.", parent=self)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.load_transactions_list()

    def next_page(self):
        total_pages = (self.total_transaction_count + self.items_per_page - 1) // self.items_per_page
        if self.current_page < total_pages:
            self.current_page += 1
            self.load_transactions_list()

    def load_financial_summary(self):
        # (Código de load_financial_summary como lo tenías)
        start_str = sanitize_text_input(self.summary_start_date_var.get())
        end_str = sanitize_text_input(self.summary_end_date_var.get())
        summary = get_financial_summary(start_date_str=start_str, end_date_str=end_str)
        self.lbl_total_income.config(text=format_currency_for_display(summary.get('total_income')))
        self.lbl_total_expense.config(text=format_currency_for_display(summary.get('total_expense')))
        net_bal = summary.get('net_balance', Decimal(0))
        self.lbl_net_balance.config(text=format_currency_for_display(net_bal),
                                    foreground="green" if net_bal >= 0 else "red")


    def open_recurring_item_form_dialog(self, item_id_to_edit: int | None = None):
        # (Código de open_recurring_item_form_dialog como lo tenías,
        #  abriría un RecurringItemFormDialog (que necesitaríamos crear))
        # Por ahora, un placeholder:
        title = "Añadir Ítem Recurrente" if not item_id_to_edit else f"Editar Ítem Recurrente #{item_id_to_edit}"
        dialog = RecurringItemFormDialog(self, self.controller, title=title, item_id=item_id_to_edit)
        if dialog.result and dialog.result.get("success"):
            self.load_recurring_items_list()
            action = "actualizado" if item_id_to_edit else "añadido"
            messagebox.showinfo(f"Ítem Recurrente {action.capitalize()}", f"Ítem {action} exitosamente.", parent=self)


    def edit_selected_recurring_item(self):
        # (Código de edit_selected_recurring_item como lo tenías,
        #  obtiene ID seleccionado del recurring_tree y llama a open_recurring_item_form_dialog)
        selected_items = self.recurring_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selección Requerida", "Seleccione un ítem recurrente para editar.", parent=self)
            return
        item_id = self.recurring_tree.item(selected_items[0], "values")[0] # Asume que el ID es la primera columna
        self.open_recurring_item_form_dialog(item_id_to_edit=int(item_id))


    def delete_selected_recurring_item(self):
        # (Código de delete_selected_recurring_item como lo tenías)
        selected_items = self.recurring_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selección Requerida", "Seleccione un ítem recurrente para eliminar.", parent=self)
            return
        
        item_values = self.recurring_tree.item(selected_items[0], "values")
        item_id_to_delete = item_values[0]
        item_desc = item_values[2] # Asumir que descripción es la tercera columna
        
        if messagebox.askyesno("Confirmar Eliminación",
                             f"¿Está seguro de eliminar el ítem recurrente:\n'{item_desc}' (ID: {item_id_to_delete})?",
                             icon='warning', parent=self):
            # from core_logic.finances import delete_recurring_item # Necesitarás esta función
            # success, msg = delete_recurring_item(int(item_id_to_delete))
            # if success:
            #     messagebox.showinfo("Eliminado", msg, parent=self)
            #     self.load_recurring_items_list()
            # else:
            #     messagebox.showerror("Error al Eliminar", msg, parent=self)
            print(f"INFO: Lógica para eliminar ítem recurrente ID {item_id_to_delete} no implementada aún.")
            messagebox.showinfo("Próximamente", "Eliminación de ítems recurrentes no implementada.", parent=self)

    def load_recurring_items_list(self):
        # (Código de load_recurring_items_list como lo tenías)
        for item in self.recurring_tree.get_children(): self.recurring_tree.delete(item)
        
        from core_logic.finances import get_all_recurring_items # Necesitarás esta función
        recurring_items_data = get_all_recurring_items() if 'get_all_recurring_items' in globals() else [] # Check si existe

        for item_data in recurring_items_data:
            values = (
                item_data.get('id'), item_data.get('item_type', '').capitalize(), 
                item_data.get('description'), format_currency_for_display(Decimal(str(item_data.get('default_amount','0')))),
                item_data.get('category'), item_data.get('frequency'),
                format_date_for_ui(parse_string_to_date(item_data.get('next_due_date'))),
                "Sí" if item_data.get('is_active') else "No"
            )
            self.recurring_tree.insert("", "end", values=values, iid=item_data.get('id'))
        self.on_recurring_item_selected() # Para deshabilitar botones si no hay selección


    def process_due_recurring_items(self):
        # (Código de process_due_recurring_items como lo tenías)
        pending_items = get_pending_recurring_items_to_process()
        if not pending_items:
            messagebox.showinfo("Proceso Completado", "No hay ítems recurrentes pendientes.", parent=self); return
        if not messagebox.askyesno("Confirmar Proceso", f"{len(pending_items)} ítem(s) para procesar. Continuar?", parent=self): return
        
        proc_count, err_count = 0, 0
        user_id = self.controller.current_user_info.get('id') if self.controller.current_user_info else None
        for item in pending_items:
            item_id = item['id']
            success, msg = process_single_recurring_item(item_id, recorded_by_user_id=user_id)
            if success: proc_count += 1; print(f"INFO (FinanceFrame): {msg}")
            else: err_count += 1; print(f"ERROR (FinanceFrame): {msg}"); messagebox.showwarning("Error Procesando",f"Ítem ID {item_id}.\n{msg}", parent=self)
        
        msg_sum = f"Proceso completado.\nProcesados: {proc_count}\nErrores: {err_count}"
        messagebox.showinfo("Resultado", msg_sum, parent=self)
        self.load_transactions_list(); self.load_recurring_items_list(); self.load_financial_summary()


    def create_widgets(self): # Definición movida ANTES de __init__ para Pylance (no, __init__ es el constructor)
                            # La clave es que los MÉTODOS sean definidos antes de ser referenciados
                            # en 'command='. La llamada a load_initial_data() debe estar al final de __init__.
        self.notebook = ttk.Notebook(self)
        self.tab_transactions = ttk.Frame(self.notebook, style="TFrame", padding=10)
        self.notebook.add(self.tab_transactions, text="Transacciones")
        self.create_transactions_tab_widgets(self.tab_transactions) # Usa los métodos definidos arriba

        self.tab_summary = ttk.Frame(self.notebook, style="TFrame", padding=10)
        self.notebook.add(self.tab_summary, text="Resumen Financiero")
        self.create_summary_tab_widgets(self.tab_summary) # Usa los métodos definidos arriba
        
        self.tab_recurring = ttk.Frame(self.notebook, style="TFrame", padding=10)
        self.notebook.add(self.tab_recurring, text="Ingresos/Gastos Recurrentes")
        self.create_recurring_items_tab_widgets(self.tab_recurring) # Usa los métodos definidos arriba


    def grid_widgets(self): 
        # Esta función puede eliminarse si el notebook se empaqueta en __init__
        # self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        pass # Ya se hace el pack en __init__


    def create_transactions_tab_widgets(self, parent_tab):
        # (Código como antes, pero los 'command' ahora refieren a métodos ya definidos)
        parent_tab.columnconfigure(0, weight=1); parent_tab.rowconfigure(1, weight=1)
        filter_frame = ttk.Frame(parent_tab, style="TFrame", padding=(0,0,0,10)); filter_frame.grid(row=0, column=0, sticky="ew")
        ttk.Label(filter_frame, text="Desde:").pack(side="left",padx=(0,2),pady=5);self.entry_filter_start_date=ttk.Entry(filter_frame,textvariable=self.filter_start_date_var,width=12);self.entry_filter_start_date.pack(side="left",padx=(0,10),pady=5)
        ttk.Label(filter_frame, text="Hasta:").pack(side="left",padx=(0,2),pady=5);self.entry_filter_end_date=ttk.Entry(filter_frame,textvariable=self.filter_end_date_var,width=12);self.entry_filter_end_date.pack(side="left",padx=(0,10),pady=5)
        ttk.Label(filter_frame, text="Tipo:").pack(side="left",padx=(0,2),pady=5);self.combo_filter_type=ttk.Combobox(filter_frame,textvariable=self.filter_type_var,values=["Todos","Ingresos","Gastos"],state="readonly",width=10);self.combo_filter_type.pack(side="left",padx=(0,10),pady=5);self.combo_filter_type.current(0)
        ttk.Label(filter_frame, text="Categoría:").pack(side="left",padx=(0,2),pady=5);self.entry_filter_category=ttk.Entry(filter_frame,textvariable=self.filter_category_var,width=20);self.entry_filter_category.pack(side="left",padx=(0,10),pady=5)
        self.btn_apply_filters = ttk.Button(filter_frame, text="Aplicar Filtros", command=self.apply_transaction_filters); self.btn_apply_filters.pack(side="left", padx=5, pady=5) # OK
        ttk.Label(filter_frame, text="|").pack(side="left",padx=10,pady=5)
        self.btn_add_income = ttk.Button(filter_frame, text="Nuevo Ingreso", command=lambda: self.open_transaction_form_dialog(is_income=True)); self.btn_add_income.pack(side="left", padx=5, pady=5) # OK
        self.btn_add_expense = ttk.Button(filter_frame, text="Nuevo Gasto", command=lambda: self.open_transaction_form_dialog(is_income=False)); self.btn_add_expense.pack(side="left", padx=5, pady=5) # OK
        
        tree_frame=ttk.Frame(parent_tab,style="TFrame");tree_frame.grid(row=1,column=0,sticky="nsew");tree_frame.columnconfigure(0,weight=1);tree_frame.rowconfigure(0,weight=1)
        cols=("id_trans","date","type","desc","category","amount","method","user");names=("ID Trans.","Fecha","Tipo","Descripción","Categoría","Monto","Método Pago","Registrado Por")
        self.transactions_tree=ttk.Treeview(tree_frame,columns=cols,show="headings",selectmode="browse");
        for c,n in zip(cols,names): w=120;a="w"; (w:=100,a:="center") if c=="id_trans" else (w:=90,a:="center") if c=="date" else (w:=70,a:="center") if c=="type" else (w:=250) if c=="desc" else (w:=100,a:="e") if c=="amount" else (w:=100,a:="center") if c=="user" else w;self.transactions_tree.heading(c,text=n,anchor=a);self.transactions_tree.column(c,width=w,stretch=tk.YES,anchor=a)
        self.transactions_tree.grid(row=0,column=0,sticky="nsew");s=ttk.Scrollbar(tree_frame,orient="vertical",command=self.transactions_tree.yview);self.transactions_tree.configure(yscrollcommand=s.set);s.grid(row=0,column=1,sticky="ns")
        
        self.pagination_frame=ttk.Frame(parent_tab,style="TFrame");self.pagination_frame.grid(row=2,column=0,sticky="ew",pady=(5,0))
        self.lbl_page_info=ttk.Label(self.pagination_frame,text="");self.lbl_page_info.pack(side="left",padx=10)
        self.btn_prev_page = ttk.Button(self.pagination_frame, text="<< Anterior", command=self.prev_page, state="disabled"); self.btn_prev_page.pack(side="left", padx=5) # OK
        self.btn_next_page = ttk.Button(self.pagination_frame, text="Siguiente >>", command=self.next_page, state="disabled"); self.btn_next_page.pack(side="left", padx=5) # OK

    def create_summary_tab_widgets(self, parent_tab):
        # (Código como antes, pero command=self.load_financial_summary ya definido)
        parent_tab.columnconfigure(0,weight=1); summary_content_frame=ttk.Frame(parent_tab,style="TFrame",padding=20);summary_content_frame.grid(row=0,column=0,sticky="")
        date_filter_frame=ttk.Labelframe(summary_content_frame,text="Filtrar Resumen por Fecha",style="TLabelframe",padding=10);date_filter_frame.pack(pady=(0,20),fill="x")
        self.summary_start_date_var=tk.StringVar();self.summary_end_date_var=tk.StringVar()
        ttk.Label(date_filter_frame,text="Desde:").grid(row=0,column=0,padx=5,pady=5,sticky="w");self.entry_summary_start=ttk.Entry(date_filter_frame,textvariable=self.summary_start_date_var,width=15);self.entry_summary_start.grid(row=0,column=1,padx=5,pady=5,sticky="w")
        ttk.Label(date_filter_frame,text="Hasta:").grid(row=0,column=2,padx=5,pady=5,sticky="w");self.entry_summary_end=ttk.Entry(date_filter_frame,textvariable=self.summary_end_date_var,width=15);self.entry_summary_end.grid(row=0,column=3,padx=5,pady=5,sticky="w")
        ttk.Button(date_filter_frame,text="Actualizar Resumen",command=self.load_financial_summary).grid(row=0,column=4,padx=10,pady=5) # OK

        summary_display_frame=ttk.Frame(summary_content_frame,style="TFrame",padding=10,relief="groove",borderwidth=2);summary_display_frame.pack(pady=10,fill="x");summary_display_frame.columnconfigure(1,weight=1)
        font_label=(UI_DEFAULT_FONT_FAMILY,UI_DEFAULT_FONT_SIZE_MEDIUM);font_value=(UI_DEFAULT_FONT_FAMILY,UI_DEFAULT_FONT_SIZE_LARGE,"bold")
        ttk.Label(summary_display_frame,text="Ingresos Totales:",font=font_label).grid(row=0,column=0,padx=10,pady=8,sticky="w");self.lbl_total_income=ttk.Label(summary_display_frame,text="0.00 "+CURRENCY_DISPLAY_SYMBOL,font=font_value,foreground="green");self.lbl_total_income.grid(row=0,column=1,padx=10,pady=8,sticky="e")
        ttk.Label(summary_display_frame,text="Gastos Totales:",font=font_label).grid(row=1,column=0,padx=10,pady=8,sticky="w");self.lbl_total_expense=ttk.Label(summary_display_frame,text="0.00 "+CURRENCY_DISPLAY_SYMBOL,font=font_value,foreground="red");self.lbl_total_expense.grid(row=1,column=1,padx=10,pady=8,sticky="e")
        ttk.Separator(summary_display_frame,orient="horizontal").grid(row=2,column=0,columnspan=2,sticky="ew",pady=10)
        ttk.Label(summary_display_frame,text="Balance Neto:",font=font_label).grid(row=3,column=0,padx=10,pady=8,sticky="w");self.lbl_net_balance=ttk.Label(summary_display_frame,text="0.00 "+CURRENCY_DISPLAY_SYMBOL,font=font_value,foreground="navy");self.lbl_net_balance.grid(row=3,column=1,padx=10,pady=8,sticky="e")

    def create_recurring_items_tab_widgets(self, parent_tab):
        # (Código como antes, pero los 'command' ahora refieren a métodos ya definidos)
        parent_tab.columnconfigure(0,weight=1);parent_tab.rowconfigure(1,weight=1)
        action_frame=ttk.Frame(parent_tab,style="TFrame",padding=(0,0,0,10));action_frame.grid(row=0,column=0,sticky="ew")
        ttk.Button(action_frame,text="Añadir Recurrente",command=self.open_recurring_item_form_dialog).pack(side="left",padx=5,pady=5) # OK
        self.btn_edit_rec=ttk.Button(action_frame,text="Editar Seleccionado",command=self.edit_selected_recurring_item,state="disabled");self.btn_edit_rec.pack(side="left",padx=5,pady=5) # OK
        self.btn_del_rec=ttk.Button(action_frame,text="Eliminar Seleccionado",command=self.delete_selected_recurring_item,state="disabled");self.btn_del_rec.pack(side="left",padx=5,pady=5) # OK
        ttk.Button(action_frame,text="Refrescar Recurrentes",command=self.load_recurring_items_list).pack(side="left",padx=5,pady=5) # OK
        ttk.Separator(action_frame,orient="vertical").pack(side="left",fill="y",padx=15,pady=5)
        ttk.Button(action_frame,text="Procesar Pendientes HOY",command=self.process_due_recurring_items).pack(side="left",padx=5,pady=5) # OK

        tree_frame_rec=ttk.Frame(parent_tab,style="TFrame");tree_frame_rec.grid(row=1,column=0,sticky="nsew");tree_frame_rec.columnconfigure(0,weight=1);tree_frame_rec.rowconfigure(0,weight=1)
        rec_cols=("id_rec","type","desc","amount","category","freq","next_due","active");rec_names=("ID","Tipo","Descripción","Monto Def.","Categoría","Frecuencia","Próx. Venc.","Activo")
        self.recurring_tree=ttk.Treeview(tree_frame_rec,columns=rec_cols,show="headings",selectmode="browse");
        for c,n in zip(rec_cols,rec_names):w=100;a="w";(w:=50,a:="center")if c=="id_rec"else(w:=70,a:="center")if c=="type"else(w:=200)if c=="desc"else(w:=100,a:="e")if c=="amount"else(w:=70,a:="center")if c=="active"else w;self.recurring_tree.heading(c,text=n,anchor=a);self.recurring_tree.column(c,width=w,stretch=tk.YES,anchor=a)
        self.recurring_tree.grid(row=0,column=0,sticky="nsew");s_rec=ttk.Scrollbar(tree_frame_rec,orient="vertical",command=self.recurring_tree.yview);self.recurring_tree.configure(yscrollcommand=s_rec.set);s_rec.grid(row=0,column=1,sticky="ns")
        self.recurring_tree.bind("<<TreeviewSelect>>", self.on_recurring_item_selected)


    # --- El método load_initial_data() debe estar definido ANTES de que __init__ lo llame ---
    def load_initial_data(self):
        self.current_page = 1
        today = date.today()
        first_day_month = today.replace(day=1)
        self.filter_start_date_var.set(format_date_for_ui(first_day_month))
        self.filter_end_date_var.set(format_date_for_ui(today))
        
        self.load_transactions_list()
        self.load_financial_summary()
        self.load_recurring_items_list()

    def update_pagination_controls(self):
        # (Código como antes)
        total_pages = (self.total_transaction_count + self.items_per_page -1) // self.items_per_page
        if total_pages == 0: total_pages = 1
        self.lbl_page_info.config(text=f"Pág {self.current_page}/{total_pages} ({self.total_transaction_count} trans.)")
        self.btn_prev_page.config(state="normal" if self.current_page > 1 else "disabled")
        self.btn_next_page.config(state="normal" if self.current_page < total_pages else "disabled")

    def on_recurring_item_selected(self, event=None):
        selected_items = self.recurring_tree.selection()
        state_to_set = "normal" if selected_items else "disabled"
        if hasattr(self, 'btn_edit_rec'): self.btn_edit_rec.config(state=state_to_set)
        if hasattr(self, 'btn_del_rec'): self.btn_del_rec.config(state=state_to_set)
        if selected_items:
            item_values = self.recurring_tree.item(selected_items[0], "values")
            self.selected_recurring_item_id = item_values[0] if item_values else None
        else:
            self.selected_recurring_item_id = None
            
    def on_show_frame(self, data_to_pass: dict | None = None):
        self.load_initial_data()
        self.give_focus()

    def give_focus(self):
        self.entry_filter_start_date.focus_set()


# --- CLASE DE DIÁLOGO PARA TRANSACCIÓN ---
# (Clase TransactionFormDialog como la tenías, asegurar que usa constantes de config importadas directamente)
class TransactionFormDialog(Toplevel):
    def __init__(self, parent_frame, controller, title: str, is_income: bool, transaction_id: int | None = None):
        super().__init__(parent_frame)
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
        # self.notes_var ya no se usa, se usa self.notes_text_widget

        self.create_form_widgets_transaction()
        if self.transaction_id_to_edit:
            self.load_transaction_data_for_edit()

        self.protocol("WM_DELETE_WINDOW", self.on_cancel_transaction)
        self.center_dialog_transaction() # Método para centrar
        self.date_entry.focus_set()
        self.wait_window()

    def center_dialog_transaction(self): # Método para centrar
        self.update_idletasks()
        # (Código de centrado, ej. como en UserFormDialog)
        parent_x=self.master.winfo_rootx();parent_y=self.master.winfo_rooty();parent_w=self.master.winfo_width();parent_h=self.master.winfo_height();dw=self.winfo_width();dh=self.winfo_height();x=parent_x+(parent_w-dw)//2;y=parent_y+(parent_h-dh)//2;
        if dw>0 and dh>0: self.geometry(f"+{x}+{y}")

    def create_form_widgets_transaction(self):
        form = ttk.Frame(self, padding=20, style="TFrame")
        form.pack(fill="both", expand=True); form.columnconfigure(1, weight=1)
        row=0
        ttk.Label(form,text="Fecha (*):").grid(row=row,column=0,sticky="w",pady=3);self.date_entry=ttk.Entry(form,textvariable=self.date_var,width=15);self.date_entry.grid(row=row,column=1,sticky="w",pady=3);row+=1
        ttk.Label(form,text="Descripción (*):").grid(row=row,column=0,sticky="w",pady=3);self.desc_entry=ttk.Entry(form,textvariable=self.desc_var,width=40);self.desc_entry.grid(row=row,column=1,sticky="ew",pady=3);row+=1
        ttk.Label(form,text="Categoría (*):").grid(row=row,column=0,sticky="w",pady=3);cats=DEFAULT_INCOME_CATEGORIES_LIST if self.is_income else DEFAULT_EXPENSE_CATEGORIES_LIST;self.category_combo=ttk.Combobox(form,textvariable=self.category_var,values=cats,state="readonly",width=38);self.category_combo.grid(row=row,column=1,sticky="ew",pady=3); (self.category_combo.current(0) if cats else None); row+=1
        ttk.Label(form,text="Monto (*):").grid(row=row,column=0,sticky="w",pady=3);self.amount_entry=ttk.Entry(form,textvariable=self.amount_var,width=15);self.amount_entry.grid(row=row,column=1,sticky="w",pady=3);ttk.Label(form,text=CURRENCY_DISPLAY_SYMBOL).grid(row=row,column=1,sticky="w",padx=(self.amount_entry.winfo_reqwidth()+5,0));row+=1
        ttk.Label(form,text="Método Pago:").grid(row=row,column=0,sticky="w",pady=3);pay_methods=["Efectivo","Tarjeta Crédito","Tarjeta Débito","Transferencia","Bizum","Cheque","Otro"];self.method_combo=ttk.Combobox(form,textvariable=self.method_var,values=pay_methods,width=20);self.method_combo.grid(row=row,column=1,sticky="w",pady=3);row+=1
        ttk.Label(form,text="Notas:").grid(row=row,column=0,sticky="nw",pady=3);self.notes_text_widget=tk.Text(form,height=4,width=40,wrap="word",relief="solid",borderwidth=1,font=(UI_DEFAULT_FONT_FAMILY,UI_DEFAULT_FONT_SIZE_NORMAL));self.notes_text_widget.grid(row=row,column=1,sticky="ew",pady=3);row+=1
        btns_frame=ttk.Frame(form,style="TFrame");btns_frame.grid(row=row,column=0,columnspan=2,pady=(15,0),sticky="e");ttk.Button(btns_frame,text="Guardar",command=self.on_save_transaction).pack(side="right",padx=(5,0));ttk.Button(btns_frame,text="Cancelar",command=self.on_cancel_transaction).pack(side="right")

    def load_transaction_data_for_edit(self): print(f"INFO: Carga para editar transacción ID {self.transaction_id_to_edit} pendiente."); pass # Placeholder

    def on_save_transaction(self):
        date_s=self.date_var.get();desc_s=self.desc_var.get();cat_s=self.category_var.get();amount_s=self.amount_var.get()
        if not (date_s and desc_s and cat_s and amount_s): messagebox.showerror("Obligatorio","Fecha, Descripción, Categoría y Monto son obligatorios.",parent=self); return
        parsed_amt=parse_string_to_decimal(amount_s)
        if parsed_amt is None or parsed_amt <= Decimal(0): messagebox.showerror("Monto Inválido","Monto debe ser número positivo.",parent=self); return
        user_id=self.controller.current_user_info.get('id') if self.controller.current_user_info else None
        if self.transaction_id_to_edit: success,msg_id = False,"Edición no implementada" # Placeholder
        else: success,msg_id=record_financial_transaction("income" if self.is_income else "expense",date_s,desc_s,cat_s,str(parsed_amt),self.method_var.get(),notes=self.notes_text_widget.get("1.0",tk.END).strip(),recorded_by_user_id=user_id)
        if success: self.result["success"]=True; self.destroy()
        else: messagebox.showerror("Error al Guardar",f"No se pudo guardar.\n{msg_id}",parent=self)
            
    def on_cancel_transaction(self): self.result={"success":False}; self.destroy()

# --- CLASE DE DIÁLOGO PARA ÍTEMS RECURRENTES (Placeholder Básico) ---
class RecurringItemFormDialog(Toplevel):
    def __init__(self, parent_frame, controller, title: str, item_id: int | None = None):
        super().__init__(parent_frame)
        self.parent_frame = parent_frame; self.controller = controller
        self.item_id_to_edit = item_id; self.result = {"success": False}
        self.title(title); self.transient(parent_frame); self.grab_set(); self.resizable(False,False)
        # ... StringVars y widgets para tipo, desc, monto, categoría, freq, fecha_inicio, etc. ...
        ttk.Label(self, text="Formulario de Ítem Recurrente\n(En desarrollo)").pack(padx=50, pady=50)
        ttk.Button(self, text="Cerrar (Test)", command=self.destroy).pack(pady=10)
        self.wait_window()


# No añadir if __name__ == "__main__" a los archivos de gui_frames.
# Se prueban a través de main_gui.py.