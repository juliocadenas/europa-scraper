
import os

file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We want to keep the first occurrence of _process_single_result (lines 108+)
# and remove the ones starting around 699 and 844.

new_lines = []
skip_mode = False
process_single_count = 0

for i, line in enumerate(lines):
    if 'async def _process_single_result' in line:
        process_single_count += 1
        if process_single_count > 1:
            print(f"Skipping duplicate _process_single_result starting at index {i}")
            skip_mode = True
        else:
            new_lines.append(line)
            continue
    
    # Check if we are at the start of another method that should stop skip_mode
    if skip_mode:
        if ('async def ' in line or 'def ' in line) and not line.startswith(' '):
            if '_process_single_result' not in line:
                skip_mode = False
                new_lines.append(line)
            else:
                # Still in a duplicate
                pass
        continue
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Cleanup finished. Found {process_single_count} occurrences of _process_single_result, kept 1.")
