"""Efeito da largura w no rake search (RS-w) e no pilot method (PM-w).

Uso: python scripts/variar_largura.py [--larguras 1,2,3,4,5,7,10] [--conjunto A]
                                      [--timeout 60] [--jobs 4]
     python scripts/variar_largura.py --pesadas      # classes de B com 100% de ocupacao
     python scripts/variar_largura.py --arquivos brp_W7_H8_N49,... --sufixo _x

Roda RS-w e PM-w em cada instancia (mesma chamada de scripts/rodar_comparacao.py)
e compara com o otimo irrestrito do B&B: lido de resultados/metricas_comparacao.csv
quando existe; senao o B&B (DFBB) e rodado aqui. Se o B&B estourar o tempo, a
referencia e o melhor valor conhecido (menor Z entre B&B e todos os RS-w/PM-w).
As saidas recebem o --sufixo (padrao "_pesadas" com --pesadas).

Saidas:
    resultados/largura_bruto.csv       instancia x metodo x w
    resultados/tabela_largura.csv/.md  medias por w (todas as instancias)
    resultados/tabela_largura_classe.csv  medias por w e classe
    graficos/tabela_largura.png
"""
import argparse, csv, textwrap
from concurrent.futures import ThreadPoolExecutor

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from rodar_comparacao import PASTA, RES, RE_NOME, conjunto_de, rodar, calcular_gap, fmt3

GRAF = RES.parent / "graficos"
TXT, TXT2, GRID, FUNDO = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
FAMILIAS = [("RS", "RS"), ("PM", "PM")]


PESADAS = ["brp_W7_H6_N37", "brp_W7_H7_N43", "brp_W7_H8_N49"]


def ler_otimos():
    p = RES / "metricas_comparacao.csv"
    if not p.exists():
        return {}
    with open(p, newline="") as fh:
        return {(l["arquivo"], int(l["id"])): int(l["Z_irrestrito"])
                for l in csv.DictReader(fh)
                if l["metodo"] == "DFBB" and l["Z_irrestrito"] != ""}


