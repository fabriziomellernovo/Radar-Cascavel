import json, urllib.request, urllib.parse, time, pathlib, datetime, html, re, os
BASE="https://sapl.cascavel.pr.leg.br"
def require(ok,msg):
    if not ok: raise RuntimeError(msg)
def get(url):
    require(urllib.parse.urlsplit(url).netloc=="sapl.cascavel.pr.leg.br","Host inesperado")
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"Radar-Cascavel/1.0 (public civic data)"}),timeout=40) as f:
                require(urllib.parse.urlsplit(f.geturl()).netloc=="sapl.cascavel.pr.leg.br","Redirecionamento inesperado")
                data=json.load(f)
            time.sleep(.2)
            return data
        except Exception:
            if i==2: raise
            time.sleep(2**i)
def collect(path):
    url=BASE+"/api/"+path+"/?format=json"
    rows=[]; seen=set(); count=None
    while url:
        url=urllib.parse.urljoin(BASE,url).replace("http://","https://",1)
        require(url not in seen and len(seen)<5000,"Paginação inválida")
        seen.add(url); d=get(url)
        require(isinstance(d,dict) and isinstance(d.get("results"),list) and isinstance(d.get("count"),int),"Formato inesperado: "+path)
        if count is None: count=d["count"]
        require(count==d["count"],"Contagem mudou durante coleta")
        rows+=d["results"]; url=d.get("next")
        require(len(rows)<=count,"Excesso de registros")
    require(len(rows)==count and count>0,"Coleta incompleta: "+path)
    require(all(isinstance(x.get("id"),int) for x in rows) and len({x["id"] for x in rows})==count,"IDs inválidos ou duplicados")
    print(path,count,flush=True)
    return rows
def ref(x,k):
    v=x[k]
    require(isinstance(v,int),"Referência inválida: "+k)
    return v
def main():
    paths={"people":"parlamentares/parlamentar","sessions":"sessao/sessaoplenaria","attendance":"sessao/sessaoplenariapresenca","matters":"materia/materialegislativa","authors":"materia/autoria","author_ids":"base/autor","votes":"sessao/votoparlamentar","rollcalls":"sessao/registrovotacao"}
    data={k:collect(v) for k,v in paths.items()}
    ids={k:{x["id"] for x in v} for k,v in data.items()}
    for k,links in {"attendance":{"sessao_plenaria":"sessions","parlamentar":"people"},"authors":{"materia":"matters","autor":"author_ids"},"votes":{"votacao":"rollcalls","parlamentar":"people"}}.items():
        for x in data[k]:
            for field,target in links.items(): require(ref(x,field) in ids[target],"Referência órfã "+k)
    sessions={x["id"]:x for x in data["sessions"] if str(x["data_inicio"])[:4] in ("2025","2026","2027","2028") and x.get("iniciada") is True and x.get("finalizada") is True}
    require({1343,1344}<=sessions.keys(),"Sessões de referência ausentes")
    attendance=[x for x in data["attendance"] if x["sessao_plenaria"] in sessions]
    pairs={(x["sessao_plenaria"],x["parlamentar"]) for x in attendance}
    require(len(pairs)==len(attendance),"Presença duplicada")
    require(sum(s==1343 for s,p in pairs)==20 and sum(s==1344 for s,p in pairs)==21,"Divergência com referência auditada")
    require(all(any(s==i for s,p in pairs) for i in sessions),"Sessão encerrada sem presença")
    counts={k:len(v) for k,v in data.items()}
    baseline=pathlib.Path("last-good.json")
    if baseline.exists():
        old=json.loads(baseline.read_text())
        for k,n in old.items(): require(counts[k]>=n and counts[k]<=max(n+100, int(n*1.3)),"Variação anormal: "+k)
    # Do not publish unvalidated mappings. First run generates a diagnostic only.
    pathlib.Path("candidate-counts.json").write_text(json.dumps(counts,indent=2))
    require(os.environ.get("RADAR_SCHEMA_APPROVED")=="yes","Primeira publicação bloqueada: validar mapeamento de autoria, votos, ocorrências e busca territorial com registros oficiais")
    # Explicitly fail closed until complete presentation and independent reconciliation are implemented.
    raise RuntimeError("Publicação bloqueada: reconciliação integral e renderização ainda não implementadas")
if __name__=="__main__": main()
