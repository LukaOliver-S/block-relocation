"""Gera os graficos de comparacao heuristicas x exatos (A*, B&B) a partir dos CSVs de
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

from rodar_comparacao import fmt3

RAIZ = Path(__file__).resolve().parent.parent
RES = RAIZ / "resultados"
OUT = RAIZ / "graficos"
OUT.mkdir(exist_ok=True)

METODOS = ["ASTAR", "DFBB", "MM", "RS-5", "PM-3"]
EXATOS = ["ASTAR", "DFBB"]
HEUR = ["MM", "RS-5", "PM-3"]
# metodos ocultos nos GRAFICOS (continuam nos CSVs e na tabela)
OCULTAR_GRAF = {"MM"}
METODOS_G = [m for m in METODOS if m not in OCULTAR_GRAF]
HEUR_G = [m for m in HEUR if m not in OCULTAR_GRAF]
NOMES = {"ASTAR": "A*", "DFBB": "B&B", "MM": "Min-Max", "RS-5": "RS-5", "PM-3": "PM-3"}
COR = {"ASTAR": "#2a78d6", "DFBB": "#e87ba4", "MM": "#eda100", "RS-5": "#eb6834", "PM-3": "#1baf7a"}  # fixa por metodo
TXT, TXT2, GRID, FUNDO = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
NOTA_IRR = ("Gap contra o ótimo da variante de cada método: Min-Max vs A* (BRP restrito); "
            "RS-5 e PM-3 vs B&B (BRP irrestrito).")
NOTA_G = ("Gap contra o ótimo da variante de cada método: RS-5 e PM-3 vs B&B "
          "(BRP irrestrito). Min-Max oculto nos gráficos (ver tabela).")

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


def barras(col, titulo, ylabel, nome, metodos=None, log=False, fator=1.0,
           linha_zero=False, nota=None):
    metodos = metodos or METODOS_G
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
       nota="Médias só das execuções concluídas (exatos excluem timeouts). " + NOTA_G)

# 2) tabelas numericas (PNG + CSV + Markdown)
def salvar_tabela(fmt, nome, titulo, nota, largura):
    """fmt: DataFrame ja formatado como texto. Salva .md em resultados/ e .png em graficos/."""
    with open(RES / f"{nome}.md", "w", encoding="utf-8") as fh:
        fh.write("| " + " | ".join(fmt.columns) + " |\n")
        fh.write("|" + "|".join(["---"] + ["---:"] * (len(fmt.columns) - 1)) + "|\n")
        for _, row in fmt.iterrows():
            fh.write("| " + " | ".join(map(str, row.values)) + " |\n")
    fig, ax = plt.subplots(figsize=(largura, 0.32 * (len(fmt) + 2) + 1.0))
    ax.axis("off")
    cab = [c.replace(" ", "\n", 1) if c != "Classe" else c for c in fmt.columns]
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
            if fmt.iloc[i - 1, 0] == "Total":
                cel.set_text_props(weight="bold")
            if j == 0:
                cel.get_text().set_horizontalalignment("left")
                cel.PAD = 0.05
    ax.set_title(titulo + SUF, fontweight="bold", pad=10)
    salvar(fig, f"{nome}.png", nota)
    print("->", RES / f"{nome}.md")


def tabela_reshuffles_tempo():
    linhas = []
    for c in classes:
        lin = {"Classe": c}
        for met in METODOS:
            s = r[(r.classe == c) & (r.metodo == met)].iloc[0]
            lin[f"{NOMES[met]} reshuffles"] = s.reshuffles_medio
            lin[f"{NOMES[met]} tempo (ms)"] = s.tempo_medio_s * 1000
            if met in EXATOS:
                lin[f"{NOMES[met]} resolvidas"] = f"{int(s.n_ok)}/{int(s.n_instancias)}"
        linhas.append(lin)
    t = pd.DataFrame(linhas)
    t.to_csv(RES / "tabela_reshuffles_tempo.csv", index=False)
    fmt = t.copy()
    for col in fmt.columns:
        if col.endswith("reshuffles"):
            fmt[col] = fmt[col].map(lambda v: f"{v:.1f}")
        elif col.endswith("(ms)"):
            fmt[col] = fmt[col].map(fmt3)
    salvar_tabela(fmt, "tabela_reshuffles_tempo", "Reshuffles e tempo médios por classe",
                  "Médias das execuções concluídas; para os exatos, só das instâncias "
                  "resolvidas no tempo (ver colunas 'resolvidas'). " + NOTA_IRR, 19)


def tabela_gap():
    """Gap de cada heuristica contra o otimo da sua variante, por classe + total."""
    REF = {"MM": "A*", "RS-5": "B&B", "PM-3": "B&B"}
    linhas = []
    for c in classes + ["Total"]:
        lin = {"Classe": c}
        for met in HEUR:
            d = ok[(ok.metodo == met) & ((ok.classe == c) | (c == "Total"))]
            g = d.gap.dropna() * 100
            nome = f"{NOMES[met]} (vs {REF[met]})"
            lin[f"{nome} gap médio (%)"] = g.mean()
            lin[f"{nome} gap máx (%)"] = g.max()
            lin[f"{nome} = ótimo"] = f"{int((d.reshuffles == d.Z_ref).sum())}/{len(d)}"
        linhas.append(lin)
    t = pd.DataFrame(linhas)
    t.to_csv(RES / "tabela_gap.csv", index=False)
    fmt = t.copy()
    for col in fmt.columns:
        if "(%)" in col:
            fmt[col] = fmt[col].map(lambda v: f"{v:.2f}")
    salvar_tabela(fmt, "tabela_gap", "Gap das heurísticas em relação ao ótimo",
                  "Gap = (Z − Z*)/Z*, com Z* do exato da mesma variante: Min-Max vs A* "
                  "(BRP restrito); RS-5 e PM-3 vs B&B (BRP irrestrito). "
                  "'= ótimo' = instâncias em que a heurística atingiu Z*.", 19)


tabela_reshuffles_tempo()
tabela_gap()

# 6) taxa de resolucao dos exatos (so se houve timeout)
r["pct_ok"] = r.n_ok / r.n_instancias * 100
if (r[r.metodo.isin(EXATOS)].n_ok < r[r.metodo.isin(EXATOS)].n_instancias).any():
    barras("pct_ok", "Instâncias resolvidas no limite de tempo", "% resolvidas",
           "exatos_resolvidos.png", metodos=EXATOS)

# tabela resumida no terminal
tab = r.pivot_table(index="classe", columns="metodo",
                    values=["reshuffles_medio", "tempo_medio_s", "gap_medio"]).reindex(classes)
print(tab.round(4).to_string())
