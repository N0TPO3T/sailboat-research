import json, urllib.request, concurrent.futures
from pathlib import Path
DOIS=['10.3390/s20061550','10.1109/IROS.2009.5354175','10.1016/j.automatica.2016.08.013','10.1002/rob.22512','10.1002/rob.21900','10.1109/IROS55552.2023.10341787','10.1109/JOE.2013.2247276','10.1016/j.apor.2026.105246']
def fetch(doi):
    try:
        m=json.load(urllib.request.urlopen('https://api.crossref.org/works/'+doi,timeout=20))['message']
        return {'doi':doi,**{k:m.get(k) for k in ['title','author','container-title','volume','issue','page','published']}}
    except Exception as e:
        return {'doi':doi,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(4) as pool:
    results=list(pool.map(fetch,DOIS))
Path(__file__).with_name('REFERENCE_METADATA_CHECK.json').write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps([{k:v for k,v in r.items() if k!='author'} for r in results],indent=2))
