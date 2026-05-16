with open('gui/scraper_gui.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '                    csv_total = data.get("csv_total", 0)\n'
new = '                    csv_total = data.get("csv_total", 0) if is_running else 0\n'

if old in content:
    content = content.replace(old, new, 1)
    with open('gui/scraper_gui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("OK - fix applied")
else:
    print("ERROR - pattern not found")
