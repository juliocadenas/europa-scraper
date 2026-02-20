import os

file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    # Identify my inserted lines by unique comments or logs
    if 'Cleanup empty file if exists (Auto-fix)' in line or \
       'Eliminando archivo vacío durante early exit' in line or \
       'logger.error(f"Error cleaning up empty file' in line or \
       'with open(output_file, "r", encoding="utf-8")' in line or \
       'content_lines = f.readlines()' in line or \
       'if os.path.exists(output_file):' in line or \
       'if len(content_lines) <= 1:' in line or \
       'os.remove(output_file)' in line or \
       'try:' in line and 'logger' not in line and 'return' not in line: # generic try is risky, need context?
       
       # Better check: if line matches exactly one of the inserted lines from previous patch
       # My previous patch lines started with 12 spaces.
       # I want them to have 16 spaces.
       
       # Careful: "try:" appears elsewhere.
       # My inserted 'try:' has 16 spaces (in previous patch 12 + 4 inside block? No, I defined `cleanup_code` with fixed strings)
       # In patch_scraper.py: '            if os.path.exists(output_file):\n' (12 spaces)
       # '                try:\n' (16 spaces)
       
       # Wait. If `if os.path` is 12 spaces. It matches the OUTER `if` (12 spaces).
       # But `logger` (1387) was 16 spaces.
       # So `if os.path` (12) closes the `if total...` (12) block?
       # No, `if total...` is 12. Body is 16.
       # If I insert 12. It closes the body.
       
       # So basically I need to shift ALL my inserted lines by 4 spaces.
       # How to identify them safely?
       # They are the ONLY lines with "Eliminando archivo vacío durante early exit".
       pass

# Let's iterate and re-construct.
# I know the blocks are between 1388-1397 and 1418-1427 roughly.

# I'll just check if the line contains "Auto-fix" or "early exit" and surrounding lines?
# Actually, I can just rewrite the whole file logic or use a specific replace.

# Safest: Read file, find the lines that look like my patch, indent them.
# My patch validation:
# '            # Cleanup empty file if exists (Auto-fix)\n' (Start)
# ...
# '                    logger.error(f"Error cleaning up empty file: {e}")\n' (End)

# I will scan for these blocks and indent them.

new_lines = []
in_patch_block = False

for line in lines:
    if 'Cleanup empty file if exists (Auto-fix)' in line:
        in_patch_block = True
    
    if in_patch_block:
        # Add 4 spaces
        new_lines.append('    ' + line)
        if 'logger.error(f"Error cleaning up empty file' in line:
            in_patch_block = False
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
    
print("Indentation fixed.")
