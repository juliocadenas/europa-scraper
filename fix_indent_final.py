import os

file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Read line 1387 (index 1386) to get reference indentation
# Step 987 showed: 1387:               logger.warning...
# Note: 1386: if total_courses == 0:
# logger.warning is inside if.

# Let's find index of 'logger.warning("No se encontraron cursos...'
idx_ref = -1
for i, line in enumerate(lines):
    if 'logger.warning("No se encontraron cursos en el rango especificado")' in line:
        idx_ref = i
        break

if idx_ref == -1:
    print("Error: Could not find reference line")
    exit(1)

# Get spaces
ref_indent = len(lines[idx_ref]) - len(lines[idx_ref].lstrip())
print(f"Reference indentation at line {idx_ref+1}: {ref_indent}")

# My block starts at idx_ref + 1
# I want to indent it to SAME level as ref_indent (14 spaces likely).
# Or maybe more?
# 1386: if ... (10)
# 1387: logger ... (14)
# 1388: # Cleanup (should be 14)
# 1389: if os... (should be 14)

# Wait. Python 'if' body indentation must be consistent.
# If logger is at 14, then next statements must be at 14.
# My `multi_replace` put them at 12.
# 12 < 14. So "unindent does not match any outer".
# 10 is outer. 14 is inner. 12 is invalid.

target_indent = ' ' * ref_indent

new_lines = []
in_cleanup_block = False

for i, line in enumerate(lines):
    if 'Cleanup empty file if exists (Auto-fix)' in line:
        in_cleanup_block = True
    
    if in_cleanup_block:
        stripped = line.lstrip()
        new_lines.append(target_indent + stripped)
        
        if 'logger.error(f"Error cleaning up empty file' in line:
            in_cleanup_block = False
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
    
print("Fixed indentation successfully.")
