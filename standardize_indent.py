
import os

file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Indicies for lines 1323 to 1358 (1-based in view)
# Indices 1322 to 1357

for i in range(1322, 1358):
    line = lines[i].lstrip()
    if not line.strip():
        lines[i] = '\n'
        continue
    
    # Check if it starts with 'if', 'elif', 'else'
    if line.startswith('if ') or line.startswith('elif ') or line.startswith('else:') or line.startswith('require_keywords =') or line.startswith('processed_results ='):
        lines[i] = ' ' * 10 + line
    else:
        # Likely content of the if/else blocks
        lines[i] = ' ' * 14 + line

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Standardized indentation for lines 1323-1358")
