
file_path = r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start = 1040
end = 1060
print(f"Inspecting lines {start} to {end} (0-indexed)")

for i in range(start, end):
    if i < len(lines):
        print(f"{i}: {repr(lines[i])}")
