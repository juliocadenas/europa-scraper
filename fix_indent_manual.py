import os

file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

# Define the correct block with explicit indentation
# 1386: if total_courses == 0: (10 spaces)
# Body starts at 14 spaces.

correct_block_14 = [
    '              # Cleanup empty file if exists (Auto-fix)\n',
    '              if os.path.exists(output_file):\n',
    '                  try:\n',
    '                      with open(output_file, "r", encoding="utf-8") as f:\n',
    '                          content_lines = f.readlines()\n',
    '                      if len(content_lines) <= 1:\n',
    '                          logger.info(f"🗑️ Eliminando archivo vacío durante early exit: {output_file}")\n',
    '                          os.remove(output_file)\n',
    '                  except Exception as e:\n',
    '                      logger.error(f"Error cleaning up empty file: {e}")\n'
]

# For the second occurrence (line ~1418), check indentation.
# 1416: if not all_search_results: (10 spaces?)
# Let's verify line 1417 logger indentation.
# It should be same as 1387 (14 spaces).

# We will read the file, identify the start/end of the botched blocks, and replace them.

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False

for i, line in enumerate(lines):
    if skip:
        if 'logger.error(f"Error cleaning up empty file' in line:
            skip = False
        continue

    # Identify the start of our broken block
    if 'Cleanup empty file if exists (Auto-fix)' in line:
        # We found the start. Write the correct block.
        new_lines.extend(correct_block_14)
        skip = True # Skip until end of old block
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Applied manual indentation fix.")
