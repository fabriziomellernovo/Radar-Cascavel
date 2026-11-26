"""Audita a lista de presença da sessão plenária para uma base identificada do SAPL."""

import argparse
import json
from datetime import date
from pathlib import Path

from acesso import BASE
from coleta_escopo import collect, out, require

ENDPOINT = "sessao/sessaoplenariapresenca"
CAMPOS = ("id", "sessao_plenaria", "parlamentar")
REFERENCIAS = {1343: 20, 1344: 21}


def ler(nome):
    base = json.loads((out / f"{nome}.json").read_text(encoding="utf-8"))
    linhas = base["rows"]
    require(isinstance(linhas, list) and base["total"] == len(linhas),
            f"Contagem incompatível em {nome}")
    ids = [linha["id"] for linha in linhas]
    require(all(type(i) is int for i in ids) and len(set(ids)) == len(ids),
            f"Identificadores inválidos em {nome}")
    return base


def conferir_lista(sid, pessoas):
    base = ler(f"presenca_{sid}")
    origem = f"{BASE}/api/{ENDPOINT}/?sessao_plenaria={sid}"
    require(base["source"] == origem, f"Fonte divergente na sessão {sid}")
    vistos = set()
    for linha in base["rows"]:
        pessoa = linha["parlamentar"]
        require(set(linha) == set(CAMPOS) and linha["sessao_plenaria"] == sid
                and type(pessoa) is int and pessoa in pessoas and pessoa not in vistos,
                f"Presença inválida ou duplicada na sessão {sid}")
        vistos.add(pessoa)
    if sid in REFERENCIAS:
        require(len(vistos) == REFERENCIAS[sid], f"Revisar a sessão de referência {sid}")
    return base["rows"]


def cobertura(sessoes, pessoas, corte, base_id):
    resumo = {"execucao_base": base_id, "data_de_corte": corte.isoformat(),
              "cadastradas": len(sessoes), "elegiveis": 0, "consultadas": 0,
              "com_lista": 0, "sem_registro_no_sapl": 0, "pendentes": 0, "sessoes": []}
    registros = set()
    for sessao in sessoes:
        sid = sessao["id"]
        dia = date.fromisoformat(sessao["data_inicio"])
        require(type(sessao["iniciada"]) is bool and type(sessao["finalizada"]) is bool,
                f"Situação indefinida na sessão {sid}")
        linha = {"id": sid, "data": dia.isoformat(), "fonte": f"{BASE}/sessao/{sid}/resumo"}
        if dia > corte or not (sessao["iniciada"] and sessao["finalizada"]):
            linha["situacao"] = "fora_do_recorte"
        else:
            resumo["elegiveis"] += 1
            if (out / f"presenca_{sid}.json").is_file():
                lista = conferir_lista(sid, pessoas)
                ids = {r["id"] for r in lista}
                require(registros.isdisjoint(ids), "Registro de presença repetido entre sessões")
                registros.update(ids)
                linha["situacao"] = "com_lista" if lista else "sem_registro_no_sapl"
                if lista:
                    linha["registros"] = len(lista)
                resumo["consultadas"] += 1
            else:
                linha["situacao"] = "pendentes"
            resumo[linha["situacao"]] += 1
        resumo["sessoes"].append(linha)
    resumo["cobertura_integral_de_consulta"] = resumo["elegiveis"] > 0 and resumo["pendentes"] == 0
    return resumo


def executar(corte, base_id, limite):
    sessoes = ler("sessoes")["rows"]
    pessoas = {p["id"] for p in ler("parlamentares")["rows"]}
    rel = json.loads(Path("scope-report.json").read_text(encoding="utf-8"))["sessoes"]
    leg = rel["params"]["legislatura"]
    require(rel["sample_matches"] is True and len(sessoes) == rel["total_entries"]
            and all(s["legislatura"] == leg for s in sessoes), "Base de sessões divergente")
    require(REFERENCIAS.keys() <= {s["id"] for s in sessoes}, "Sessões de referência ausentes")
    for sid in REFERENCIAS:
        conferir_lista(sid, pessoas)

    def registrar():
        resumo = cobertura(sessoes, pessoas, corte, base_id)
        tmp = Path("cobertura.tmp")
        tmp.write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace("cobertura.json")
        print(f"Consultadas {resumo['consultadas']}/{resumo['elegiveis']}; "
              f"com lista {resumo['com_lista']}; sem registro {resumo['sem_registro_no_sapl']}; "
              f"pendentes {resumo['pendentes']}", flush=True)
        return resumo

    resumo = registrar()
    pendentes = sorted((s for s in resumo["sessoes"] if s["situacao"] == "pendentes"),
                       key=lambda s: (s["data"], s["id"]), reverse=True)
    for sessao in pendentes[:limite]:
        sid = sessao["id"]
        collect(f"presenca_{sid}", ENDPOINT, {"sessao_plenaria": sid},
                lambda r: r["sessao_plenaria"] == sid and type(r["parlamentar"]) is int
                and r["parlamentar"] in pessoas, CAMPOS, allow_empty=True, distinct="parlamentar")
        try:
            resumo = registrar()
        except (ValueError, RuntimeError, KeyError, TypeError):
            (out / f"presenca_{sid}.json").unlink()
            raise
    if limite is None:
        require(resumo["cobertura_integral_de_consulta"], "Consulta de presenças incompleta")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corte", type=date.fromisoformat, required=True)
    parser.add_argument("--base", required=True, type=int)
    parser.add_argument("--limite", type=int)
    args = parser.parse_args()
    if args.limite is not None and args.limite < 0:
        parser.error("O limite deve ser positivo ou zero.")
    executar(args.corte, args.base, args.limite)
