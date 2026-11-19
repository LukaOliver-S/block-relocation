"""Roda os metodos do brp sobre os conjuntos de instancias e gera:
  - resultados/resultados_irrestrito.csv  (uma linha por instancia x metodo)
  - resultados/solucoes/<metodo>/<conjunto>_<instancia>.txt   (formato -sf)
  - resultados/passos/<metodo>/passos_csv/<instancia>_passos.csv  (passo a passo)
  - resultados/passos/<metodo>/passos_txt/<instancia>_passos.txt  (idem, legivel)
  - resultados/passos/<metodo>/moves/<instancia>_moves.txt        ([[origem, destino], ...])

Uso (de qualquer pasta):
  python scripts/rodar_experimentos.py
  python scripts/rodar_experimentos.py --conjuntos brp_txt --metodos RS-5,PM-3,ASTAR
Opcoes: --metodos, --conjuntos, --timeout (s por execucao), --tl-astar (s),
        --tl-bb (s, para BB/DFBB/DFBB-L), --sem-compilar (usa o brp.exe que
        ja existe), --csv (arquivo de saida).
Padrao de --metodos: MM, RS-5, PM-3, ASTAR, BB.
Em BB/DFBB que estouram o limite, status = timeout mas relocacoes traz a
melhor solucao achada (nao provada otima).
O CSV de resultados e gravado linha a linha durante a execucao.
O brp.exe e recompilado automaticamente se algum .cpp/.h for mais novo.
"""
import argparse
import csv
import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXE = RAIZ / "brp.exe"
# MM, ASTAR: restritos. RS-5, PM-3: irrestritos. BB: exato no IRRESTRITO
# (serve de comparacao; seu valor e um limite inferior do otimo restrito).
METODOS = ["MM", "RS-5", "PM-3", "ASTAR", "BB"]
TIMEOUT = 60        # segundos por execucao (o processo e morto ao estourar)
# Limite interno (-tl) do A*. Ele guarda todos os estados em memoria
# (~0,5 GB por segundo nas instancias grandes), entao nao suba demais.
TL_ASTAR = 20
# Limite interno (-tl) dos exatos BB, DFBB e DFBB-L. Fica abaixo do TIMEOUT
# para eles terminarem sozinhos e devolverem a melhor solucao achada.
TL_BB = 50
EXATOS_BB = ("BB", "DFBB", "DFBB-L")
# conjunto -> (pasta, MAX_N ou None). MAX_N descarta instancias grandes.
CONJUNTOS = {
    "A": (RAIZ / "instancias" / "A", 40),
    "B": (RAIZ / "instancias" / "caserta", 40),
    "brp_txt": (RAIZ / "instancias" / "brp_txt", None),
}
CSV_PADRAO = RAIZ / "resultados" / "resultados_irrestrito.csv"
SOLUCOES = RAIZ / "resultados" / "solucoes"   # arquivos -sf
PASSOS = RAIZ / "resultados" / "passos"       # passos.csv, passos.txt, moves.txt
RE = re.compile(r"used (\d+) relocations in ([0-9.]+) s")


def cabecalho(p):
    return list(map(int, p.open().readline().split()[:3]))   # W, H, N


