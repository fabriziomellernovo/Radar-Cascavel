import json
from acesso import get, AccessStopped
base="https://sapl.cascavel.pr.leg.br/api/"
paths=["parlamentares/parlamentar","parlamentares/mandato","sessao/sessaoplenaria","sessao/sessaoplenariapresenca","materia/materialegislativa","materia/autoria","base/autor","sessao/votoparlamentar","sessao/registrovotacao"]
report={}
for path in paths:
    try:
        d=get(base+path+"/?format=json&page_size=2")
        rows=d if isinstance(d,list) else d.get("results",[]) if isinstance(d,dict) else []
        entry={"format":type(d).__name__,"keys":list(d) if isinstance(d,dict) else [],"received":len(rows),"count":d.get("count") if isinstance(d,dict) else None,"fields":{k:type(v).__name__ for k,v in rows[0].items()} if rows and isinstance(rows[0],dict) else {}}
        report[path]=entry
    except AccessStopped as e:
        report[path]={"error":str(e)}
        print(str(e),flush=True)
        break
    except Exception as e: report[path]={"error":str(e)}
    print(path,json.dumps(report[path],ensure_ascii=False),flush=True)
with open("schema-report.json","w") as f: json.dump(report,f,ensure_ascii=False,indent=2)
if any("error" in x or not x.get("fields") for x in report.values()): raise SystemExit("Diagnóstico incompleto")
