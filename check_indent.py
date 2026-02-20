
with open(r'c:/Users/julio/Documents/DOCUPLAY/Proyecto/Python/EUROPA/V3.1-LINUX/controllers/scraper_controller.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
start = 1290
end = 1360
for i, line in enumerate(lines[start:end]):
    print(f"{start+i}: {repr(line)}")
