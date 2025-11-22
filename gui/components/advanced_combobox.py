import tkinter as tk
from tkinter import ttk, font
import logging
from typing import List, Tuple, Callable, Optional, Any, Dict, Union

logger = logging.getLogger(__name__)

class AdvancedCombobox(ttk.Frame):
  """
  Enhanced combobox that supports code-description pairs and searching.
  Adaptable to different data formats.
  """
  
  def __init__(
      self, 
      master, 
      values: List[Any] = None, 
      width: int = 30,
      label: str = None,
      placeholder: str = "Select or search...",
      on_select: Callable = None,
      display_format: str = "both",  # "code", "description", or "both"
      **kwargs
  ):
      """
      Initialize the advanced combobox.
      
      Args:
          master: Parent widget
          values: List of values (strings or tuples of code-description pairs)
          width: Width of the combobox
          label: Optional label for the combobox
          placeholder: Placeholder text
          on_select: Callback function when an item is selected
          display_format: How to display code-description pairs
          **kwargs: Additional arguments for the frame
      """
      # Extraer on_select y display_format para que no se pasen a la clase base
      self.on_select_callback = on_select
      self.display_format = display_format
      
      # Eliminar on_select y display_format de kwargs si están presentes
      kwargs_copy = kwargs.copy()
      if 'on_select' in kwargs_copy:
          del kwargs_copy['on_select']
      if 'display_format' in kwargs_copy:
          del kwargs_copy['display_format']
      
      super().__init__(master, **kwargs_copy)
      
      self.values = values or []
      self.placeholder = placeholder
      self.search_var = tk.StringVar()
      self.selected_item = None
      
      # Datos internos para manejo de códigos y descripciones
      self._codes = []
      self._descriptions = []
      self._display_list = []
      
      # Create a frame for the label and combobox
      self.content_frame = ttk.Frame(self)
      self.content_frame.pack(fill=tk.X, expand=True)
      
      # Add label if provided
      if label:
          self.label = ttk.Label(
              self.content_frame, 
              text=label,
              font=("Arial", 12)
          )
          self.label.pack(side=tk.TOP, anchor=tk.W, pady=(0, 2))
      
      # Create the combobox with larger font
      self.combobox = ttk.Combobox(
          self.content_frame, 
          textvariable=self.search_var,
          width=width,
          font=("Arial", 12)
      )
      self.combobox.pack(fill=tk.X, expand=True)
      
      # Set placeholder
      self.combobox.set(placeholder)
      
      # Bind events
      self.combobox.bind("<KeyRelease>", self._on_key_release)
      self.combobox.bind("<<ComboboxSelected>>", self._on_select)
      self.combobox.bind("<FocusIn>", self._on_focus_in)
      self.combobox.bind("<FocusOut>", self._on_focus_out)
      
      # Set initial values
      self._update_values(self.values)
  
  def _format_item(self, item: Any) -> str:
      """
      Format an item for display in the combobox.
      
      Args:
          item: Item to format (string or tuple)
          
      Returns:
          Formatted string
      """
      if isinstance(item, tuple) and len(item) >= 2:
          code, description = item[0], item[1]
          if self.display_format == "code":
              return str(code)
          elif self.display_format == "description":
              return str(description)
          else:  # "both"
              return f"{code} - {description}"
      else:
          return str(item)
  
  def _update_values(self, values: List[Any]):
      """
      Update the combobox values.
      
      Args:
          values: New values for the combobox
      """
      self.values = values or []
      
      # Actualizar las listas internas
      self._codes = []
      self._descriptions = []
      self._display_list = []
      
      for item in self.values:
          if isinstance(item, tuple) and len(item) >= 2:
              code, description = item[0], item[1]
              self._codes.append(code)
              self._descriptions.append(description)
              self._display_list.append(self._format_item(item))
          else:
              # Para valores que no son tuplas
              self._codes.append(str(item))
              self._descriptions.append(str(item))
              self._display_list.append(str(item))
      
      self.formatted_values = self._display_list
      self.combobox['values'] = self.formatted_values
  
  def _on_key_release(self, event):
      """
      Handle key release events for searching.
      
      Args:
          event: Key event
      """
      # Skip special keys
      if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Return', 'Tab'):
          return
          
      search_term = self.search_var.get().lower()
      
      # If empty, show all values
      if not search_term or search_term == self.placeholder.lower():
          self.combobox['values'] = self.formatted_values
          return
      
      # Determinar si la búsqueda es numérica o alfabética
      is_numeric_search = search_term and search_term[0].isdigit()
      
      # Filter values based on search term
      filtered_indices = []
      
      for i, (code, description) in enumerate(zip(self._codes, self._descriptions)):
          if is_numeric_search:
              # Buscar coincidencias que inicien con los números en el código
              if str(code).lower().startswith(search_term):
                  filtered_indices.append(i)
          else:
              # Buscar coincidencias que inicien con las letras en la descripción
              if str(description).lower().startswith(search_term):
                  filtered_indices.append(i)
              # También buscar en el código si no es numérico
              elif str(code).lower().startswith(search_term):
                  filtered_indices.append(i)
      
      # Si no hay coincidencias exactas, buscar en cualquier parte del texto
      if not filtered_indices:
          for i, (code, description) in enumerate(zip(self._codes, self._descriptions)):
              if search_term in str(code).lower() or search_term in str(description).lower():
                  filtered_indices.append(i)
      
      filtered_values = [self.formatted_values[i] for i in filtered_indices]
      self.combobox['values'] = filtered_values
      
      # Open dropdown if we have filtered values
      if filtered_values:
          self.combobox.event_generate('<Down>')
  
  def _on_select(self, event):
      """
      Handle selection events.
      
      Args:
          event: Selection event
      """
      selected_text = self.combobox.get()
      
      # Find the original item
      for i, formatted in enumerate(self.formatted_values):
          if formatted == selected_text:
              if i < len(self._codes) and i < len(self._descriptions):
                  self.selected_item = (self._codes[i], self._descriptions[i])
              else:
                  self.selected_item = selected_text
              break
      else:
          self.selected_item = selected_text
      
      # Call the callback if provided
      if self.on_select_callback:
          self.on_select_callback(self.selected_item)
  
  def _on_focus_in(self, event):
      """
      Handle focus in events.
      
      Args:
          event: Focus event
      """
      if self.combobox.get() == self.placeholder:
          self.combobox.set('')
  
  def _on_focus_out(self, event):
      """
      Handle focus out events.
      
      Args:
          event: Focus event
      """
      if not self.combobox.get():
          self.combobox.set(self.placeholder)
  
  def get(self) -> Any:
      """
      Get the selected item.
      
      Returns:
          Selected item (original value, not formatted)
      """
      return self.selected_item
  
  def set(self, value: Any):
      """
      Set the selected item.
      
      Args:
          value: Item to select
      """
      # Find the item in values
      if isinstance(value, tuple) and len(value) >= 2:
          code, desc = value[0], value[1]
          for i, (c, d) in enumerate(zip(self._codes, self._descriptions)):
              if c == code and d == desc:
                  self.combobox.set(self.formatted_values[i])
                  self.selected_item = value
                  break
          else:
              # Si no se encuentra, intentar agregar
              self._codes.append(code)
              self._descriptions.append(desc)
              display_value = self._format_item(value)
              self._display_list.append(display_value)
              self.formatted_values = self._display_list
              self.combobox['values'] = self.formatted_values
              self.combobox.set(display_value)
              self.selected_item = value
      else:
          # Si es un valor simple, intentar encontrarlo
          for i, item in enumerate(self.values):
              if item == value:
                  self.combobox.set(self.formatted_values[i])
                  self.selected_item = item
                  break
          else:
              # Si no se encuentra, establecer directamente
              self.combobox.set(str(value))
              self.selected_item = value
  
  def set_values(self, values: List[Any]):
      """
      Set new values for the combobox.
      
      Args:
          values: New values
      """
      self._update_values(values)
      self.selected_item = None
      self.combobox.set(self.placeholder)
  
  def clear(self):
      """
      Clear the selection.
      """
      self.selected_item = None
      self.combobox.set(self.placeholder)
  
  def get_selected_value(self):
      """
      Retorna la tupla (código, descripción) seleccionada.
      Compatible con la implementación adjunta.
      
      Returns:
          Tupla (código, descripción) o None
      """
      return self.selected_item
  
  def search_and_select(self, search_text=None):
      """
      Busca y selecciona el primer ítem que comience con el texto de búsqueda.
      
      Args:
          search_text: Texto a buscar (opcional, usa el texto actual si no se proporciona)
          
      Returns:
          True si se encontró y seleccionó un ítem, False en caso contrario
      """
      if search_text is None:
          search_text = self.search_var.get()
          
      if not search_text:
          return False
      
      search_text = search_text.lower()
      
      # Determinar si la búsqueda es numérica o alfabética
      is_numeric_search = search_text and search_text[0].isdigit()
      
      for i, (code, desc) in enumerate(zip(self._codes, self._descriptions)):
          if is_numeric_search:
              # Buscar coincidencias que inicien con los números en el código
              if str(code).lower().startswith(search_text):
                  self._select_item(i)
                  return True
          else:
              # Buscar coincidencias que inicien con las letras en la descripción
              if str(desc).lower().startswith(search_text):
                  self._select_item(i)
                  return True
      
      return False
  
  def _select_item(self, index):
      """
      Selecciona un ítem específico en el combobox.
      
      Args:
          index: Índice del ítem a seleccionar
      """
      if 0 <= index < len(self.formatted_values):
          self.combobox.current(index)
          self.combobox.set(self.formatted_values[index])
          
          if index < len(self._codes) and index < len(self._descriptions):
              self.selected_item = (self._codes[index], self._descriptions[index])
          else:
              self.selected_item = self.formatted_values[index]
          
          # Llamar al callback si existe
          if self.on_select_callback:
              self.on_select_callback(self.selected_item)
          
          return True
      
      return False
