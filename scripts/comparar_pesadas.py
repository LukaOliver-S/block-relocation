"""Reshuffles e tempo de A*, B&B, Min-Max, RS-5 e PM-3 nas instancias mais
pesadas (classes de B com 100% de ocupacao), deixando explicito onde os exatos
estouraram o limite de tempo.

Uso: python scripts/comparar_pesadas.py [--timeout 60] [--jobs 4]
                                        [--arquivos brp_W7_H6_N37,...]
     python scripts/comparar_pesadas.py --so-tabelas   # refaz as tabelas a partir de
                                                        # resultados/pesadas_bruto.csv

Timeouts:
  A*   ao estourar nao devolve solucao -> reshuffles "TL"
  B&B  ao estourar devolve a melhor solucao achada (sem prova de otimo)
       -> reshuffles marcados com "*"

Saidas:
  resultados/pesadas_bruto.csv               instancia x metodo
  resultados/tabela_pesadas_instancias.md/.csv + graficos/tabela_pesadas_instancias.png
  resultados/tabela_pesadas_classes.md/.csv    + graficos/tabela_pesadas_classes.png
"""
import argparse, textwrap
from concurrent.futures import ThreadPoolExecutor

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from rodar_comparacao import PASTA, RES, RE_NOME, rodar, fmt3

GRAF = RES.parent / "graficos"
PESADAS = ["brp_W7_H6_N37", "brp_W7_H7_N43", "brp_W7_H8_N49"]
METODOS = ["ASTAR", "DFBB", "MM", "RS-5", "PM-3"]
NOMES = {"ASTAR": "A*", "DFBB": "B&B", "MM": "Min-Max", "RS-5": "RS-5", "PM-3": "PM-3"}
TXT, TXT2, GRID, FUNDO, ALERTA = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb", "#fde4d9"


def tabela_png(fmt, destaque, titulo, nota, caminho, largura):
    """destaque: conjunto de (linha, coluna) (0-based nos dados) com fundo de alerta."""
    fig, ax = plt.subplots(figsize=(largura, 0.30 * (len(fmt) + 2) + 1.2), facecolor=FUNDO)
    ax.axis("off")
    cab = [c.replace(" ", "\n", 1) if c not in ("Instância", "Classe") else c
           for c in fmt.columns]
    tb = ax.table(cellText=fmt.values, colLabels=cab, cellLoc="right", colLoc="center",
                  bbox=[0, 0, 1, 1])
    tb.auto_set_font_size(False)
    tb.set_fontsize(9)
    for (i, j), cel in tb.get_celld().items():
        cel.set_edgecolor(GRID)
        if i == 0:
            cel.set_text_props(weight="bold", color=TXT)
            cel.set_facecolor("#efeeea")
            continue
        cel.set_facecolor(ALERTA if (i - 1, j) in destaque else
                          (FUNDO if i % 2 else "#f5f4f1"))
        cel.get_text().set_color(TXT)
        if fmt.iloc[i - 1, 0] == "Total":
            cel.set_text_props(weight="bold")
        if j == 0:
            cel.get_text().set_horizontalalignment("left")
            cel.PAD = 0.04
    ax.set_title(titulo, fontweight="bold", color=TXT, pad=10)
    nota = textwrap.fill(nota, int(largura * 13))
    fig.text(0.01, 0.01, nota, fontsize=8, color=TXT2, va="bottom")
    fig.tight_layout(rect=(0, (nota.count("\n") + 1) * 0.16 / fig.get_figheight() + 0.01, 1, 1))
    fig.savefig(caminho, dpi=150, facecolor=FUNDO)
    plt.close(fig)


