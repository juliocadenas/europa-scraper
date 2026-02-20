import tkinter as tk
from tkinter import ttk, messagebox
import logging
import json
import os
from typing import List, Dict, Optional, Callable

logger = logging.getLogger(__name__)

class ProxyConfigFrame(ttk.LabelFrame):
    """
    Frame de configuración de proxies para el scraper.
    """
    
    def __init__(self, parent, proxy_manager=None, callback: Optional[Callable] = None):
        """
        Inicializa el frame de configuración de proxies.
        
        Args:
            parent: Widget padre
            proxy_manager: Instancia del gestor de proxies
            callback: Función a llamar cuando se guarden los cambios
        """
        super().__init__(parent, text="Configuración de Proxies", padding="10")
        self.parent = parent
        self.proxy_manager = proxy_manager
        self.callback = callback
        
        # Variables
        self.proxies = []
        self.proxy_var = tk.StringVar()
        self.protocol_var = tk.StringVar(value="http")
        self.host_var = tk.StringVar()
        self.port_var = tk.StringVar()
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        
        # Cargar proxies existentes
        self._load_proxies()
        
        # Crear interfaz
        self._create_widgets()
        
        # Actualizar lista de proxies
        self._update_proxy_list()
    
    def _create_widgets(self):
        """
        Crea los widgets de la interfaz.
        """
        # Frame principal
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame izquierdo (lista de proxies)
        left_frame = ttk.LabelFrame(main_frame, text="Proxies Configurados", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Lista de proxies
        self.proxy_listbox = tk.Listbox(left_frame, width=30, height=15)
        self.proxy_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar para la lista
        scrollbar = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.proxy_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.proxy_listbox.config(yscrollcommand=scrollbar.set)
        
        # Vincular evento de selección
        self.proxy_listbox.bind('<<ListboxSelect>>', self._on_proxy_select)
        
        # Frame derecho (formulario)
        right_frame = ttk.LabelFrame(main_frame, text="Configuración de Proxy", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Formulario
        form_frame = ttk.Frame(right_frame)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Protocolo
        ttk.Label(form_frame, text="Protocolo:").grid(row=0, column=0, sticky=tk.W, pady=5)
        protocol_combo = ttk.Combobox(form_frame, textvariable=self.protocol_var, values=["http", "https", "socks4", "socks5"])
        protocol_combo.grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        # Host
        ttk.Label(form_frame, text="Host:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(form_frame, textvariable=self.host_var).grid(row=1, column=1, sticky=tk.EW, pady=5)
        
        # Puerto
        ttk.Label(form_frame, text="Puerto:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(form_frame, textvariable=self.port_var).grid(row=2, column=1, sticky=tk.EW, pady=5)
        
        # Usuario
        ttk.Label(form_frame, text="Usuario (opcional):").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Entry(form_frame, textvariable=self.username_var).grid(row=3, column=1, sticky=tk.EW, pady=5)
        
        # Contraseña
        ttk.Label(form_frame, text="Contraseña (opcional):").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Entry(form_frame, textvariable=self.password_var, show="*").grid(row=4, column=1, sticky=tk.EW, pady=5)
        
        # Botones de acción para el formulario
        form_buttons_frame = ttk.Frame(form_frame)
        form_buttons_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        ttk.Button(form_buttons_frame, text="Añadir", command=self._add_proxy).pack(side=tk.LEFT, padx=5)
        ttk.Button(form_buttons_frame, text="Actualizar", command=self._update_proxy).pack(side=tk.LEFT, padx=5)
        ttk.Button(form_buttons_frame, text="Eliminar", command=self._delete_proxy).pack(side=tk.LEFT, padx=5)
        ttk.Button(form_buttons_frame, text="Limpiar", command=self._clear_form).pack(side=tk.LEFT, padx=5)
        
        # Botones de acción principales
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(buttons_frame, text="Guardar", command=self._save_proxies).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Probar Conexión", command=self._test_connection).pack(side=tk.LEFT, padx=5)
        
        # Configurar grid
        form_frame.columnconfigure(1, weight=1)
    
    def _load_proxies(self):
        """
        Carga los proxies existentes.
        """
        if self.proxy_manager:
            self.proxies = self.proxy_manager.get_all_proxies()
        else:
            # Intentar cargar desde archivo
            proxy_file = os.path.join("config", "proxies.json")
            if os.path.exists(proxy_file):
                try:
                    with open(proxy_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self.proxies = data
                        elif isinstance(data, dict) and 'proxies' in data:
                            self.proxies = data['proxies']
                except Exception as e:
                    logger.error(f"Error cargando proxies: {str(e)}")
    
    def _save_proxies(self):
        """
        Guarda los proxies configurados.
        """
        # Guardar en archivo
        os.makedirs("config", exist_ok=True)
        proxy_file = os.path.join("config", "proxies.json")
        
        try:
            with open(proxy_file, 'w', encoding='utf-8') as f:
                json.dump({'proxies': self.proxies}, f, indent=2)
            
            # Actualizar proxy manager si está disponible
            if self.proxy_manager:
                # Limpiar proxies existentes
                self.proxy_manager.proxies = []
                
                # Añadir nuevos proxies
                for proxy in self.proxies:
                    self.proxy_manager.add_proxy(proxy)
            
            # Llamar al callback si está definido
            if self.callback:
                self.callback(self.proxies)
            
            messagebox.showinfo("Éxito", "Configuración de proxies guardada correctamente.")
        
        except Exception as e:
            logger.error(f"Error guardando proxies: {str(e)}")
            messagebox.showerror("Error", f"Error guardando proxies: {str(e)}")
    
    def _update_proxy_list(self):
        """
        Actualiza la lista de proxies en la interfaz.
        """
        self.proxy_listbox.delete(0, tk.END)
        
        for proxy in self.proxies:
            # Mostrar versión enmascarada si tiene usuario/contraseña
            display_proxy = proxy
            if '@' in proxy:
                parts = proxy.split('@')
                auth_parts = parts[0].split('://')
                if len(auth_parts) > 1:
                    protocol = auth_parts[0]
                    auth = auth_parts[1]
                    if ':' in auth:
                        user, _ = auth.split(':', 1)
                        display_proxy = f"{protocol}://{user}:****@{parts[1]}"
            
            self.proxy_listbox.insert(tk.END, display_proxy)
    
    def _on_proxy_select(self, event):
        """
        Maneja la selección de un proxy en la lista.
        
        Args:
            event: Evento de selección
        """
        selection = self.proxy_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index < 0 or index >= len(self.proxies):
            return
        
        proxy = self.proxies[index]
        self.proxy_var.set(proxy)
        
        # Parsear el proxy para llenar el formulario
        self._parse_proxy(proxy)
    
    def _parse_proxy(self, proxy: str):
        """
        Parsea una URL de proxy para llenar el formulario.
        
        Args:
            proxy: URL del proxy
        """
        # Reiniciar variables
        self.protocol_var.set("http")
        self.host_var.set("")
        self.port_var.set("")
        self.username_var.set("")
        self.password_var.set("")
        
        # Formato: protocolo://[usuario:contraseña@]host:puerto
        try:
            # Extraer protocolo
            if "://" in proxy:
                protocol, rest = proxy.split("://", 1)
                self.protocol_var.set(protocol)
            else:
                rest = proxy
            
            # Extraer usuario y contraseña si existen
            if "@" in rest:
                auth, address = rest.split("@", 1)
                if ":" in auth:
                    username, password = auth.split(":", 1)
                    self.username_var.set(username)
                    self.password_var.set(password)
                else:
                    self.username_var.set(auth)
            else:
                address = rest
            
            # Extraer host y puerto
            if ":" in address:
                host, port = address.rsplit(":", 1)
                self.host_var.set(host)
                self.port_var.set(port)
            else:
                self.host_var.set(address)
        
        except Exception as e:
            logger.error(f"Error parseando proxy {proxy}: {str(e)}")
    
    def _build_proxy_url(self) -> str:
        """
        Construye una URL de proxy a partir de los valores del formulario.
        
        Returns:
            URL del proxy
        """
        protocol = self.protocol_var.get() or "http"
        host = self.host_var.get()
        port = self.port_var.get()
        username = self.username_var.get()
        password = self.password_var.get()
        
        if not host:
            raise ValueError("El host es obligatorio")
        
        if not port:
            raise ValueError("El puerto es obligatorio")
        
        # Construir URL
        if username and password:
            return f"{protocol}://{username}:{password}@{host}:{port}"
        elif username:
            return f"{protocol}://{username}@{host}:{port}"
        else:
            return f"{protocol}://{host}:{port}"
    
    def _add_proxy(self):
        """
        Añade un nuevo proxy a la lista.
        """
        try:
            proxy_url = self._build_proxy_url()
            
            # Verificar si ya existe
            if proxy_url in self.proxies:
                messagebox.showwarning("Advertencia", "Este proxy ya está en la lista.")
                return
            
            # Añadir a la lista
            self.proxies.append(proxy_url)
            
            # Actualizar interfaz
            self._update_proxy_list()
            
            # Limpiar formulario
            self._clear_form()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error añadiendo proxy: {str(e)}")
    
    def _update_proxy(self):
        """
        Actualiza un proxy existente.
        """
        selection = self.proxy_listbox.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor, seleccione un proxy para actualizar.")
            return
        
        index = selection[0]
        if index < 0 or index >= len(self.proxies):
            return
        
        try:
            proxy_url = self._build_proxy_url()
            
            # Actualizar en la lista
            self.proxies[index] = proxy_url
            
            # Actualizar interfaz
            self._update_proxy_list()
            
            # Limpiar formulario
            self._clear_form()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error actualizando proxy: {str(e)}")
    
    def _delete_proxy(self):
        """
        Elimina un proxy de la lista.
        """
        selection = self.proxy_listbox.curselection()
        if not selection:
            messagebox.showwarning("Advertencia", "Por favor, seleccione un proxy para eliminar.")
            return
        
        index = selection[0]
        if index < 0 or index >= len(self.proxies):
            return
        
        # Eliminar de la lista
        del self.proxies[index]
        
        # Actualizar interfaz
        self._update_proxy_list()
        
        # Limpiar formulario
        self._clear_form()
    
    def _clear_form(self):
        """
        Limpia el formulario.
        """
        self.protocol_var.set("http")
        self.host_var.set("")
        self.port_var.set("")
        self.username_var.set("")
        self.password_var.set("")
    
    def _test_connection(self):
        """
        Prueba la conexión con el proxy seleccionado.
        """
        selection = self.proxy_listbox.curselection()
        if not selection:
            try:
                # Probar con los valores del formulario
                proxy_url = self._build_proxy_url()
                self._test_proxy(proxy_url)
            except Exception as e:
                messagebox.showerror("Error", f"Error al construir la URL del proxy: {str(e)}")
            return
        
        index = selection[0]
        if index < 0 or index >= len(self.proxies):
            return
        
        # Probar el proxy seleccionado
        proxy_url = self.proxies[index]
        self._test_proxy(proxy_url)
    
    def _test_proxy(self, proxy_url: str):
        """
        Prueba la conexión con un proxy.
        
        Args:
            proxy_url: URL del proxy a probar
        """
        import requests
        import threading
        
        def test_thread():
            try:
                # Mostrar mensaje de espera
                status_label = ttk.Label(self, text="Probando conexión...")
                status_label.pack(pady=5)
                self.update()
                
                # Configurar proxies
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }
                
                # Realizar solicitud de prueba
                response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=10)
                
                # Verificar respuesta
                if response.status_code == 200:
                    messagebox.showinfo("Éxito", f"Conexión exitosa a través del proxy.\nIP detectada: {response.json().get('origin', 'Desconocida')}")
                else:
                    messagebox.showwarning("Advertencia", f"La conexión fue establecida, pero se recibió un código de estado inesperado: {response.status_code}")
            
            except requests.exceptions.ProxyError:
                messagebox.showerror("Error", "No se pudo conectar al proxy. Verifique la configuración.")
            except requests.exceptions.ConnectTimeout:
                messagebox.showerror("Error", "Tiempo de espera agotado al intentar conectar con el proxy.")
            except requests.exceptions.ReadTimeout:
                messagebox.showerror("Error", "Tiempo de espera agotado al intentar leer la respuesta.")
            except Exception as e:
                messagebox.showerror("Error", f"Error al probar el proxy: {str(e)}")
            finally:
                # Eliminar mensaje de espera
                status_label.destroy()
        
        # Iniciar prueba en un hilo separado
        threading.Thread(target=test_thread, daemon=True).start()
    
    def get_config(self):
        """
        Obtiene la configuración actual de proxies.
        
        Returns:
            Dict con la configuración de proxies
        """
        return {
            'proxies': self.proxies,
            'use_proxy': len(self.proxies) > 0
        }


# Para mantener compatibilidad con código existente
class ProxyConfigWindow(tk.Toplevel):
    """
    Ventana de configuración de proxies para el scraper.
    """
    
    def __init__(self, parent, proxy_manager=None, callback: Optional[Callable] = None):
        """
        Inicializa la ventana de configuración de proxies.
        
        Args:
            parent: Widget padre
            proxy_manager: Instancia del gestor de proxies
            callback: Función a llamar cuando se guarden los cambios
        """
        super().__init__(parent)
        self.parent = parent
        self.proxy_manager = proxy_manager
        self.callback = callback
        
        # Configurar ventana
        self.title("Configuración de Proxies")
        self.geometry("600x500")
        self.minsize(500, 400)
        self.resizable(True, True)
        self.transient(parent)  # Hacer que esta ventana sea dependiente de la ventana principal
        self.grab_set()  # Evitar interacción con la ventana principal mientras esta está abierta
        
        # Centrar la ventana
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'+{x}+{y}')
        
        # Crear el frame de configuración
        self.proxy_frame = ProxyConfigFrame(self, proxy_manager, callback)
        self.proxy_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Añadir botón de cerrar
        ttk.Button(self, text="Cerrar", command=self.destroy).pack(side=tk.RIGHT, padx=10, pady=10)
