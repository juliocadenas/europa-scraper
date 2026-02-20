#!/usr/bin/env python3
"""
Database Configuration Tab
--------------------------
Pestaña de configuración para gestión de bases de datos SQLite Cloud
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
from typing import Optional, Callable
from utils.sqlite_cloud_connector import SQLiteCloudConnector

class DatabaseConfigTab(ttk.Frame):
    """
    Pestaña de configuración de base de datos para gestionar SQLite Cloud.
    Permite conectar, gestionar tablas e importar datos.
    """

    def __init__(self, parent_frame: tk.Frame):
        """
        Inicializar la pestaña de configuración de base de datos.

        Args:
            parent_frame: Frame padre en el que se creará la pestaña
            config_manager: Gestor de configuración (opcional)
        """
        # Inicializar el Frame padre
        super().__init__(parent_frame)

        self.parent = parent_frame
        # Crear siempre instancia específica para configuración SQLite Cloud
        # Independientemente del config_manager pasado como parámetro
        from utils.sqlite_cloud_connector import DatabaseConfig as SQLiteConfig
        self.config_manager = SQLiteConfig()
        self.connector: Optional[SQLiteCloudConnector] = None
        self.is_connected = False

        # Crear la interfaz
        self.create_ui()

        # Cargar configuración inicial
        self.load_config()

    def create_ui(self):
        """Crear la interfaz de usuario de la pestaña."""
        # Configurar el frame principal (self)
        self.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Título de la pestaña
        title_label = ttk.Label(self, text="🔧 Configuración de Base de Datos (SQLite Cloud)",
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 20))

        # Frame para conexión
        conn_frame = ttk.LabelFrame(self, text="Configuración de Conexión", padding=10)
        conn_frame.pack(fill=tk.X, pady=(0, 10))

        # URL de conexión
        ttk.Label(conn_frame, text="URL de SQLite Cloud:").grid(row=0, column=0, sticky="w", pady=2)
        self.url_var = tk.StringVar(value="https://cn6wjw2rhk.g3.sqlite.cloud:443")
        self.url_entry = ttk.Entry(conn_frame, textvariable=self.url_var, width=60)
        self.url_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=2, padx=(10, 0))

        # API Key de SQLite Cloud
        ttk.Label(conn_frame, text="API Key:").grid(row=1, column=0, sticky="w", pady=2)
        self.api_key_var = tk.StringVar(value="3H****ttqE")  # Default API key for docuplay
        self.api_key_entry = ttk.Entry(conn_frame, textvariable=self.api_key_var, show="*", width=40)
        self.api_key_entry.grid(row=1, column=1, columnspan=3, sticky="ew", pady=2, padx=(10, 0))

        # Botón para mostrar/ocultar API Key
        self.show_api_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(conn_frame, text="Mostrar", variable=self.show_api_key_var,
                       command=self.toggle_api_key_visibility).grid(row=2, column=1, sticky="w", pady=2)

        # Botones de conexión
        buttons_frame = ttk.Frame(conn_frame)
        buttons_frame.grid(row=2, column=0, columnspan=4, pady=(10, 0))

        self.connect_button = ttk.Button(buttons_frame, text="🔌 Conectar",
                                       command=self.connect_to_database)
        self.connect_button.pack(side=tk.LEFT, padx=(0, 10))

        self.disconnect_button = ttk.Button(buttons_frame, text="🔌 Desconectar",
                                          command=self.disconnect_from_database, state=tk.DISABLED)
        self.disconnect_button.pack(side=tk.LEFT, padx=(0, 10))

        self.test_connection_button = ttk.Button(buttons_frame, text="🧪 Probar Conexión",
                                               command=self.test_connection)
        self.test_connection_button.pack(side=tk.LEFT)

        # Status de conexión
        self.status_label = ttk.Label(buttons_frame, text="❌ Sin conexión",
                                    foreground="red")
        self.status_label.pack(side=tk.RIGHT)

        # Frame para gestión de tablas
        tables_frame = ttk.LabelFrame(self, text="Gestión de Tablas", padding=10)
        tables_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Lista de tablas
        list_frame = ttk.Frame(tables_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(list_frame, text="Tablas disponibles:").pack(anchor="w")

        # Treeview para mostrar tablas
        columns = ("Nombre", "Registros", "Columnas")
        self.tables_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)

        for col in columns:
            self.tables_tree.heading(col, text=col)
            self.tables_tree.column(col, width=150)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tables_tree.yview)
        self.tables_tree.configure(yscrollcommand=scrollbar.set)

        self.tables_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Botones para gestión de tablas
        buttons_frame2 = ttk.Frame(tables_frame)
        buttons_frame2.pack(fill=tk.X, pady=(10, 0))

        self.refresh_button = ttk.Button(buttons_frame2, text="🔄 Actualizar",
                                       command=self.refresh_tables, state=tk.DISABLED)
        self.refresh_button.pack(side=tk.LEFT, padx=(0, 5))

        self.create_table_button = ttk.Button(buttons_frame2, text="➕ Crear Tabla",
                                            command=self.show_create_table_dialog, state=tk.DISABLED)
        self.create_table_button.pack(side=tk.LEFT, padx=(0, 5))

        self.import_csv_button = ttk.Button(buttons_frame2, text="📤 Importar CSV",
                                          command=self.show_import_csv_dialog, state=tk.DISABLED)
        self.import_csv_button.pack(side=tk.LEFT, padx=(0, 5))

        self.select_table_button = ttk.Button(buttons_frame2, text="✅ Seleccionar para Scraping",
                                            command=self.select_table_for_scraping, state=tk.DISABLED)
        self.select_table_button.pack(side=tk.LEFT, padx=(0, 5))

        # Configuración de configuración por defecto
        config_frame = ttk.LabelFrame(self, text="Configuración por Defecto", padding=10)
        config_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(config_frame, text="Tabla por defecto:").grid(row=0, column=0, sticky="w", pady=2)
        self.default_table_var = tk.StringVar()
        self.default_table_combo = ttk.Combobox(config_frame, textvariable=self.default_table_var,
                                              state="readonly", width=30)
        self.default_table_combo.grid(row=0, column=1, sticky="ew", pady=2, padx=(10, 0))
        self.save_defaults_button = ttk.Button(config_frame, text="💾 Guardar Configuración",
                                             command=self.save_default_config)
        self.save_defaults_button.grid(row=0, column=2, padx=(10, 0))

        # Información de ayuda
        help_frame = ttk.LabelFrame(self, text="Ayuda", padding=10)
        help_frame.pack(fill=tk.X)

        help_text = """🔧 Cómo usar:
1. Configura la URL de SQLite Cloud y API Key
2. Marca/desmarca "Mostrar" para ver/ocultar la API Key
3. Haz clic en "Probar Conexión" para verificar credenciales
4. Haz clic en "Conectar" para establecer la conexión permanente
5. Revisa las tablas disponibles en la lista
6. Selecciona una tabla para usar en scraping

📝 Recomendaciones:
• La tabla debe tener las columnas: course, name
• Usa "Crear Tabla" para generar tablas vacías idénticas
• Los archivos CSV pueden tener cualquier formato (columnas 1=curso, 2=nombre)
• La API Key se guarda automáticamente en el archivo de configuración"""

        help_label = ttk.Label(help_frame, text=help_text, justify=tk.LEFT, wraplength=600)
        help_label.pack(anchor="w")

        # Configurar redimensionamiento
        conn_frame.columnconfigure(1, weight=1)
        list_frame.columnconfigure(0, weight=1)
        config_frame.columnconfigure(1, weight=1)

    def toggle_api_key_visibility(self):
        """Alternar visibilidad de la API Key."""
        if self.show_api_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")

    def load_config(self):
        """Cargar configuración desde el archivo de configuración."""
        try:
            cloud_config = self.config_manager.get_cloud_config()

            if cloud_config.get('enabled', False):
                self.url_var.set(cloud_config.get('url', ''))
                self.api_key_var.set(cloud_config.get('password', ''))
                self.default_table_var.set(cloud_config.get('default_table', ''))
            else:
                # Establecer valores por defecto si no hay configuración
                self.url_var.set('https://cn6wjw2rhk.g3.sqlite.cloud:443')
                self.api_key_var.set('3H****ttqE')  # API key

        except Exception as e:
            messagebox.showerror("Error", f"Error cargando configuración: {str(e)}")
            # En caso de error, usar valores por defecto
            self.url_var.set('https://cn6wjw2rhk.g3.sqlite.cloud:443')
            self.api_key_var.set('3H****ttqE')

    def connect_to_database(self):
        """Conectar a la base de datos SQLite Cloud."""
        def connect_thread():
            try:
                # Actualizar status
                self.status_label.config(text="⏳ Conectando...", foreground="orange")
                self.connect_button.config(state=tk.DISABLED)
                self.parent.update()

                url = self.url_var.get().strip()
                api_key = self.api_key_var.get().strip()
                username = "docuplay"  # Fixed username for API key format
                password = api_key if api_key not in ["********", ""] else None

                if not url:
                    raise ValueError("La URL de SQLite Cloud es requerida")

                # Crear conector
                self.connector = SQLiteCloudConnector(url)

                # Si no hay API key válida, intentar recuperar de configuración
                if not password:
                    cloud_config = self.config_manager.get_cloud_config()
                    password = cloud_config.get('password', None)

                # Intentar conectar
                if self.connector.connect(username or None, password or None):
                    self.is_connected = True

                    # Configurar botones
                    self.connect_button.config(state=tk.DISABLED)
                    self.disconnect_button.config(state=tk.NORMAL)
                    self.refresh_button.config(state=tk.NORMAL)
                    self.create_table_button.config(state=tk.NORMAL)
                    self.import_csv_button.config(state=tk.NORMAL)
                    self.select_table_button.config(state=tk.NORMAL)

                    # Actualizar status
                    self.status_label.config(text="✅ Conectado", foreground="green")

                    # Cargar tablas
                    self.refresh_tables()

                    # Guardar configuración
                    self.config_manager.set_cloud_config(url, username, api_key)

                else:
                    raise ConnectionError("No se pudo establecer la conexión")

            except Exception as e:
                self.status_label.config(text=f"❌ Error: {str(e)}", foreground="red")
                messagebox.showerror("Error de Conexión", f"No se pudo conectar:\n{str(e)}")

                # Resetear estado
                self.connect_button.config(state=tk.NORMAL)
                self.disconnect_button.config(state=tk.DISABLED)

        # Ejecutar en hilo separado para no bloquear la UI
        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()

    def disconnect_from_database(self):
        """Desconectar de la base de datos."""
        try:
            if self.connector:
                self.connector.disconnect()
                self.connector = None

            self.is_connected = False

            # Configurar botones
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
            self.refresh_button.config(state=tk.DISABLED)
            self.create_table_button.config(state=tk.DISABLED)
            self.import_csv_button.config(state=tk.DISABLED)
            self.select_table_button.config(state=tk.DISABLED)

            # Limpiar lista de tablas
            for item in self.tables_tree.get_children():
                self.tables_tree.delete(item)

            # Actualizar status
            self.status_label.config(text="❌ Sin conexión", foreground="red")

            messagebox.showinfo("Desconectado", "Se ha desconectado de la base de datos.")

        except Exception as e:
            messagebox.showerror("Error", f"Error al desconectar: {str(e)}")

    def test_connection(self):
        """Probar la conexión a la base de datos."""
        def test_thread():
            try:
                self.status_label.config(text="🧪 Probando conexión...", foreground="blue")
                self.test_connection_button.config(state=tk.DISABLED)
                self.parent.update()

                url = self.url_var.get().strip()
                api_key = self.api_key_var.get().strip()
                username = "docuplay"  # Fixed username for API key format
                password = api_key if api_key not in ["********", ""] else None

                if not url:
                    raise ValueError("La URL de SQLite Cloud es requerida")

                # Crear conector temporal
                temp_connector = SQLiteCloudConnector(url)

                # Si no hay API key válida, intentar recuperar de configuración
                if not password:
                    cloud_config = self.config_manager.get_cloud_config()
                    password = cloud_config.get('password', None)

                # Intentar conectar
                if temp_connector.connect(username or None, password or None):
                    tables = temp_connector.get_tables()
                    temp_connector.disconnect()

                    self.status_label.config(text=f"✅ Conexión OK ({len(tables)} tablas)",
                                           foreground="green")
                    messagebox.showinfo("Prueba Exitosa",
                                      f"Conexión exitosa a SQLite Cloud!\n"
                                      f"Tablas encontradas: {len(tables)}")

                else:
                    self.status_label.config(text="❌ Error de conexión", foreground="red")
                    messagebox.showerror("Error de Conexión",
                                       "No se pudo conectar a SQLite Cloud")

            except Exception as e:
                self.status_label.config(text="❌ Error de conexión", foreground="red")
                messagebox.showerror("Error", f"Error probando conexión:\n{str(e)}")

            finally:
                self.test_connection_button.config(state=tk.NORMAL)

        # Ejecutar en hilo separado
        thread = threading.Thread(target=test_thread, daemon=True)
        thread.start()

    def refresh_tables(self):
        """Actualizar la lista de tablas."""
        if not self.is_connected or not self.connector:
            return

        try:
            # Limpiar lista anterior
            for item in self.tables_tree.get_children():
                self.tables_tree.delete(item)

            # Obtener tablas
            tables = self.connector.get_tables()

            for table_name in tables:
                # Obtener información de la tabla
                count = self.connector.get_table_count(table_name)

                # Obtener estructura (última columna)
                structure = self.connector.get_table_structure(table_name)
                columns_count = len(structure)

                # Agregar a la lista
                self.tables_tree.insert("", tk.END, values=(table_name, count, columns_count))

            # Actualizar combo de tabla por defecto
            table_names = [t[0] for t in self.tables_tree.get_children()]
            self.default_table_combo['values'] = table_names

            messagebox.showinfo("Tablas Actualizadas",
                              f"Se encontraron {len(tables)} tablas en la base de datos.")

        except Exception as e:
            messagebox.showerror("Error", f"Error actualizando tablas:\n{str(e)}")

    def show_create_table_dialog(self):
        """Mostrar diálogo para crear una nueva tabla."""
        if not self.is_connected or not self.connector:
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title("Crear Nueva Tabla")
        dialog.geometry("400x250")
        dialog.resizable(False, False)

        # Centrar el diálogo
        dialog.transient(self.parent)
        dialog.grab_set()

        ttk.Label(dialog, text="Nueva tabla vacía basada en tabla existente:",
                 font=("Arial", 11, "bold")).pack(pady=10)

        # Seleccionar tabla fuente
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        ttk.Label(frame, text="Tabla fuente:").pack(anchor="w")
        source_table_var = tk.StringVar()
        source_combo = ttk.Combobox(frame, textvariable=source_table_var,
                                  values=[t[0] for t in self.tables_tree.get_children()],
                                  state="readonly")
        source_combo.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(frame, text="Nombre de nueva tabla:").pack(anchor="w")
        new_table_name_var = tk.StringVar()
        new_table_name_entry = ttk.Entry(frame, textvariable=new_table_name_var)
        new_table_name_entry.pack(fill=tk.X)

        # Botones
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=20, pady=(10, 20))

        def create_table():
            try:
                source_table = source_table_var.get()
                new_table = new_table_name_var.get().strip()

                if not source_table:
                    messagebox.showerror("Error", "Debe seleccionar una tabla fuente.")
                    return

                if not new_table:
                    messagebox.showerror("Error", "Debe especificar un nombre para la nueva tabla.")
                    return

                if self.connector.create_table_like(source_table, new_table):
                    messagebox.showinfo("Éxito", f"Tabla '{new_table}' creada exitosamente.")
                    dialog.destroy()
                    self.refresh_tables()
                else:
                    messagebox.showerror("Error", "No se pudo crear la tabla.")

            except Exception as e:
                messagebox.showerror("Error", f"Error creando tabla:\n{str(e)}")

        ttk.Button(buttons_frame, text="➕ Crear", command=create_table).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="❌ Cancelar", command=dialog.destroy).pack(side=tk.RIGHT)

    def show_import_csv_dialog(self):
        """Mostrar diálogo para importar CSV."""
        if not self.is_connected or not self.connector:
            return

        dialog = tk.Toplevel(self.parent)
        dialog.title("Importar CSV")
        dialog.geometry("500x400")
        dialog.resizable(False, False)

        # Centrar el diálogo
        dialog.transient(self.parent)
        dialog.grab_set()

        ttk.Label(dialog, text="Importar datos desde archivo CSV",
                 font=("Arial", 11, "bold")).pack(pady=10)

        # Seleccionar archivo CSV
        file_frame = ttk.Frame(dialog)
        file_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        ttk.Label(file_frame, text="Archivo CSV:").pack(anchor="w")
        csv_file_var = tk.StringVar()
        csv_file_entry = ttk.Entry(file_frame, textvariable=csv_file_var)
        csv_file_entry.pack(fill=tk.X, side=tk.LEFT, expand=True)
        ttk.Button(file_frame, text="📁 Examinar",
                  command=lambda: csv_file_var.set(filedialog.askopenfilename(
                      filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]))).pack(side=tk.RIGHT, padx=(5, 0))

        # Seleccionar tabla destino
        table_frame = ttk.Frame(dialog)
        table_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        ttk.Label(table_frame, text="Tabla destino:").pack(anchor="w")
        target_table_var = tk.StringVar()
        target_combo = ttk.Combobox(table_frame, textvariable=target_table_var,
                                  values=[t[0] for t in self.tables_tree.get_children()],
                                  state="readonly")
        target_combo.pack(fill=tk.X)

        # Configuración de columnas
        columns_frame = ttk.Frame(dialog)
        columns_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        ttk.Label(columns_frame, text="Mapeo de columnas:",
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))

        # Columnas del CSV
        ttk.Label(columns_frame, text="Columna 'course' en CSV:").grid(row=0, column=0, sticky="w", pady=2)
        course_column_var = tk.StringVar(value="course")
        course_column_entry = ttk.Entry(columns_frame, textvariable=course_column_var)
        course_column_entry.grid(row=0, column=1, sticky="ew", pady=2, padx=(10, 0))

        ttk.Label(columns_frame, text="Columna 'name' en CSV:").grid(row=1, column=0, sticky="w", pady=2)
        name_column_var = tk.StringVar(value="name")
        name_column_entry = ttk.Entry(columns_frame, textvariable=name_column_var)
        name_column_entry.grid(row=1, column=1, sticky="ew", pady=2, padx=(10, 0))

        columns_frame.columnconfigure(1, weight=1)

        # Botones
        buttons_frame = ttk.Frame(dialog)
        buttons_frame.pack(fill=tk.X, padx=20, pady=(10, 20))

        def import_csv_async():
            try:
                csv_file = csv_file_var.get()
                target_table = target_table_var.get()

                if not csv_file:
                    messagebox.showerror("Error", "Debe seleccionar un archivo CSV.")
                    return

                if not target_table:
                    messagebox.showerror("Error", "Debe seleccionar una tabla destino.")
                    return

                # Mostrar progreso
                progress_label = ttk.Label(buttons_frame, text="⌛ Importando datos...")
                progress_label.pack(side=tk.LEFT, padx=(0, 10))

                # Realizar la importación
                success, imported_count = self.connector.import_csv_to_table(
                    csv_file, target_table,
                    course_column_var.get(),
                    name_column_var.get()
                )

                # Ocultar progreso
                progress_label.destroy()

                if success:
                    messagebox.showinfo("Éxito",
                                      f"Importación completada!\n"
                                      f"Se importaron {imported_count} registros.")
                    dialog.destroy()
                    self.refresh_tables()
                else:
                    messagebox.showerror("Error", "No se pudo importar el CSV.")

            except Exception as e:
                messagebox.showerror("Error", f"Error en importación:\n{str(e)}")

        ttk.Button(buttons_frame, text="📤 Importar", command=import_csv_async).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(buttons_frame, text="❌ Cancelar", command=dialog.destroy).pack(side=tk.RIGHT)

        ttk.Label(dialog, text="\n💡 Si el CSV no tiene nombres de columnas,\n"
                              "   se usarán automáticamente la columna 1 para 'course'\n"
                              "   y la columna 2 para 'name'.", justify=tk.LEFT).pack(padx=20)

    def select_table_for_scraping(self):
        """Seleccionar una tabla para usar en scraping."""
        selected_items = self.tables_tree.selection()

        if not selected_items:
            messagebox.showwarning("Seleccionar Tabla",
                                 "Por favor, selecciona una tabla de la lista.")
            return

        # Obtener la tabla seleccionada
        selected_table = self.tables_tree.item(selected_items[0])['values'][0]

        # Establecer como tabla por defecto
        self.default_table_var.set(selected_table)
        self.save_default_config()

        messagebox.showinfo("Tabla Seleccionada",
                          f"La tabla '{selected_table}' ha sido seleccionada como\n"
                          f"la tabla por defecto para scraping.\n\n"
                          f"Esta tabla se utilizará automáticamente en\n"
                          f"las próximas operaciones de scraping.")

    def save_default_config(self):
        """Guardar la configuración por defecto."""
        try:
            selected_table = self.default_table_var.get()

            if selected_table:
                cloud_config = self.config_manager.get_cloud_config()
                cloud_config['default_table'] = selected_table
                self.config_manager.save_config()

                messagebox.showinfo("Configuración Guardada",
                                  f"Tabla por defecto establecida: '{selected_table}'")
            else:
                messagebox.showwarning("Tabla No Seleccionada",
                                     "Por favor, selecciona una tabla de la lista.")

        except Exception as e:
            messagebox.showerror("Error", f"Error guardando configuración:\n{str(e)}")


class DatabaseConfigWindow(tk.Toplevel):
    """
    Ventana dedicada para configuración de base de datos.
    Puede ser abierta desde el menú principal o desde otras partes de la aplicación.
    """

    def __init__(self, parent=None):
        """
        Inicializar ventana de configuración de base de datos.

        Args:
            parent: Ventana padre
        """
        super().__init__(parent)

        self.title("🔧 Configuración de Base de Datos - SQLite Cloud")
        self.geometry("800x700")
        self.resizable(False, False)

        # Centrar en la pantalla
        self.center_window()

        # Crear la pestaña de configuración
        self.database_tab = DatabaseConfigTab(self)

    def center_window(self):
        """Centrar la ventana en la pantalla."""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')