def salvar_md(fmt, caminho, legenda):
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write("| " + " | ".join(fmt.columns) + " |\n")
        fh.write("|" + "|".join([":---"] + ["---:"] * (len(fmt.columns) - 1)) + "|\n")
        for _, row in fmt.iterrows():
            fh.write("| " + " | ".join(map(str, row.values)) + " |\n")
        fh.write("\n" + legenda + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--arquivos", default=",".join(PESADAS))
    ap.add_argument("--so-tabelas", action="store_true")
    a = ap.parse_args()
    filtro = a.arquivos.split(",")

    arqs = sorted((f for f in PASTA.glob("*.txt") if RE_NOME.search(f.name)
                   and RE_NOME.search(f.name).group(1) in filtro),
                  key=lambda f: (filtro.index(RE_NOME.search(f.name).group(1)),
                                 int(RE_NOME.search(f.name).group(5))))
    if a.so_tabelas:
        d = pd.read_csv(RES / "pesadas_bruto.csv", keep_default_na=False)
    else:
        tarefas = [(f, m) for f in arqs for m in METODOS]
        print(f"{len(arqs)} instancias x {len(METODOS)} metodos (limite {a.timeout} s)")
        with ThreadPoolExecutor(a.jobs) as ex:
            linhas = list(ex.map(lambda t: rodar(*t, a.timeout), tarefas))
        d = pd.DataFrame(linhas)
        d.to_csv(RES / "pesadas_bruto.csv", index=False)
    d["classe"] = d.apply(lambda x: f"W{x.W} H{x.H} N{x.N}", axis=1)
    d["tl"] = d.status == "timeout"
    d["Z"] = pd.to_numeric(d.reshuffles, errors="coerce")
    d["t"] = pd.to_numeric(d.tempo_s, errors="coerce")
    TL = a.timeout

    # ---------- por instancia ----------
    linhas_i, raw_i, dest_i = [], [], set()
    for f in arqs:
        arq, *_, ident = RE_NOME.search(f.name).groups()
        lin, raw = {"Instância": f"{arq.replace('brp_', '')} id {ident}"}, {"instancia": f"{arq}_id{ident}"}
        for m in METODOS:
            x = d[(d.arquivo == arq) & (d.id == int(ident)) & (d.metodo == m)].iloc[0]
            if x.tl and pd.isna(x.Z):
                z = "TL"
            elif x.tl:
                z = f"{int(x.Z)}*"
            elif x.status == "ok":
                z = f"{int(x.Z)}"
            else:
                z = x.status
            tt = f"≥{TL} s" if x.tl else fmt3(x.t * 1000)
            lin[f"{NOMES[m]} reshuffles"], lin[f"{NOMES[m]} tempo (ms)"] = z, tt
            raw[f"{m}_reshuffles"] = "" if pd.isna(x.Z) else int(x.Z)
            raw[f"{m}_tempo_s"] = TL if x.tl else x.t
            raw[f"{m}_status"] = x.status
            if x.tl:
                c = list(lin).index(f"{NOMES[m]} reshuffles")
                dest_i |= {(len(linhas_i), c), (len(linhas_i), c + 1)}
        linhas_i.append(lin)
        raw_i.append(raw)
    ti = pd.DataFrame(linhas_i)
    pd.DataFrame(raw_i).to_csv(RES / "tabela_pesadas_instancias.csv", index=False)

    legenda = (f"TL = A* estourou o limite de {TL} s sem solução. "
               f"* = B&B estourou {TL} s; valor = melhor solução achada (sem prova de ótimo). "
               f"≥{TL} s = tempo esgotado. Tempos em milissegundos. Células destacadas = timeout. "
               "A* e Min-Max: BRP restrito; B&B, RS-5 e PM-3: irrestrito.")
    salvar_md(ti, RES / "tabela_pesadas_instancias.md", legenda)
    tabela_png(ti, dest_i, "Instâncias mais pesadas: reshuffles e tempo por instância",
               legenda, GRAF / "tabela_pesadas_instancias.png", 17)

    # ---------- por classe ----------
    linhas_c, dest_c = [], set()
    classes = list(dict.fromkeys(d.classe))
    for c in classes + ["Total"]:
        g = d if c == "Total" else d[d.classe == c]
        lin = {"Classe": c}
        for m in METODOS:
            gm = g[g.metodo == m]
            ok = gm[gm.status == "ok"]
            n_tl = int(gm.tl.sum())
            lin[f"{NOMES[m]} timeouts"] = f"{n_tl}/{len(gm)}"
            lin[f"{NOMES[m]} reshuffles"] = f"{ok.Z.mean():.2f}" if len(ok) else "—"
            lin[f"{NOMES[m]} tempo (ms)"] = fmt3(ok.t.mean() * 1000) if len(ok) else "—"
            if n_tl:
                dest_c.add((len(linhas_c), list(lin).index(f"{NOMES[m]} timeouts")))
        linhas_c.append(lin)
    tc = pd.DataFrame(linhas_c)
    tc.to_csv(RES / "tabela_pesadas_classes.csv", index=False)
    leg_c = (f"Médias só das execuções concluídas dentro de {TL} s (para A* e B&B, apenas as "
             "instâncias resolvidas: com muitos timeouts, a média é de poucas instâncias, "
             "possivelmente as mais fáceis). Timeouts = execuções que estouraram o limite. "
             "A* e Min-Max: BRP restrito; B&B, RS-5 e PM-3: irrestrito.")
    salvar_md(tc, RES / "tabela_pesadas_classes.md", leg_c)
    tabela_png(tc, dest_c, "Instâncias mais pesadas: médias por classe", leg_c,
               GRAF / "tabela_pesadas_classes.png", 19)

    print(tc.to_string(index=False))
    for p in ("pesadas_bruto.csv", "tabela_pesadas_instancias.md", "tabela_pesadas_classes.md"):
        print("->", RES / p)
    print("->", GRAF / "tabela_pesadas_instancias.png")
    print("->", GRAF / "tabela_pesadas_classes.png")


if __name__ == "__main__":
    main()
