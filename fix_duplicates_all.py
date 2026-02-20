
import os

file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Indicies 0-based.
# Line 108 in view (1-based) is index 107.
# Line 158 in view (1-based) is index 157.

# I want to remove lines 107 to 156 (inclusive of 156? check line 157).
# Line 157 was empty.
# Line 158 (index 157) is the NEW method definition.

start_remove = 107
# Find where the NEW method starts.
# Look for "async def _process_single_result" that has "require_keywords" param.
end_remove = -1

found_first = False
new_method_index = -1

for i, line in enumerate(lines):
    if 'async def _process_single_result' in line:
        if not found_first:
            # This follows __init__, so it is likely the one at 108.
            # But verifying index.
            if i > 100 and i < 120:
                print(f"Found first (old) method at index {i}")
                start_remove = i
                found_first = True
        else:
            # Found second occurrence
            print(f"Found second (new) method at index {i}")
            new_method_index = i
            break

if new_method_index != -1 and found_first:
    # Delete from start_remove to new_method_index (exclusive)
    print(f"Removing lines from {start_remove} to {new_method_index}")
    keep_lines = lines[:start_remove] + lines[new_method_index:]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(keep_lines)
    print("Fixed duplicates.")
else:
    print("Could not find both duplicates. Aborting.")
