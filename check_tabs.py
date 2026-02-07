
import os

file_path = os.path.join('controllers', 'scraper_controller.py')
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    # Try absolute just in case but with forward slashes
    file_path = 'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()
    if '\t' in content:
        print("TABS DETECTED!")
        print(f"First tab at index: {content.index('\t')}")
        # Show line
        line_num = content[:content.index('\t')].count('\n') + 1
        print(f"Line number: {line_num}")
    else:
        print("No tabs found.")
