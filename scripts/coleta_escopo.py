"""Primeira base de escopo limitado. Não publica o site."""
import json, pathlib
from urllib.parse import urlencode, urlsplit, urlunsplit
from acesso import BASE, get
out=pathlib.Path("staging")
out.mkdir(exist_ok=True)
def require(ok,msg):
    if not ok: raise RuntimeError(msg)
def collect(name,path,params,valid,fields,expected=None):
    url=BASE+"/api/"+path+"/?"+urlencode({"format":"json","page_size":100,**params})
    rows=[]; ids=set(); total=None; page=1
    while url:
        d=get(url); p=d["pagination"]; batch=d["results"]
        if total is None:
            total=p["total_entries"]
            require(isinstance(total,int) and total>0,"Base vazia ou total inválido")
            require(expected is None or total==expected,"Total divergente do diagnóstico: "+name)
        require(p["total_entries"]==total and p["page"]==page,"Paginação ou total inconsistente")
        require(p["start_index"]==len(rows)+1 and p["end_index"]==len(rows)+len(batch),"Intervalo inconsistente")
        for row in batch:
            require(valid(row),"Registro fora do escopo: "+name)
            require(isinstance(row["id"],int) and row["id"] not in ids,"ID inválido ou repetido")
            ids.add(row["id"])
            rows.append({k:row[k] for k in fields})
        next_url=p["links"]["next"]
        require(bool(next_url)==(len(rows)<total),"Fim de paginação inconsistente")
        require(len(rows)<=total,"Excesso de registros")
        if next_url:
            u=urlsplit(next_url)
            require(u.netloc=="sapl.cascavel.pr.leg.br" and u.path=="/api/"+path+"/","Link fora da fonte")
            url=urlunsplit(("https",u.netloc,u.path,u.query,""))
        else: url=None
        page+=1
        print(name,len(rows),"/",total,flush=True)
    require(len(rows)==total,"Base incompleta")
    tmp=out/(name+".tmp")
    tmp.write_text(json.dumps({"source":BASE+"/api/"+path+"/?"+urlencode(params),"total":total,"rows":rows},ensure_ascii=False),encoding="utf-8")
    tmp.replace(out/(name+".json"))
    return rows
def main():
    report=json.loads(pathlib.Path("scope-report.json").read_text())
    for k in ("sessoes","mandatos","presenca_sessao_1343"):
        require(report.get(k,{}).get("sample_matches") is True,"Filtro não demonstrado: "+k)
    leg=report["sessoes"]["params"]["legislatura"]
    people=collect("parlamentares","parlamentares/parlamentar",{},lambda x:bool(x["nome_parlamentar"]),["id","nome_parlamentar","ativo"])
    ids={x["id"] for x in people}
    sessions=collect("sessoes","sessao/sessaoplenaria",{"legislatura":leg},lambda x:x["legislatura"]==leg and x["data_inicio"][:4] in ("2025","2026","2027","2028"),["id","data_inicio","numero","tipo","legislatura","iniciada","finalizada"],report["sessoes"]["total_entries"])
    mandates=collect("mandatos","parlamentares/mandato",{"legislatura":leg},lambda x:x["legislatura"]==leg and x["parlamentar"] in ids,["id","parlamentar","legislatura","data_inicio_mandato","data_fim_mandato","titular"],report["mandatos"]["total_entries"])
    require({1343,1344}<={x["id"] for x in sessions},"Sessões auditadas ausentes")
    for sid,n in [(1343,20),(1344,21)]:
        p=collect("presenca_"+str(sid),"sessao/sessaoplenariapresenca",{"sessao_plenaria":sid},lambda x:x["sessao_plenaria"]==sid and x["parlamentar"] in ids,["id","sessao_plenaria","parlamentar"],n)
        require(len({x["parlamentar"] for x in p})==n,"Presença duplicada")
    print("Base inicial de escopo validada. Publicação ainda bloqueada.",flush=True)
if __name__=="__main__": main()
