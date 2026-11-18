"""
Gerador de instâncias do Container Relocation Problem (CRP).

(A) Conjunto pequeno: W in 3..5, H in 4..5, N <= 20  (ótimos virão do A*)
(B) Literatura: Caserta, Voß & Sniedovich (2011) -> formato CVS:
    W (stacks) x T (tiers), altura máxima H = T + 2, N = W * T,
    prioridades distintas 1..N, baías inicialmente cheias até T.

Representação: baía = lista de W pilhas; cada pilha é lista bottom->top
com a prioridade (1 = sai primeiro).

Uso:
    python gerar_instancias.py            # gera tudo em ./instancias
"""
import json
import random
from pathlib import Path


# ---------------------------------------------------------------- geração
def gerar_instancia(W, H, N, seed, altura_inicial=None):
    """Distribui N containers (prioridades distintas 1..N) em W pilhas.

    altura_inicial: se informado, cada pilha recebe no máximo esse número
    de containers (estilo CVS: T). Caso contrário, o limite é H.
    """
    lim = altura_inicial if altura_inicial is not None else H
    assert N <= W * lim, "N não cabe na baía"
    rng = random.Random(seed)
    prioridades = list(range(1, N + 1))
    rng.shuffle(prioridades)

    pilhas = [[] for _ in range(W)]
    for p in prioridades:
        livres = [i for i in range(W) if len(pilhas[i]) < lim]
        pilhas[rng.choice(livres)].append(p)
    return pilhas


def pequenas(sementes=10):
    """(A) W=3..5, H=4..5, N<=20. N = W*(H-1) deixa folga p/ realocar
    (5x5 -> N=20, o teto do conjunto). Também gera N reduzido."""
    inst = {}
    for W in (3, 4, 5):
        for H in (4, 5):
            n_max = min(20, W * (H - 1), (W - 1) * H + 1)
            for N in sorted({n_max, max(W + 1, n_max - W)}):
                for s in range(sementes):
                    nome = f"A_W{W}_H{H}_N{N}_{s:02d}"
                    seed = W * 1_000_000 + H * 100_000 + N * 1_000 + s
                    inst[nome] = dict(
                        W=W, H=H, N=N, seed=seed,
                        bay=gerar_instancia(W, H, N, seed),
                    )
    return inst


def cvs(Ws=(3, 4, 5, 6, 7, 8, 9, 10), Ts=(3, 4, 5, 6), sementes=40):
    """(B) Estilo Caserta/Voß/Sniedovich: N = W*T, H = T+2.
    ATENÇÃO: reproduz a *distribuição* das instâncias, não os arquivos
    originais (que são sorteios específicos)."""
    inst = {}
    for W in Ws:
        for T in Ts:
            H, N = T + 2, W * T
            for s in range(1, sementes + 1):
                nome = f"data{W}-{T}-{s}"
                seed = W * 1_000_000 + T * 10_000 + s
                inst[nome] = dict(
                    W=W, H=H, N=N, seed=seed,
                    bay=gerar_instancia(W, H, N, seed, altura_inicial=T),
                )
    return inst


# ---------------------------------------------------------------- E/S
def salvar_json(inst, caminho):
    Path(caminho).write_text(json.dumps(inst, indent=1), encoding="utf-8")


def salvar_txt(nome, d, pasta):
    linhas = [f"{d['W']} {d['H']} {d['N']}"]
    linhas += [" ".join(map(str, [len(p)] + p)) for p in d["bay"]]
    (Path(pasta) / f"{nome}.txt").write_text("\n".join(linhas) + "\n")

def ler_txt_cvs(caminho):
    """Lê instância original (baixada da literatura) -> lista de pilhas."""
    L = Path(caminho).read_text().split("\n")
    W, N = map(int, L[0].split())
    bay = []
    for i in range(1, W + 1):
        v = list(map(int, L[i].split()))
        bay.append(v[1:1 + v[0]])
    return bay


def mostrar(bay, H):
    for nivel in range(H - 1, -1, -1):
        print(" ".join(f"{p[nivel]:3d}" if nivel < len(p) else "  ." for p in bay))
    print("-" * (4 * len(bay)))


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "instancias"
    (out / "A").mkdir(parents=True, exist_ok=True)
    A = pequenas()
    salvar_json(A, out / "A_pequenas.json")
    for n, d in A.items():
        salvar_txt(n, d, out / "A")
    print(f"A: {len(A)} instâncias")
    # for n, d in B.items():
    #     salvar_txt_cvs(n, d, out / "B")

    # print(f"A: {len(A)} instâncias | B: {len(B)} instâncias")
    # n0 = next(iter(A))
    # print(n0); mostrar(A[n0]["bay"], A[n0]["H"])

