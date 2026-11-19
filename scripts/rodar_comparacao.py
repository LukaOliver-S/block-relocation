"""Compara heuristicas (RS-5, PM-3) com o A* nas instancias da disciplina.

Uso (de qualquer pasta):
    python scripts/rodar_comparacao.py                 # roda tudo e calcula metricas
    python scripts/rodar_comparacao.py --filtro W3_H4  # so instancias cujo nome contem W3_H4
    python scripts/rodar_comparacao.py --so-metricas   # recalcula metricas do CSV existente
Opcoes: --timeout S (padrao 60), --jobs J (execucoes em paralelo, padrao 4).

Saidas em resultados/:
    resultados_comparacao.csv  uma linha por instancia x metodo (bruto)
    metricas_comparacao.csv    + Z_ref, ref_tipo, gap
    resumo_por_classe.csv      medias por classe (arquivo) e metodo

Gap = (Z - Z_ref) / Z_ref, com Z_ref = Z* do A* quando ele termina no tempo
(ref_tipo = otimo); senao, o menor Z entre os metodos (melhor_conhecido).
Se Z_ref = 0: gap = 0 quando Z = 0, senao gap = Z (valor absoluto).
Atencao: RS-5 e PM-3 resolvem o BRP IRRESTRITO, entao Z < Z* (gap < 0) e possivel.
"""
import argparse, csv, re, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import mean

RAIZ = Path(__file__).resolve().parent.parent
EXE = RAIZ / "brp.exe"
PASTA = RAIZ / "instancias" / "brp_txt"
RES = RAIZ / "resultados"
METODOS = ["ASTAR", "RS-5", "PM-3"]
RE_Z = re.compile(r"used (\d+) relocations in ([0-9.eE+-]+) s")
RE_NOME = re.compile(r"(brp_W(\d+)_H(\d+)_N(\d+))_id(\d+)\.txt$")

CAMPOS_BRUTO = ["conjunto", "arquivo", "id", "W", "H", "N", "metodo",
                "reshuffles", "tempo_s", "status"]


def rodar(f, m, timeout):
    arquivo, W, H, N, ident = RE_NOME.search(f.name).groups()
    W, H, N, ident = int(W), int(H), int(N), int(ident)
    cmd = [str(EXE), "-i", str(f), "-m", m, "-maxHeight", "file"]
    if m == "ASTAR":
        cmd += ["-tl", str(timeout)]
    z = t = ""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout + 10)
        mt = RE_Z.search(r.stdout)
        if r.returncode == 0 and mt:
            z, t, st = int(mt.group(1)), float(mt.group(2)), "ok"
        elif r.returncode == 4:          # AStarTimeout (ver main.cpp)
            t, st = timeout, "timeout"
        else:
            st = f"erro({r.returncode})"
    except subprocess.TimeoutExpired:
        t, st = timeout, "timeout"
    linha = {"conjunto": "A" if W < 7 else "B", "arquivo": arquivo, "id": ident,
             "W": W, "H": H, "N": N, "metodo": m, "reshuffles": z,
             "tempo_s": t, "status": st}
    print(f"{f.name:28s} {m:6s} Z={z!s:>4} t={t!s:>8} {st}", flush=True)
    return linha


def executar(filtro, timeout, jobs):
    arqs = sorted((f for f in PASTA.glob("*.txt") if RE_NOME.search(f.name)
                   and filtro in f.name),
                  key=lambda f: (int(RE_NOME.search(f.name).group(4)), f.name))
    tarefas = [(f, m) for f in arqs for m in METODOS]
    print(f"{len(arqs)} instancias x {len(METODOS)} metodos = {len(tarefas)} execucoes")
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        linhas = list(ex.map(lambda a: rodar(*a, timeout), tarefas))
    linhas.sort(key=lambda l: (l["conjunto"], l["W"], l["H"], l["N"], l["id"],
                               METODOS.index(l["metodo"])))
    RES.mkdir(exist_ok=True)
    with open(RES / "resultados_comparacao.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, CAMPOS_BRUTO)
        w.writeheader()
        w.writerows(linhas)


def calcular_gap(z, zref):
    if zref == 0:
        return 0.0 if z == 0 else float(z)
    return (z - zref) / zref


def metricas():
    with open(RES / "resultados_comparacao.csv", newline="") as fh:
        linhas = list(csv.DictReader(fh))

    por_inst = {}
    for l in linhas:
        por_inst.setdefault((l["arquivo"], l["id"]), []).append(l)

    saida = []
    for (arq, ident), ls in por_inst.items():
        ok = {l["metodo"]: int(l["reshuffles"]) for l in ls if l["status"] == "ok"}
        if "ASTAR" in ok:
            zref, tipo = ok["ASTAR"], "otimo"
        elif ok:
            zref, tipo = min(ok.values()), "melhor_conhecido"
        else:
            zref, tipo = "", "sem_referencia"
        for l in ls:
            l = dict(l)
            l["Z_ref"], l["ref_tipo"] = zref, tipo
            if l["status"] == "ok" and zref != "":
                z = int(l["reshuffles"])
                l["gap"] = round(calcular_gap(z, zref), 6)
                l["gap_obs"] = "zref_zero" if zref == 0 else ""
            else:
                l["gap"], l["gap_obs"] = "", ""
            saida.append(l)

    with open(RES / "metricas_comparacao.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, CAMPOS_BRUTO + ["Z_ref", "ref_tipo", "gap", "gap_obs"])
        w.writeheader()
        w.writerows(saida)

    # resumo por classe (arquivo) e metodo
    grupos = {}
    for l in saida:
        grupos.setdefault((l["conjunto"], l["arquivo"], int(l["W"]), int(l["H"]),
                           int(l["N"]), l["metodo"]), []).append(l)
    resumo = []
    for (conj, arq, W, H, N, m), ls in sorted(
            grupos.items(), key=lambda kv: (kv[0][0], kv[0][2], kv[0][3], kv[0][4],
                                            METODOS.index(kv[0][5]))):
        oks = [l for l in ls if l["status"] == "ok"]
        gaps = [float(l["gap"]) for l in oks if l["gap"] != ""]
        resumo.append({
            "conjunto": conj, "arquivo": arq, "W": W, "H": H, "N": N, "metodo": m,
            "n_instancias": len(ls), "n_ok": len(oks),
            "n_timeout": sum(l["status"] == "timeout" for l in ls),
            "reshuffles_medio": round(mean(int(l["reshuffles"]) for l in oks), 3) if oks else "",
            "tempo_medio_s": round(mean(float(l["tempo_s"]) for l in oks), 4) if oks else "",
            "gap_medio": round(mean(gaps), 6) if gaps else "",
            "gap_max": round(max(gaps), 6) if gaps else "",
            "n_iguala_ref": sum(int(l["reshuffles"]) == l["Z_ref"] for l in oks
                                if l["Z_ref"] != ""),
            "n_ref_otimo": sum(l["ref_tipo"] == "otimo" for l in ls),
        })
    with open(RES / "resumo_por_classe.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, list(resumo[0].keys()))
        w.writeheader()
        w.writerows(resumo)
    print(f"metricas: {RES / 'metricas_comparacao.csv'}")
    print(f"resumo:   {RES / 'resumo_por_classe.csv'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--filtro", default="")
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--so-metricas", action="store_true")
    a = ap.parse_args()
    if not a.so_metricas:
        executar(a.filtro, a.timeout, a.jobs)
    metricas()
