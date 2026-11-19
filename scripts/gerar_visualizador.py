"""Gera resultados/visualizador_solucoes.html: passo a passo da solucao de cada
metodo em cada instancia (HTML unico, autocontido, abre direto no navegador).

Uso: python scripts/gerar_visualizador.py [--conjunto A|B|AB] [--timeout S] [--jobs J]

Para cada instancia x metodo roda o brp.exe com -trace (mesmos parametros de
scripts/rodar_comparacao.py) e le o passos.csv gerado. Se existir
resultados/metricas_comparacao.csv, o Z_ref e o gap de cada metodo entram no HTML.
"""
import argparse, csv, json, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from rodar_comparacao import (EXE, PASTA, RES, METODOS, VARIANTE, RE_NOME, RE_Z,
                              conjunto_de)

RAIZ = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).with_name("visualizador_template.html")
SAIDA = RES / "visualizador_solucoes.html"
NOMES = {"ASTAR": "A*", "DFBB": "B&B", "MM": "Min-Max", "RS-5": "RS-5", "PM-3": "PM-3"}


def ler_instancia(f):
    linhas = f.read_text().split("\n")
    W, H, N = map(int, linhas[0].split()[:3])
    pilhas = []
    for l in linhas[1:1 + W]:
        v = list(map(int, l.split()))
        pilhas.append(v[1:1 + v[0]])           # base -> topo
    return W, H, N, pilhas


def rodar(f, m, timeout, tmp):
    trace = Path(tmp) / f"{f.stem}__{m}.txt"
    cmd = [str(EXE), "-i", str(f), "-m", m, "-maxHeight", "file", "-trace", str(trace)]
    if m == "ASTAR":
        cmd += ["-tl", str(timeout)]
    elif m == "DFBB":
        cmd += ["-ub", "LA-1", "-lb", "3", "-tl", str(timeout)]
    res = {"status": "erro", "Z": None, "tempo": None, "passos": []}
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)
    except subprocess.TimeoutExpired:
        res["status"] = "timeout"
        return res
    mt = RE_Z.search(r.stdout)
    if r.returncode == 4:
        res["status"] = "timeout"
    elif r.returncode == 0 and mt:
        res["status"] = "timeout" if "Time limit reached" in r.stdout else "ok"
        res["Z"], res["tempo"] = int(mt.group(1)), float(mt.group(2))
        with open(trace.with_suffix(".csv"), newline="") as fh:
            for p in csv.DictReader(fh):
                res["passos"].append([
                    "R" if p["tipo"] == "relocacao" else "S",     # relocacao / saida
                    int(p["container"]), int(p["origem"]),
                    int(p["destino"]) if p["destino"] else 0,
                    "V" if p["classe"] == "voluntaria" else "",
                ])
    else:
        res["status"] = f"erro({r.returncode})"
    return res


def metricas_existentes():
    p = RES / "metricas_comparacao.csv"
    if not p.exists():
        return {}
    with open(p, newline="") as fh:
        return {(l["arquivo"], int(l["id"]), l["metodo"]): l for l in csv.DictReader(fh)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--conjunto", default="A", choices=["A", "B", "AB"])
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()

    arqs = sorted((f for f in PASTA.glob("*.txt") if RE_NOME.search(f.name)
                   and conjunto_de(f.name) in a.conjunto),
                  key=lambda f: (int(RE_NOME.search(f.name).group(4)),
                                 int(RE_NOME.search(f.name).group(2)),
                                 int(RE_NOME.search(f.name).group(5))))
    met = metricas_existentes()
    tarefas = [(f, m) for f in arqs for m in METODOS]
    print(f"{len(arqs)} instancias x {len(METODOS)} metodos")
    with tempfile.TemporaryDirectory() as tmp, ThreadPoolExecutor(a.jobs) as ex:
        resultados = list(ex.map(lambda t: rodar(*t, a.timeout, tmp), tarefas))

    instancias, k = [], 0
    for f in arqs:
        arquivo, _, _, _, ident = RE_NOME.search(f.name).groups()
        W, H, N, pilhas = ler_instancia(f)
        sol = {}
        for m in METODOS:
            r = resultados[k]; k += 1
            l = met.get((arquivo, int(ident), m))
            if l:
                r["Zref"] = int(l["Z_ref"]) if l["Z_ref"] != "" else None
                r["gap"] = float(l["gap"]) if l["gap"] != "" else None
            sol[m] = r
        instancias.append({"arquivo": arquivo, "id": int(ident), "conjunto": conjunto_de(f.name),
                           "W": W, "H": H, "N": N, "pilhas": pilhas, "sol": sol})

    dados = {"metodos": [{"cod": m, "nome": NOMES.get(m, m), "variante": VARIANTE[m]}
                         for m in METODOS],
             "instancias": instancias}
    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "/*__DADOS__*/null", json.dumps(dados, separators=(",", ":")))
    SAIDA.write_text(html, encoding="utf-8")
    print("->", SAIDA)


if __name__ == "__main__":
    main()
