import tkinter as tk
from tkinter import ttk, messagebox
import logging

logger = logging.getLogger(__name__)

class CaptchaConfigFrame(ttk.LabelFrame):
    """
    Frame de configuración para el solucionador de CAPTCHAs.
    """
    
    def __init__(self, parent, config_manager, callback=None):
        """
        Inicializa el frame de configuración.
        
        Args:
            parent: Widget padre
            config_manager: Instancia del gestor de configuración (Config)
            callback: Función a llamar cuando se guarda la configuración
        """
        super().__init__(parent, text="Configuración de CAPTCHA", padding="10")
        self.parent = parent
        self.config_manager = config_manager
        self.callback = callback
        
        # Configurar estilos
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TLabel", background="#f0f0f0", font=("Arial", 10))
        self.style.configure("TButton", font=("Arial", 10))
        self.style.configure("Header.TLabel", font=("Arial", 12, "bold"))
        
        # Crear widgets
        self._create_widgets()
        
        # Cargar configuración actual
        self._load_current_config()
    
    def _create_widgets(self):
        """Crea los widgets de la interfaz."""
        # Título
        self.title_label = ttk.Label(
            self,
            text="Configuración del Solucionador de CAPTCHAs",
            style="Header.TLabel"
        )
        self.title_label.pack(pady=(0, 20))
        
        # Frame para la configuración
        self.captcha_frame = ttk.LabelFrame(
            self,
            text="Proveedor de Servicio",
            padding="10"
        )
        self.captcha_frame.pack(fill=tk.X, pady=10)

        # Checkbox para habilitar la resolución de captchas
        self.enabled_var = tk.BooleanVar()
        self.enabled_check = ttk.Checkbutton(
            self.captcha_frame,
            text="Habilitar resolución de CAPTCHAs",
            variable=self.enabled_var,
            command=self._toggle_service_options
        )
        self.enabled_check.pack(fill=tk.X, pady=5)
        
        # Opciones de servicio (se mostrarán/ocultarán)
        self.service_options_frame = ttk.Frame(self.captcha_frame)
        self.service_options_frame.pack(fill=tk.X, pady=5)

        # Selector de servicio
        self.service_label = ttk.Label(
            self.service_options_frame,
            text="Servicio:"
        )
        self.service_label.pack(side=tk.LEFT, padx=(0, 10))

        self.service_var = tk.StringVar()
        self.service_combo = ttk.Combobox(
            self.service_options_frame,
            textvariable=self.service_var,
            values=["Manual", "2Captcha"], # Añadir otros servicios aquí
            state="readonly"
        )
        self.service_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.service_combo.bind("<<ComboboxSelected>>", self._toggle_api_key_field)

        # Campo para la clave API
        self.api_key_frame = ttk.Frame(self.captcha_frame)
        self.api_key_frame.pack(fill=tk.X, pady=5, padx=20)
        
        self.api_key_label = ttk.Label(
            self.api_key_frame,
            text="Clave API:"
        )
        self.api_key_label.pack(side=tk.LEFT, padx=(0, 10))
        
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(
            self.api_key_frame,
            textvariable=self.api_key_var,
            width=30,
            show="*"
        )
        self.api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Botón para mostrar/ocultar la clave API
        self.show_api_key_var = tk.BooleanVar(value=False)
        self.show_api_key_check = ttk.Checkbutton(
            self.api_key_frame,
            text="Mostrar",
            variable=self.show_api_key_var,
            command=self._toggle_api_key_visibility
        )
        self.show_api_key_check.pack(side=tk.LEFT, padx=(10, 0))
        
        # Frame para los botones
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # Botón para guardar
        self.save_button = ttk.Button(
            self.button_frame,
            text="Guardar",
            command=self._save_config
        )
        self.save_button.pack(side=tk.RIGHT, padx=5)
        
        # Inicialmente deshabilitar las opciones
        self._toggle_service_options()

    def _toggle_service_options(self):
        """Habilita o deshabilita las opciones de servicio según el checkbox principal."""
        if self.enabled_var.get():
            for child in self.service_options_frame.winfo_children():
                child.configure(state="normal")
            self._toggle_api_key_field()
        else:
            for child in self.service_options_frame.winfo_children():
                child.configure(state="disabled")
            self._toggle_api_key_field(force_disable=True)

    def _toggle_api_key_field(self, event=None, force_disable=False):
        """Habilita o deshabilita el campo de clave API según el servicio seleccionado."""
        is_manual = self.service_var.get() == "Manual"
        should_disable = is_manual or force_disable or not self.enabled_var.get()

        if not should_disable:
            self.api_key_entry.config(state="normal")
            self.show_api_key_check.config(state="normal")
        else:
            self.api_key_var.set("") # Limpiar el valor de la API Key
            self.api_key_entry.config(state="disabled")
            self.show_api_key_check.config(state="disabled")
    
    def _toggle_api_key_visibility(self):
        """Muestra u oculta la clave API."""
        if self.show_api_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")
    
    def _load_current_config(self):
        """Carga la configuración actual desde el config_manager."""
        try:
            enabled = self.config_manager.get("captcha_solving_enabled", False)
            service = self.config_manager.get("captcha_service", "Manual")
            api_key = self.config_manager.get("captcha_api_key", "")

            self.enabled_var.set(enabled)
            self.service_var.set(service)
            self.api_key_var.set(api_key)
            
            self._toggle_service_options()
            
        except Exception as e:
            logger.error(f"Error cargando configuración de CAPTCHA: {str(e)}")
    
    def _save_config(self):
        """Guarda la configuración en el config_manager."""
        try:
            enabled = self.enabled_var.get()
            service = self.service_var.get()
            api_key = self.api_key_var.get().strip()

            # Si el servicio es manual, la clave API no es necesaria y debe ser vacía
            if service == "Manual":
                api_key = ""

            print(f"DEBUG: enabled={enabled}, service={service}, api_key='{api_key}'")

            if enabled and service != "Manual" and not api_key:
                messagebox.showerror("Error", "Por favor, ingrese una clave API para el servicio seleccionado.")
                return

            self.config_manager.set("captcha_solving_enabled", enabled)
            self.config_manager.set("captcha_service", service)
            self.config_manager.set("captcha_api_key", api_key if enabled else "")
            
            if self.config_manager.save_config():
                messagebox.showinfo("Configuración Guardada", "La configuración de CAPTCHA ha sido guardada correctamente.")
                if self.callback:
                    self.callback()
            else:
                messagebox.showerror("Error", "No se pudo guardar la configuración. Revise los logs para más detalles.")

        except Exception as e:
            logger.error(f"Error guardando configuración de CAPTCHA: {str(e)}")
            messagebox.showerror("Error", f"Ocurrió un error al guardar la configuración: {str(e)}")

