"""Verifica filtros de escopo sem baixar o acervo histórico.
Nenhuma informação pessoal ou conteúdo bruto é gravado."""
import json
from urllib.parse import urlencode
from acesso import get, BASE, AccessStopped

report={}
def call(path,params):
    return get(BASE+"/api/"+path+"/?"+urlencode({"format":"json","page_size":2,**params}))
def probe(name,path,params,valid):
    d=call(path,params)
    p=d["pagination"]
    rows=d["results"]
    ok=bool(rows) and all(valid(x) for x in rows)
    report[name]={"params":params,"total_entries":p["total_entries"],"sample_size":len(rows),"sample_matches":ok,"page":p["page"]}
    print(name,json.dumps(report[name],ensure_ascii=False),flush=True)
    return ok
def main():
    ref=get(BASE+"/api/sessao/sessaoplenaria/1343/?format=json")
    assert ref["id"]==1343 and ref["data_inicio"]=="2026-09-01"
    legislature=ref["legislatura"]
    print("Legislatura de referência:",legislature,flush=True)
    probe("sessoes","sessao/sessaoplenaria",{"legislatura":legislature},lambda x:x["legislatura"]==legislature and x["data_inicio"][:4] in ("2025","2026","2027","2028"))
    probe("mandatos","parlamentares/mandato",{"legislatura":legislature},lambda x:x["legislatura"]==legislature)
    probe("materias_2025","materia/materialegislativa",{"ano":2025},lambda x:x["ano"]==2025)
    probe("materias_2026","materia/materialegislativa",{"ano":2026},lambda x:x["ano"]==2026)
    probe("presenca_sessao_1343","sessao/sessaoplenariapresenca",{"sessao_plenaria":1343},lambda x:x["sessao_plenaria"]==1343)
    probe("votos_2026","sessao/votoparlamentar",{"data_hora__year":2026},lambda x:str(x["data_hora"]).startswith("2026"))
    probe("resultados_2026","sessao/registrovotacao",{"data_hora__year":2026},lambda x:str(x["data_hora"]).startswith("2026"))
    # O filtro de presença deve reproduzir a contagem já auditada.
    assert report["presenca_sessao_1343"]["total_entries"]==20
    assert all(v["sample_matches"] for v in report.values()),"Filtro ignorado ou amostra vazia: não utilizar para coleta"
if __name__=="__main__":
    try: main()
    finally:
        with open("scope-report.json","w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
