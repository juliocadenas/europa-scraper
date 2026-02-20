
import os

file_path = os.path.join('controllers', 'scraper_controller.py')
# Fallback absolute path just in case
if not os.path.exists(file_path):
    file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

print(f"Fixing indentation in: {file_path}")

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Expand tabs to 4 spaces (standard python) or 2?
    # If the file uses 2 spaces, tabs are usually 4 or 8 spaces visual, but python treats tab as 8 spaces for indentation logic unless consistently used.
    # Safe bet: Replace tab with 4 spaces if it looks like standard indentation, OR just replace all tabs with 4 spaces.
    # BUT if the file uses 2 spaces, maybe I should replace tab with 2 spaces?
    # No, usually tab = 4 spaces.
    
    if '\t' in content:
        print("Tabs found! Replacing with 4 spaces.")
        new_content = content.replace('\t', '    ')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Fixed tabs.")
    else:
        print("No tabs found.")
        
except Exception as e:
    print(f"Error: {e}")