# --- El resto de la clase CaptchaConfigWindow puede permanecer igual o ser adaptada ---

class CaptchaConfigWindow:
    """
    Ventana de configuración para el solucionador de CAPTCHAs.
    """
    
    def __init__(self, parent, config_manager, callback=None):
        """
        Inicializa la ventana de configuración.
        
        Args:
            parent: Widget padre
            config_manager: Instancia del gestor de configuración (Config)
            callback: Función a llamar cuando se guarda la configuración
        """
        self.parent = parent
        
        # Crear ventana
        self.window = tk.Toplevel(parent)
        self.window.title("Configuración de CAPTCHA")
        self.window.geometry("500x350")
        self.window.minsize(450, 300)
        self.window.transient(parent)
        self.window.grab_set()
        
        # Centrar la ventana
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        
        # Crear el frame de configuración
        self.config_frame = CaptchaConfigFrame(
            self.window,
            config_manager=config_manager,
            callback=self._on_save
        )
        self.config_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Añadir botón de cancelar
        self.cancel_button = ttk.Button(
            self.config_frame.button_frame,
            text="Cancelar",
            command=self.window.destroy
        )
        self.cancel_button.pack(side=tk.RIGHT, padx=5)
    
    def _on_save(self):
        """Callback cuando se guarda la configuración."""
        # La lógica de callback puede ser manejada directamente en el frame
        # o aquí si es necesario. Por ahora, solo cerramos la ventana.
        self.window.destroy()