def compilar():
    """Recompila o brp.exe se nao existir ou se algum fonte for mais novo."""
    fontes = sorted((RAIZ / "src").glob("*.cpp"))
    todos = fontes + list((RAIZ / "include").glob("*.h"))
    if EXE.exists() and EXE.stat().st_mtime >= max(f.stat().st_mtime for f in todos):
        return
    print(">> compilando brp.exe ...", flush=True)
    # Caminhos RELATIVOS e cwd = raiz: o ld do MinGW falha ("Illegal byte
    # sequence") quando recebe caminho absoluto com acento (Otimização-BRP).
    cmd = ["g++", "-std=c++14", "-O3", "-static", "-Wall", "-pedantic",
           "-Wno-sign-compare", "-Wno-unused", "-I", "include"]
    cmd += [f"src/{f.name}" for f in fontes] + ["-o", EXE.name]
    r = subprocess.run(cmd, cwd=RAIZ)
    if r.returncode != 0:
        raise SystemExit("Erro de compilacao (veja as mensagens acima). Se o "
                         "brp.exe ja estiver atualizado, use --sem-compilar.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metodos", default=",".join(METODOS))
    ap.add_argument("--conjuntos", default=",".join(CONJUNTOS))
    ap.add_argument("--timeout", type=int, default=TIMEOUT)
    ap.add_argument("--tl-astar", type=int, default=TL_ASTAR)
    ap.add_argument("--tl-bb", type=int, default=TL_BB,
                    help="limite (s) de BB, DFBB e DFBB-L (padrao: %(default)s)")
    ap.add_argument("--sem-compilar", action="store_true",
                    help="usa o brp.exe existente, sem recompilar")
    ap.add_argument("--csv", default=str(CSV_PADRAO),
                    help="arquivo CSV de resultados (padrao: %(default)s)")
    a = ap.parse_args()
    metodos = [m for m in a.metodos.split(",") if m]
    conjuntos = [c for c in a.conjuntos.split(",") if c]
    for c in conjuntos:
        if c not in CONJUNTOS:
            ap.error(f"conjunto desconhecido: {c} (validos: {', '.join(CONJUNTOS)})")

    if not a.sem_compilar:
        compilar()
    elif not EXE.exists():
        raise SystemExit("brp.exe nao existe; rode sem --sem-compilar.")
    # O CSV e gravado linha a linha (com flush): da para acompanhar durante a
    # execucao e nao se perde nada se ela for interrompida.
    saida = Path(a.csv)
    saida.parent.mkdir(parents=True, exist_ok=True)
    fh = open(saida, "w", newline="")
    w = csv.writer(fh)
    w.writerow(["conjunto", "instancia", "W", "H", "N", "metodo",
                "relocacoes", "tempo_s", "status", "valida_irrestrita",
                "valida_restrita", "z_confere", "passos_csv"])
    fh.flush()
    for conj in conjuntos:
        pasta, max_n = CONJUNTOS[conj]
        for f in sorted(pasta.glob("*.txt")):
            W, H, N = cabecalho(f)
            if max_n is not None and N > max_n:
                continue
            for m in metodos:
                sol = SOLUCOES / m / f"{conj}_{f.name}"
                sol.parent.mkdir(parents=True, exist_ok=True)
                passos = PASSOS / m / "passos_csv" / f"{f.stem}_passos.csv"
                for velho in (passos,                   # nada de arquivo velho
                              PASSOS / m / "passos_txt" / f"{f.stem}_passos.txt",
                              PASSOS / m / "moves" / f"{f.stem}_moves.txt"):
                    velho.unlink(missing_ok=True)
                cmd = [str(EXE), "-i", str(f), "-m", m, "-maxHeight", "file",
                       "-sf", str(sol), "-out", str(PASSOS)]
                if m == "ASTAR":
                    cmd += ["-tl", str(a.tl_astar)]
                elif m in EXATOS_BB:
                    cmd += ["-tl", str(a.tl_bb)]
                v_irr = v_res = z_conf = ""
                try:
                    r = subprocess.run(cmd, capture_output=True, text=True,
                                       timeout=a.timeout)
                    mt = RE.search(r.stdout)
                    if r.returncode == 0 and mt:
                        z, t, st = int(mt.group(1)), float(mt.group(2)), "ok"
                        # BB/DFBB estouram o limite devolvendo a MELHOR solucao
                        # achada (sem prova de otimo): marca como timeout.
                        if "time limit reached" in r.stdout.lower():
                            st = "timeout"
                    elif r.returncode == 4:             # A*: limite de tempo
                        z, t, st = "", a.tl_astar, "timeout"
                    else:
                        z, t, st = "", "", f"erro({r.returncode})"
                except subprocess.TimeoutExpired:
                    z, t, st = "", a.timeout, "timeout"
                if z == "":                     # sem solucao: so a linha da instancia
                    sol.unlink(missing_ok=True)
                ref = str(passos.relative_to(RAIZ)) if passos.exists() else ""
                w.writerow([conj, f.name, W, H, N, m, z, t, st,
                            v_irr, v_res, z_conf, ref])
                fh.flush()
                print(conj, f.name, m, z, t, st, ref, flush=True)

    fh.close()
    print(f">> resultados em {saida}", flush=True)


if __name__ == "__main__":
    main()