def tabela_png(fmt, titulo, nota, caminho):
    fig, ax = plt.subplots(figsize=(15, 0.36 * (len(fmt) + 2) + 1.1), facecolor=FUNDO)
    ax.axis("off")
    cab = [c.replace(" ", "\n", 1) if c != "w" else c for c in fmt.columns]
    tb = ax.table(cellText=fmt.values, colLabels=cab, cellLoc="right", colLoc="center",
                  bbox=[0, 0, 1, 1])
    tb.auto_set_font_size(False)
    tb.set_fontsize(9.5)
    for (i, j), cel in tb.get_celld().items():
        cel.set_edgecolor(GRID)
        if i == 0:
            cel.set_text_props(weight="bold", color=TXT)
            cel.set_facecolor("#efeeea")
        else:
            cel.set_facecolor(FUNDO if i % 2 else "#f5f4f1")
            cel.get_text().set_color(TXT)
            if j == 0:
                cel.get_text().set_horizontalalignment("center")
    ax.set_title(titulo, fontweight="bold", color=TXT, pad=10)
    nota = textwrap.fill(nota, 190)
    fig.text(0.01, 0.01, nota, fontsize=8, color=TXT2, va="bottom")
    fig.tight_layout(rect=(0, (nota.count("\n") + 1) * 0.16 / fig.get_figheight() + 0.01, 1, 1))
    fig.savefig(caminho, dpi=150, facecolor=FUNDO)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--larguras", default="1,2,3,4,5,7,10")
    ap.add_argument("--conjunto", default="A", choices=["A", "B", "AB"])
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--arquivos", default="", help="classes separadas por virgula")
    ap.add_argument("--pesadas", action="store_true")
    ap.add_argument("--sufixo", default=None)
    a = ap.parse_args()
    if a.pesadas:
        a.arquivos = ",".join(PESADAS)
    suf = a.sufixo if a.sufixo is not None else ("_pesadas" if a.pesadas else "")
    filtro = [x for x in a.arquivos.split(",") if x]
    larguras = [int(w) for w in a.larguras.split(",")]

    otimos = ler_otimos()
    arqs = sorted(f for f in PASTA.glob("*.txt") if RE_NOME.search(f.name) and (
        RE_NOME.search(f.name).group(1) in filtro if filtro
        else conjunto_de(f.name) in a.conjunto))
    chave = lambda f: (RE_NOME.search(f.name).group(1), int(RE_NOME.search(f.name).group(5)))
    faltam = [f for f in arqs if chave(f) not in otimos]
    tarefas = [(f, f"{fam}-{w}") for f in arqs for _, fam in FAMILIAS for w in larguras]
    tarefas += [(f, "DFBB") for f in faltam]
    print(f"{len(arqs)} instancias x {len(FAMILIAS) * len(larguras)} configuracoes"
          f" + B&B em {len(faltam)}")
    with ThreadPoolExecutor(a.jobs) as ex:
        todas = list(ex.map(lambda t: rodar(*t, a.timeout), tarefas))
    linhas = [l for l in todas if l["metodo"] != "DFBB"]

    # referencia por instancia: otimo do B&B, senao melhor conhecido
    tipo_ref = {k: "otimo" for k in otimos}
    for l in todas:
        if l["metodo"] == "DFBB" and l["status"] == "ok":
            otimos[(l["arquivo"], l["id"])] = l["reshuffles"]
            tipo_ref[(l["arquivo"], l["id"])] = "otimo"
    for l in todas:
        k = (l["arquivo"], l["id"])
        if tipo_ref.get(k) != "otimo" and l["reshuffles"] != "":
            otimos[k] = min(otimos.get(k, 10**9), l["reshuffles"])
            tipo_ref[k] = "melhor_conhecido"

    for l in linhas:
        l["familia"], l["w"] = l["metodo"].split("-")
        l["w"] = int(l["w"])
        zs = otimos.get((l["arquivo"], l["id"]))
        l["Z_otimo"] = zs if zs is not None else ""
        l["ref_tipo"] = tipo_ref.get((l["arquivo"], l["id"]), "sem_referencia")
        l["gap"] = (round(calcular_gap(l["reshuffles"], zs), 6)
                    if l["status"] == "ok" and zs is not None else "")
    d = pd.DataFrame(linhas)
    d.to_csv(RES / f"largura_bruto{suf}.csv", index=False)

    ok = d[d.status == "ok"].copy()
    ok["gap"] = ok.gap.astype(float)
    ok["otimo"] = ok.reshuffles == ok.Z_otimo

    def agrega(g):
        return pd.Series({"reshuffles": g.reshuffles.mean(), "gap": g.gap.mean() * 100,
                          "gap_max": g.gap.max() * 100,
                          "otimos": f"{int(g.otimo.sum())}/{len(g)}",
                          "tempo": g.tempo_s.mean(), "tempo_max": g.tempo_s.max()})

    # por classe (CSV de detalhe)
    ok["classe"] = ok.apply(lambda x: f"W{x.W} H{x.H} N{x.N}", axis=1)
    ok.groupby(["familia", "w", "classe"]).apply(agrega, include_groups=False) \
      .reset_index().to_csv(RES / f"tabela_largura_classe{suf}.csv", index=False)

    # tabela principal: uma linha por w, colunas por familia
    resumo = ok.groupby(["familia", "w"]).apply(agrega, include_groups=False)
    tab = pd.DataFrame({"w": larguras})
    for _, fam in FAMILIAS:
        r = resumo.loc[fam].reindex(larguras)
        tab[f"{fam}-w reshuffles médio"] = r.reshuffles.values
        tab[f"{fam}-w gap médio (%)"] = r.gap.values
        tab[f"{fam}-w gap máx (%)"] = r.gap_max.values
        tab[f"{fam}-w = ótimo"] = r.otimos.values
        tab[f"{fam}-w tempo médio (ms)"] = r.tempo.values * 1000
    tab.to_csv(RES / f"tabela_largura{suf}.csv", index=False)

    fmt = tab.copy()
    for c in fmt.columns:
        if "reshuffles" in c:
            fmt[c] = fmt[c].map(lambda v: f"{v:.2f}")
        elif "(%)" in c:
            fmt[c] = fmt[c].map(lambda v: f"{v:.2f}")
        elif "(ms)" in c:
            fmt[c] = fmt[c].map(fmt3)
    with open(RES / f"tabela_largura{suf}.md", "w", encoding="utf-8") as fh:
        fh.write("| " + " | ".join(fmt.columns) + " |\n")
        fh.write("|" + "|".join([":---:"] + ["---:"] * (len(fmt.columns) - 1)) + "|\n")
        for _, row in fmt.iterrows():
            fh.write("| " + " | ".join(map(str, row.values)) + " |\n")

    n = len(arqs)
    n_ot = sum(tipo_ref.get(chave(f)) == "otimo" for f in arqs)
    if filtro:
        conj = ", ".join(x.replace("brp_", "").replace("_", " ") for x in filtro)
    else:
        conj = "conjunto " + a.conjunto if len(a.conjunto) == 1 else "conjuntos A e B"
    ref_txt = ("Z* = ótimo irrestrito do B&B" if n_ot == n else
               f"Z* = ótimo irrestrito do B&B em {n_ot}/{n} instâncias; nas demais o B&B "
               f"estourou {a.timeout} s e Z* = melhor valor conhecido (menor Z entre B&B e "
               "todos os RS-w/PM-w)")
    tabela_png(fmt, f"Rake search (RS-w) e pilot method (PM-w) variando a largura w ({conj})",
               f"Médias sobre {n} instâncias. Gap = (Z − Z*)/Z*, com {ref_txt} (RS e PM são "
               "irrestritos). '= ótimo' = instâncias em que o método atingiu Z*.",
               GRAF / f"tabela_largura{suf}.png")
    print(fmt.to_string(index=False))
    print(f"referencia: otimo em {n_ot}/{n}")
    for p in (f"tabela_largura{suf}.md", f"tabela_largura{suf}.csv",
              f"tabela_largura_classe{suf}.csv", f"largura_bruto{suf}.csv"):
        print("->", RES / p)
    print("->", GRAF / f"tabela_largura{suf}.png")


if __name__ == "__main__":
    main()
