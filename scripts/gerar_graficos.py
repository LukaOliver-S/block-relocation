"""Gera os graficos de comparacao heuristicas x A* a partir dos CSVs de
scripts/rodar_comparacao.py. Saida: graficos/*.png

Uso: python scripts/gerar_graficos.py
"""
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

METODOS = ["ASTAR", "RS-5", "PM-3"]
NOMES = {"ASTAR": "A*", "RS-5": "RS-5", "PM-3": "PM-3"}
COR = {"ASTAR": "#2a78d6", "RS-5": "#eb6834", "PM-3": "#1baf7a"}  # fixa por metodo
TXT, TXT2, GRID, FUNDO = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
NOTA_IRR = "RS-5 e PM-3 resolvem o BRP irrestrito: gap < 0 é possível."

plt.rcParams.update({
    "figure.facecolor": FUNDO, "axes.facecolor": FUNDO, "savefig.facecolor": FUNDO,
    "axes.edgecolor": GRID, "axes.labelcolor": TXT2, "xtick.color": TXT2,
    "ytick.color": TXT2, "text.color": TXT, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.8, "axes.axisbelow": True, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 10, "axes.titlesize": 12,
    "axes.titleweight": "bold", "legend.frameon": False,
})

m = pd.read_csv(RES / "metricas_comparacao.csv")
r = pd.read_csv(RES / "resumo_por_classe.csv")
m["classe"] = m.apply(lambda x: f"W{x.W} H{x.H} N{x.N}", axis=1)
r["classe"] = r.apply(lambda x: f"W{x.W} H{x.H} N{x.N}", axis=1)
classes = list(dict.fromkeys(r.sort_values(["conjunto", "W", "H", "N"])["classe"]))
x = np.arange(len(classes))
ok = m[m.status == "ok"].copy()


def salvar(fig, nome, nota=None):
    if nota:
        fig.text(0.01, 0.01, nota, fontsize=8, color=TXT2)
    fig.tight_layout(rect=(0, 0.03 if nota else 0, 1, 1))
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
    fig, ax = plt.subplots(figsize=(13, 5))
    w = 0.8 / len(metodos)
    for i, met in enumerate(metodos):
        s = r[r.metodo == met].set_index("classe").reindex(classes)[col] * fator
        ax.bar(x + (i - (len(metodos) - 1) / 2) * w, s.values, w * 0.92,
               color=COR[met], label=NOMES[met])
    ax.set_xticks(x, classes, rotation=45, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo, pad=18)
    if log:
        ax.set_yscale("log")
    if linha_zero:
        ax.axhline(0, color=TXT2, lw=1)
    separar_conjuntos(ax)
    ax.legend(ncol=len(metodos), loc="upper left")
    salvar(fig, nome, nota)


# 1) reshuffles medios
barras("reshuffles_medio", "Reshuffles médios por classe", "reshuffles (média)",
       "reshuffles_por_classe.png",
       nota="Médias só das execuções concluídas (A* exclui timeouts). " + NOTA_IRR)

# 2) tempo medio (log)
barras("tempo_medio_s", "Tempo de execução médio por classe (escala log)",
       "tempo (s, log)", "tempo_por_classe.png", log=True,
       nota="Tempos 0 (abaixo da resolução do clock) não aparecem em escala log.")

# 3) gap medio das heuristicas
barras("gap_medio", "Gap médio das heurísticas em relação a Z_ref", "gap médio (%)",
       "gap_por_classe.png", metodos=["RS-5", "PM-3"], fator=100, linha_zero=True,
       nota="Z_ref = ótimo do A* quando terminou; senão melhor conhecido. " + NOTA_IRR)

# 4) boxplot do gap por metodo e conjunto
fig, axs = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
for ax, conj in zip(axs, ["A", "B"]):
    dados = [ok[(ok.conjunto == conj) & (ok.metodo == met)].gap.dropna() * 100
             for met in ["RS-5", "PM-3"]]
    bp = ax.boxplot(dados, patch_artist=True, widths=0.5,
                    medianprops=dict(color=TXT, lw=1.5))
    for patch, met in zip(bp["boxes"], ["RS-5", "PM-3"]):
        patch.set(facecolor=COR[met], alpha=0.85, edgecolor=TXT2)
    ax.set_xticks([1, 2], ["RS-5", "PM-3"])
    ax.axhline(0, color=TXT2, lw=1)
    ax.set_title(f"Conjunto {conj}")
axs[0].set_ylabel("gap (%)")
fig.suptitle("Distribuição do gap por heurística", fontweight="bold")
salvar(fig, "gap_boxplot.png", NOTA_IRR)

# 5) tempo x gap
fig, ax = plt.subplots(figsize=(8, 5))
for met in ["RS-5", "PM-3"]:
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
ax.set_title("Tempo × gap por instância")
ax.legend()
salvar(fig, "tempo_vs_gap.png", NOTA_IRR)

# 6) taxa de resolucao do A*
a = r[r.metodo == "ASTAR"].set_index("classe").reindex(classes)
fig, ax = plt.subplots(figsize=(13, 4.5))
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
