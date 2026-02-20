"""
Worker Status Frame
-------------------
Componente para mostrar el estado detallado de los workers.
"""

import tkinter as tk
from tkinter import ttk

class WorkerStatusFrame(ttk.LabelFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, text="Estado de Workers", padding=10, **kwargs)
        
        self.workers = {}
        
        # Crear el Treeview
        self.tree = ttk.Treeview(
            self,
            columns=("ID", "Estado", "Tarea Actual", "Progreso"),
            show="headings"
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # Definir las cabeceras
        self.tree.heading("ID", text="ID")
        self.tree.heading("Estado", text="Estado")
        self.tree.heading("Tarea Actual", text="Tarea Actual")
        self.tree.heading("Progreso", text="Progreso")
        
        # Definir el ancho de las columnas
        self.tree.column("ID", width=40, anchor="center", stretch=False)
        self.tree.column("Estado", width=80, anchor="w")
        self.tree.column("Tarea Actual", width=300, anchor="w")
        self.tree.column("Progreso", width=120, anchor="center")

        self.tree.tag_configure("working", background="#FFDDC1")
        self.tree.tag_configure("idle", background="#D4EDDA")

    def update_status(self, worker_states):
        """
        Actualiza la tabla con el estado más reciente de los workers.
        """
        for worker_id, data in worker_states.items():
            status = data.get("status", "desconocido").capitalize()
            current_task = data.get("current_task", "N/A")
            progress = data.get("progress", 0)

            # Formatear la tarea si ha finalizado
            if 'Finished:' in current_task:
                task_display = "Finished"
            else:
                task_display = current_task

            # Truncar si es demasiado largo para evitar fila gigante
            if len(task_display) > 100:
                task_display = task_display[:97] + "..."

            # Determinar el estado para la visualización
            state_display = "Working" if status.lower() == "working" else "Idle"
            
            # Formatear el progreso
            progress_str = f"{progress:.0f}%"

            tag = "working" if state_display == "Working" else "idle"

            # LÓGICA DE PERSISTENCIA:
            # Si el worker ya tiene una fila, revisamos si su tarea anterior TERMINÓ.
            # Si terminó (estaba en 'Completed' o 'Finished') y ahora viene una nueva actualización (Working),
            # entonces "olvidamos" la fila anterior (dejándola como historial visible) y creamos una nueva.
            if worker_id in self.workers:
                item_id = self.workers[worker_id]
                try:
                    current_values = self.tree.item(item_id, "values")
                    prev_status = current_values[1] # La columna "Estado" es la índice 1
                    
                    # Si antes estaba completado y ahora está trabajando de nuevo, es una NUEVA tarea.
                    # Dejamos la fila vieja como constancia y forzamos crear una nueva.
                    if "Completed" in prev_status or "Finished" in prev_status:
                        if state_display == "Working":
                            del self.workers[worker_id] 
                except Exception:
                    pass # Si hay error leyendo, asumimos que no hay fila válida

            if worker_id not in self.workers:
                # Insertar nueva fila (al final de la lista)
                item_id = self.tree.insert("", "end", iid=None, values=( # iid=None para autogenerar ID único
                    worker_id,
                    state_display,
                    task_display,
                    progress_str
                ), tags=(tag,))
                self.workers[worker_id] = item_id
            else:
                # Actualizar fila existente (misma tarea en progreso)
                self.tree.item(self.workers[worker_id], values=(
                    worker_id,
                    state_display,
                    task_display,
                    progress_str
                ), tags=(tag,))
