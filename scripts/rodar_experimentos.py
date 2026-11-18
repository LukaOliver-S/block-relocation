import csv, re, subprocess
from pathlib import Path
from verificar import verificar, ler_movimentos

RAIZ = Path(__file__).resolve().parent.parent   
EXE = RAIZ / "brp.exe"
METODOS = ["RS-5", "PM-3"]         
TIMEOUT = 60                         
MAX_N = 40                          
PASTAS = {"A": RAIZ / "instancias" / "A",
          "B": RAIZ / "instancias" / "caserta"}
SOLUCOES = RAIZ / "resultados" / "solucoes"
RE = re.compile(r"used (\d+) relocations in ([0-9.]+) s")


def cabecalho(p):
    return list(map(int, p.open().readline().split()[:3]))   # W, H, N


linhas = []
for conj, pasta in PASTAS.items():
    for f in sorted(pasta.glob("*.txt")):
        W, H, N = cabecalho(f)
        if N > MAX_N:
            continue
        for m in METODOS:
            sol = SOLUCOES / m / f"{conj}_{f.name}"
            sol.parent.mkdir(parents=True, exist_ok=True)
            cmd = [str(EXE), "-i", str(f), "-m", m, "-maxHeight", "file",
                   "-sf", str(sol)]
            v_irr = v_res = z_conf = ""
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
                mt = RE.search(r.stdout)
                if r.returncode == 0 and mt:
                    z, t, st = int(mt.group(1)), float(mt.group(2)), "ok"
                    movs = ler_movimentos(sol)
                    v_irr = verificar(f, movs, restrito=False)[0]
                    v_res = verificar(f, movs, restrito=True)[0]
                    z_conf = (len(movs) == z)
                else:
                    z, t, st = "", "", f"erro({r.returncode})"
            except subprocess.TimeoutExpired:
                z, t, st = "", TIMEOUT, "timeout"
            linhas.append([conj, f.name, W, H, N, m, z, t, st, v_irr, v_res, z_conf])
            print(conj, f.name, m, z, t, st, v_irr, v_res, z_conf, flush=True)

(RAIZ / "resultados").mkdir(exist_ok=True)
with open(RAIZ / "resultados" / "resultados_irrestrito.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["conjunto", "instancia", "W", "H", "N", "metodo", "relocacoes",
                "tempo_s", "status", "valida_irrestrita", "valida_restrita",
                "z_confere"])
    w.writerows(linhas)