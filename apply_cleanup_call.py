import os

file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
inserted = False

for i, line in enumerate(lines):
    # Determine context. We are looking for 'return processed_results' 
    # appearing after 'logger.info(f"Estadísticas finales:...'
    # Wait, simple search:
    if 'return processed_results' in line and not inserted:
        # Check indentation
        indent = line[:line.find('return')]
        
        # Insert cleanup call 
        new_lines.append(f'{indent}# Final cleanup check to ensure no empty files are left behind\n')
        new_lines.append(f'{indent}self.result_manager.cleanup_if_empty()\n')
        new_lines.append('\n')
        new_lines.append(line)
        inserted = True
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

if inserted:
    print("Successfully inserted cleanup call.")
else:
    print("Error: Could not find insertion point.")
