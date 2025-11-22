@echo off
echo ===================================================
echo CORDIS Europa CSV Scraper - Reparacion de Archivo CSV
echo ===================================================
echo.
echo Este script reparara el archivo CSV para asegurar que
echo tenga las columnas 'sic_code' y 'course_name' necesarias.
echo.
echo IMPORTANTE: Se creara una copia de respaldo del archivo original.
echo.
pause

python repair_csv.py

echo.
echo Proceso completado.
echo.
pause
