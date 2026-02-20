He añadido la línea de depuración final. Ahora es el momento de la verdad.

**Por favor, haz esto por última vez:**

1.  **Asegúrate de que el servidor está (teóricamente) reiniciado.**
2.  **Ejecuta `INICIAR_CLIENTE.bat` (o `INICIAR_FRONTEND.bat`).**
3.  **Inicia un trabajo de scraping y déjalo terminar.**
4.  Copia **TODO** el contenido de la consola y pégalo aquí.

Ahora, en el log aparecerá una línea que empieza con `DEBUG GUI RENDER:`. Esta línea me mostrará la información en crudo que el servidor le está enviando a tu cliente.

*   **Si esa información no contiene las estadísticas**, confirmará al 100% que un proceso de servidor antiguo y obsoleto se está ejecutando en tu máquina, y te daré los comandos exactos para encontrarlo y destruirlo.
*   **Si la información sí contiene las estadísticas**, entonces el error está en la forma en que la GUI lo muestra (lo cual dudo, pero el log nos lo dirá).

Con este log, la raíz del problema quedará expuesta y podré darte la solución definitiva.