import json

try:
    with open('C:/Temp/events.json', 'r', encoding='utf-8') as f:
        d = json.load(f)
    evs = d.get('events', [])
    print(f'Total eventos: {len(evs)}')
    print()
    for e in evs[-40:]: # Last 40 events
        print(f"[{e.get('timestamp', '')[:19]}] [{e.get('type', '')}] [{e.get('source', '')}] {e.get('message', '')}")
except Exception as e:
    print(f"Error reading events: {e}")
