"""Verifica uma solucao: simula os movimentos na instancia.
Uso: python scripts/verificar.py <instancia.txt> <solucao.txt> [--restrito]
"""
import re
import sys
from pathlib import Path

RE_MOV = re.compile(r"relocating x from (\d+) to (\d+)")


def ler_instancia(caminho):
    L = Path(caminho).read_text().splitlines()
    W, H, N = map(int, L[0].split()[:3])
    pilhas = []
    for linha in L[1:1 + W]:
        v = list(map(int, linha.split()))
        pilhas.append(v[1:1 + v[0]])
    return W, H, N, pilhas


def ler_movimentos(caminho):
    """Lista de (de, para) na ordem em que o algoritmo os fez."""
    texto = Path(caminho).read_text()
    return [(int(a), int(b)) for a, b in RE_MOV.findall(texto)]


def _recuperar(pilhas, prox, N):
    """Retira, em cascata, o proximo container enquanto ele estiver no topo."""
    while prox <= N:
        s = next(i for i, p in enumerate(pilhas) if prox in p)
        if pilhas[s][-1] != prox:
            break
        pilhas[s].pop()
        prox += 1
    return prox


def verificar(instancia, movs, restrito=False):
    """Retorna (ok, mensagem). Mensagem = Z se ok, motivo se invalida.
    restrito=True: so pode mover o topo da pilha que contem o alvo."""
    W, H, N, pilhas = ler_instancia(instancia)
    if any(len(p) > H for p in pilhas):
        return False, "instancia com pilha acima de H"
    prox = _recuperar(pilhas, 1, N)
    for k, (a, b) in enumerate(movs):
        if not (0 <= a < W and 0 <= b < W):
            return False, f"mov {k}: pilha inexistente"
        if a == b:
            return False, f"mov {k}: origem = destino"
        if not pilhas[a]:
            return False, f"mov {k}: pilha {a} vazia"
        if len(pilhas[b]) >= H:
            return False, f"mov {k}: pilha {b} cheia (H={H})"
        if restrito and prox not in pilhas[a]:
            return False, f"mov {k}: viola restricao (alvo {prox} nao esta na pilha {a})"
        pilhas[b].append(pilhas[a].pop())
        prox = _recuperar(pilhas, prox, N)
    if prox <= N:
        return False, f"baia nao esvaziou (parou no container {prox})"
    return True, len(movs)


if __name__ == "__main__":
    inst, sol = sys.argv[1], sys.argv[2]
    restrito = "--restrito" in sys.argv
    ok, msg = verificar(inst, ler_movimentos(sol), restrito)
    print(("VALIDA, Z = " if ok else "INVALIDA: ") + str(msg))
    sys.exit(0 if ok else 1)