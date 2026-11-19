"""Gera os graficos de comparacao heuristicas x A* a partir dos CSVs de
scripts/rodar_comparacao.py. Saida: graficos/*.png

Uso: python scripts/gerar_graficos.py               # so conjunto A (padrao)
     python scripts/gerar_graficos.py --conjunto AB  # A e B
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "resultados"
OUT = RAIZ / "graficos"
OUT.mkdir(exist_ok=True)

METODOS = ["ASTAR", "MM", "RS-5", "PM-3"]
HEUR = ["MM", "RS-5", "PM-3"]
NOMES = {"ASTAR": "A*", "MM": "Min-Max", "RS-5": "RS-5", "PM-3": "PM-3"}
COR = {"ASTAR": "#2a78d6", "MM": "#eda100", "RS-5": "#eb6834", "PM-3": "#1baf7a"}  # fixa por metodo
TXT, TXT2, GRID, FUNDO = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
NOTA_IRR = ("Min-Max e A* são restritos (gap do Min-Max ≥ 0); RS-5 e PM-3 resolvem o BRP "
            "irrestrito: gap < 0 é possível.")

plt.rcParams.update({
    "figure.facecolor": FUNDO, "axes.facecolor": FUNDO, "savefig.facecolor": FUNDO,
    "axes.edgecolor": GRID, "axes.labelcolor": TXT2, "xtick.color": TXT2,
    "ytick.color": TXT2, "text.color": TXT, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.axisbelow": True, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 10, "axes.titlesize": 12,
    "axes.titleweight": "bold", "legend.frameon": False,
})

ap = argparse.ArgumentParser()
ap.add_argument("--conjunto", default="A", choices=["A", "B", "AB"])
CONJ = list(ap.parse_args().conjunto)

m = pd.read_csv(RES / "metricas_comparacao.csv")
r = pd.read_csv(RES / "resumo_por_classe.csv")
m, r = m[m.conjunto.isin(CONJ)].copy(), r[r.conjunto.isin(CONJ)].copy()
m["classe"] = m.apply(lambda x: f"W{x.W} H{x.H} N{x.N}", axis=1)
r["classe"] = r.apply(lambda x: f"W{x.W} H{x.H} N{x.N}", axis=1)
classes = list(dict.fromkeys(r.sort_values(["conjunto", "W", "H", "N"])["classe"]))
x = np.arange(len(classes))
LARG = max(8, 0.75 * len(classes) + 4)
SUF = "" if len(CONJ) > 1 else f" (conjunto {CONJ[0]})"
ok = m[m.status == "ok"].copy()


def salvar(fig, nome, nota=None):
    base = 0
    if nota:
        import textwrap
        largura = int(fig.get_figwidth() * 15)   # ~caracteres por linha (fonte 8)
        nota = textwrap.fill(nota, largura)
        fig.text(0.01, 0.01, nota, fontsize=8, color=TXT2, va="bottom")
        base = (nota.count("\n") + 1) * 0.16 / fig.get_figheight() + 0.01
    fig.tight_layout(rect=(0, base, 1, 1))
    fig.savefig(OUT / nome, dpi=150)
    plt.close(fig)
    print("->", OUT / nome)


def separar_conjuntos(ax):
    nA = sum(c.startswith(("W3", "W4", "W5", "W6")) for c in classes)
    if 0 < nA < len(classes):
        ax.axvline(nA - 0.5, color=TXT2, lw=1, ls=":")
        ax.text(nA / 2 - 0.5, 1.01, "Conjunto A", transform=ax.get_xaxis_transform(),
                ha="center", color=TXT2, fontsize=9)
        ax.text((nA + len(classes)) / 2 - 0.5, 1.01, "Conjunto B",
                transform=ax.get_xaxis_transform(), ha="center", color=TXT2, fontsize=9)


def barras(col, titulo, ylabel, nome, metodos=METODOS, log=False, fator=1.0,
           linha_zero=False, nota=None):
    fig, ax = plt.subplots(figsize=(LARG, 5))
    w = 0.8 / len(metodos)
    for i, met in enumerate(metodos):
        s = r[r.metodo == met].set_index("classe").reindex(classes)[col] * fator
        ax.bar(x + (i - (len(metodos) - 1) / 2) * w, s.values, w * 0.92,
               color=COR[met], label=NOMES[met])
    ax.set_xticks(x, classes, rotation=45, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo + SUF, pad=18)
    if log:
        ax.set_yscale("log")
    if linha_zero:
        ax.axhline(0, color=TXT2, lw=1)
    separar_conjuntos(ax)
    ax.legend(ncol=len(metodos), loc="lower left" if linha_zero else "upper left")
    salvar(fig, nome, nota)


# 1) reshuffles medios
barras("reshuffles_medio", "Reshuffles médios por classe", "reshuffles (média)",
       "reshuffles_por_classe.png",
       nota="Médias só das execuções concluídas (A* exclui timeouts). " + NOTA_IRR)

# 2) tabela: reshuffles e tempo medios por classe e metodo
def tabela_reshuffles_tempo():
    linhas = []
    for c in classes:
        lin = {"Classe": c}
        for met in METODOS:
            s = r[(r.classe == c) & (r.metodo == met)].iloc[0]
            lin[f"{NOMES[met]} reshuffles"] = s.reshuffles_medio
            lin[f"{NOMES[met]} tempo (s)"] = s.tempo_medio_s
            if met == "ASTAR":
                lin["A* resolvidas"] = f"{int(s.n_ok)}/{int(s.n_instancias)}"
        linhas.append(lin)
    t = pd.DataFrame(linhas)
    t.to_csv(RES / "tabela_reshuffles_tempo.csv", index=False)

    fmt = t.copy()
    for col in fmt.columns:
        if col.endswith("reshuffles"):
            fmt[col] = fmt[col].map(lambda v: f"{v:.1f}")
        elif col.endswith("(s)"):
            fmt[col] = fmt[col].map(lambda v: f"{v:.4f}")
    with open(RES / "tabela_reshuffles_tempo.md", "w", encoding="utf-8") as fh:
        fh.write("| " + " | ".join(fmt.columns) + " |\n")
        fh.write("|" + "|".join(["---"] + ["---:"] * (len(fmt.columns) - 1)) + "|\n")
        for _, row in fmt.iterrows():
            fh.write("| " + " | ".join(map(str, row.values)) + " |\n")

    fig, ax = plt.subplots(figsize=(16, 0.32 * (len(fmt) + 2) + 1.0))
    ax.axis("off")
    cab = [c.replace(" reshuffles", "\nreshuffles").replace(" tempo", "\ntempo")
           .replace(" resolvidas", "\nresolvidas") for c in fmt.columns]
    tb = ax.table(cellText=fmt.values, colLabels=cab, cellLoc="right",
                  colLoc="center", bbox=[0, 0, 1, 1])
    tb.auto_set_font_size(False)
    tb.set_fontsize(9)
    for (i, j), cel in tb.get_celld().items():
        cel.set_edgecolor(GRID)
        if i == 0:
            cel.set_text_props(weight="bold", color=TXT)
            cel.set_facecolor("#efeeea")
        else:
            cel.set_facecolor(FUNDO if i % 2 else "#f5f4f1")
            if j == 0:
                cel.get_text().set_horizontalalignment("left")
                cel.PAD = 0.05
    ax.set_title("Reshuffles e tempo médios por classe" + SUF, fontweight="bold", pad=10)
    salvar(fig, "tabela_reshuffles_tempo.png",
           "Médias das execuções concluídas; para o A*, só das instâncias resolvidas "
           "no tempo (ver 'A* resolvidas'). " + NOTA_IRR)
    print("->", RES / "tabela_reshuffles_tempo.csv")
    print("->", RES / "tabela_reshuffles_tempo.md")


tabela_reshuffles_tempo()

# 3) gap medio das heuristicas
barras("gap_medio", "Gap médio das heurísticas em relação a Z_ref", "gap médio (%)",
       "gap_por_classe.png", metodos=HEUR, fator=100, linha_zero=True,
       nota="Z_ref = ótimo do A* quando terminou; senão melhor conhecido. " + NOTA_IRR)

# 4) boxplot do gap por metodo e conjunto
fig, axs = plt.subplots(1, len(CONJ), figsize=(5.5 * len(CONJ), 4.5), sharey=True,
                        squeeze=False)
axs = axs[0]
for ax, conj in zip(axs, CONJ):
    dados = [ok[(ok.conjunto == conj) & (ok.metodo == met)].gap.dropna() * 100
             for met in HEUR]
    bp = ax.boxplot(dados, patch_artist=True, widths=0.5,
                    medianprops=dict(color=TXT, lw=1.5))
    for patch, met in zip(bp["boxes"], HEUR):
        patch.set(facecolor=COR[met], alpha=0.85, edgecolor=TXT2)
    ax.set_xticks(range(1, len(HEUR) + 1), [NOMES[h] for h in HEUR])
    ax.axhline(0, color=TXT2, lw=1)
    if len(CONJ) > 1:
        ax.set_title(f"Conjunto {conj}")
axs[0].set_ylabel("gap (%)")
fig.suptitle("Distribuição do gap por heurística" + SUF, fontweight="bold")
salvar(fig, "gap_boxplot.png", NOTA_IRR)

# 5) tempo x gap
fig, ax = plt.subplots(figsize=(8, 5))
for met in HEUR:
    d = ok[ok.metodo == met]
    ax.scatter(d.tempo_s.clip(lower=1e-4), d.gap * 100, s=36, color=COR[met],
               edgecolor=FUNDO, linewidth=1, label=NOMES[met], alpha=0.85)
d = ok[ok.metodo == "ASTAR"]
ax.scatter(d.tempo_s.clip(lower=1e-4), d.gap * 100, s=36, color=COR["ASTAR"],
           edgecolor=FUNDO, linewidth=1, label="A*", alpha=0.85, marker="s")
ax.set_xscale("log")
ax.axhline(0, color=TXT2, lw=1)
ax.set_xlabel("tempo (s, log; 0 mostrado como 1e-4)")
ax.set_ylabel("gap (%)")
ax.set_title("Tempo × gap por instância" + SUF)
ax.legend()
salvar(fig, "tempo_vs_gap.png", NOTA_IRR)

# 6) taxa de resolucao do A* (so se houve timeout)
a = r[r.metodo == "ASTAR"].set_index("classe").reindex(classes)
if (a.n_ok < a.n_instancias).any():
    fig, ax = plt.subplots(figsize=(LARG, 4.5))
    frac = a.n_ok / a.n_instancias * 100
    ax.bar(x, frac.values, 0.6, color=COR["ASTAR"], label="resolvidas")
    for xi, (v, n, t) in enumerate(zip(frac.values, a.n_ok, a.n_instancias)):
        ax.text(xi, v + 2, f"{int(n)}/{int(t)}", ha="center", fontsize=8, color=TXT2)
    ax.set_xticks(x, classes, rotation=45, ha="right")
    ax.set_ylim(0, 112)
    ax.set_ylabel("% resolvidas no tempo")
    ax.set_title("Instâncias resolvidas pelo A* dentro do limite de tempo", pad=18)
    separar_conjuntos(ax)
    salvar(fig, "astar_resolvidas.png")

# tabela resumida no terminal
tab = r.pivot_table(index="classe", columns="metodo",
                    values=["reshuffles_medio", "tempo_medio_s", "gap_medio"]).reindex(classes)
print(tab.round(4).to_string())
