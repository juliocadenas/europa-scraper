import os

file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

cleanup_code = [
    '            # Cleanup empty file if exists (Auto-fix)\n',
    '            if os.path.exists(output_file):\n',
    '                try:\n',
    '                    with open(output_file, "r", encoding="utf-8") as f:\n',
    '                        content_lines = f.readlines()\n',
    '                    if len(content_lines) <= 1:\n',
    '                        logger.info(f"🗑️ Eliminando archivo vacío durante early exit: {output_file}")\n',
    '                        os.remove(output_file)\n',
    '                except Exception as e:\n',
    '                    logger.error(f"Error cleaning up empty file: {e}")\n'
]

new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    
    # Fix 1: No courses found
    if 'logger.warning("No se encontraron cursos en el rango especificado")' in line:
        # Check if next line is 'return []' (ignoring whitespace)
        if i + 1 < len(lines) and 'return []' in lines[i+1]:
            new_lines.extend(cleanup_code)

    # Fix 2: No search results found
    # This block has a progress callback before return, so we insert before return []
    if 'progress_callback(100, "No se encontraron resultados para procesar")' in line:
         if i + 1 < len(lines) and 'return []' in lines[i+1]:
            new_lines.extend(cleanup_code)

# Check if we also need to catch the case where progress_callback is NOT called (if it's None)
# The code is:
# if not all_search_results:
#    logger...
#    if progress_callback:
#        progress_callback(...)
#    return []

# My simplistic parser above only catches if progress_callback is called.
# But indentation of 'return []' is what matters. 
# Let's try a different approach: Find 'logger.warning("No se encontraron resultados para procesar")'
# Then find the next 'return []' at same indentation level.

# Re-reading logic to be safer.
new_lines = []
skip = False
for i, line in enumerate(lines):
    new_lines.append(line)
    
    if 'logger.warning("No se encontraron cursos en el rango especificado")' in line:
        # Insert cleanup immediately
        new_lines.extend(cleanup_code)
        
    if 'logger.warning("No se encontraron resultados para procesar")' in line:
        # Insert cleanup immediately
        # It's okay if it runs before progress callback
        new_lines.extend(cleanup_code)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Scraper controller patched successfully.")
