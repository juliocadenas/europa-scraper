import os

file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    # Fix return indentation
    # 1398:             return [] (12 spaces) -> needs 14
    # The erroneous lines have 12 spaces.
    
    # We look for '            return []' (12 spaces)
    if line.startswith('            return []'):
        # Check context: Is it inside 'if total_courses == 0' or 'if not all_search_results'?
        # In both cases, the preceding block (which was 12 spaces, now fixed to 14) ends with logger...
        # So we definitely want 14 spaces.
        new_lines.append('              return []\n')
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed return indentation.")
