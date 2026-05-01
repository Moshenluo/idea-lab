import requests, json, time

r = requests.post('http://localhost:5000/api/run', json={'query': 'transformer attention mechanism'}, timeout=5)
job = r.json()['job_id']
print('Job:', job)

for i in range(20):
    time.sleep(3)
    s = requests.get(f'http://localhost:5000/api/status/{job}', timeout=5).json()
    if s['status'] == 'done':
        papers = s['result']['papers']
        for p in papers[:3]:
            yr = p.get('year', '?')
            title = p.get('title', '')[:50]
            url = p.get('url', 'N/A')
            print(f"  [{yr}] {title}")
            print(f"    URL: {url}")
        break
    elif s['status'] == 'error':
        print('Error:', s['error'])
        break
    else:
        print(f"  {s['step']} ({s['progress']}%)")
