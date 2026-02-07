
import os

file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Based on view_file 125-145 (1-based), indices 124-144
# Line 135 (index 134) starts the bad block "description = ..."
# Line 144 (index 143) starts "except ..."

# Range to fix body: 135 to 143 (indices 134 to 142) -> force 12 spaces
# Range to fix except: 144 (index 143) -> force 8 spaces

for i in range(134, 143):
    line = lines[i].lstrip()
    if line.strip(): # if not empty
        lines[i] = ' ' * 12 + line
    else:
        lines[i] = '\n' # preserve empty lines but clean them

# Fix except line
lines[143] = ' ' * 8 + lines[143].lstrip()

# Check lines after except (145+)
# Indices 144 to 153 (approx) should be 12 spaces.
# Let's verify up to line 150 (index 149)
for i in range(144, 153):
     line = lines[i].lstrip()
     if line.strip():
         lines[i] = ' ' * 12 + line

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed indentation.")
