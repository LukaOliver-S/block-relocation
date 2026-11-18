=====================================================================
 Block Relocation Problem - como executar
=====================================================================

ESTRUTURA
---------
include/        headers (.h)
src/            fontes (.cpp)
scripts/        gerar_instancias.py, rodar_experimentos.py
instancias/
  A/            conjunto pequeno (W=3..5, H=4..5, N<=20), gerado por script
  caserta/      instancias da literatura (Caserta, Voss & Sniedovich, 2011)
  _obsoleto/    arquivos antigos, pode ser apagado
resultados/     CSVs gerados pelo runner
graficos/       figuras

REQUISITOS
----------
- g++ com suporte a C++14 (no Windows: MSYS2/MinGW)
- Python 3

1) COMPILAR  (rodar na raiz do projeto, onde esta este README)
---------------------------------------------------------------
PowerShell (nao precisa de make):

  g++ -std=c++14 -O3 -Wall -pedantic -Wno-sign-compare -Wno-unused -Iinclude (Get-ChildItem src\*.cpp).FullName -o brp.exe

Git Bash / MSYS2 / Linux:

  g++ -std=c++14 -O3 -Wall -pedantic -Wno-sign-compare -Wno-unused -Iinclude src/*.cpp -o brp.exe

Ou, se o make estiver instalado:  make   (gera ./brp)

2) GERAR O CONJUNTO A
---------------------
  python scripts/gerar_instancias.py

Cria instancias/A/*.txt (e instancias/A_pequenas.json).

3) RODAR UMA INSTANCIA
----------------------
  PowerShell:   .\brp.exe -i instancias\caserta\data3-3-1.txt -m RS-5 -maxHeight file
  Bash/Linux:   ./brp.exe -i instancias/caserta/data3-3-1.txt -m RS-5 -maxHeight file

A linha de interesse na saida e:   RS-5  used 6 relocations in 0.002 s
(para data3-3-1, RS-5 e PM-3 devem dar 6).

Outros exemplos:
  -m PM-3          pilot method (largura 3)
  -m DFBB          branch-and-bound exato (problema irrestrito)
  -v               mostra a solucao passo a passo
  -sf saida.txt    grava a solucao em arquivo

4) RODAR TODAS AS INSTANCIAS (A e B) E GERAR O CSV
--------------------------------------------------
  python scripts/rodar_experimentos.py

Pode ser executado de qualquer pasta. Configuracao no topo do script:
METODOS (ex.: ["RS-5", "PM-3"]), TIMEOUT (s por instancia) e MAX_N
(ignora instancias com mais de MAX_N containers).
Saida: resultados/resultados_irrestrito.csv
(colunas: conjunto, instancia, W, H, N, metodo, relocacoes, tempo_s, status,
 valida_irrestrita, valida_restrita, z_confere;
 status = ok | timeout | erro(<codigo>)).
As sequencias de movimentos ficam em resultados/solucoes/.

5) VERIFICAR UMA SOLUCAO
------------------------
O runner passa "-sf" ao brp.exe: cada execucao grava a sequencia de
movimentos em resultados/solucoes/<metodo>/<conjunto>_<instancia>.txt e o
script scripts/verificar.py simula essa sequencia na instancia (respeitando H,
recuperando os containers em ordem e exigindo que a baia termine vazia).
Isoladamente:

  python scripts/verificar.py instancias/caserta/data3-3-1.txt <solucao.txt>
  python scripts/verificar.py instancias/caserta/data3-3-1.txt <solucao.txt> --restrito

Saida: "VALIDA, Z = <n>" ou "INVALIDA: <motivo>". Com --restrito so e aceito
mover o topo da pilha que contem o proximo container a sair. No CSV:
valida_irrestrita, valida_restrita e z_confere (Z reportado = movimentos).

=====================================================================
 O QUE O CODIGO JA OFERECE (inventario para quem vai implementar)
=====================================================================
(Baseado na leitura de main, brpstate, brppolicy, safemoves, petering,
 fastmeta, rakesearch, pilotmethod, dfbb, branchandbound, genpolicy e dos
 headers de subsequence e glah. Os corpos de subsequence.cpp e glah.cpp
 NAO foram lidos.)

A) Gravacao e leitura de movimentos
- BRPState guarda cada operacao em operations_, na ordem em que ocorreu:
  (a, b) com a != b = realocacao da pilha a para a pilha b;
  (a, a) = recuperacao. Pilhas numeradas a partir de 0.
- "-v" imprime a solucao passo a passo no terminal.
- "-sf <arquivo>" grava a instancia e a sequencia completa, por exemplo:
      retrieving 1 from 0      (0)
      relocating x from 1 to 2 (1)
  Funciona para qualquer metodo: o historico viaja com o estado.
- undoLastMove() desfaz a ultima operacao usando esse historico (e o que
  permite ao DFBB fazer busca em profundidade sem copiar estados).
- nRelocations() conta SO realocacoes (sem recuperacoes): e exatamente a
  metrica "reshuffles" do estudo.

B) A classe BRPState (o estado da baia)
- Operacoes: relocate(de, para), retrieveNext(), undoLastMove(), empty().
- Consultas: top(s), height(s), low(s) (menor prioridade na pilha),
  stackForItem(i), next() (proximo alvo), W(), H(), n().
- Auxiliares: necessaryRelocates(), safeRelocates(), safe2Relocates(),
  bestSafeRelocate(), dominates(), condenseJin(), condenseTricoire().

C) Cotas inferiores (uteis para o A*)
- LB1() = numero de blocos acima de algum bloco de prioridade menor
  (bloqueadores). Mantida incrementalmente, custo O(1). E exatamente o h(n)
  pedido para o A* baseline e e admissivel.
- LB2() e LB3() sao mais fortes e mais caras. Valem para o problema
  irrestrito e, portanto, tambem para o restrito (as solucoes restritas
  sao um subconjunto das irrestritas).

D) Arcabouco de politicas (BRPPolicy)
- solve(): se o alvo esta no topo, recupera; senao tenta voluntaryMoves();
  se nao houver, faz forcedMove() (realoca o que bloqueia o alvo).
- Novas heuristicas herdam de BRPPolicy e reimplementam essas funcoes.
- A politica base, SEM voluntaryMoves, so realoca o topo da pilha do alvo:
  resolve o problema RESTRITO. Sua regra de destino
  (bestDestForLaRelocate) escolhe a pilha cujo minimo e maior que o
  container (o menor desses minimos) e, se nenhuma serve, a de maior
  minimo. Em essencia e a regra Min-Max (confirmar o desempate no artigo
  de Caserta et al., 2012). Falta apenas expor um nome na CLI em
  genpolicy.cpp (ex.: "MM" -> make_unique<BRPPolicy>()).

E) Algoritmos implementados  (-m <nome>)
  LA-N               Petering (lookahead)            irrestrito
  SM-1, SM-2         safe moves                      irrestrito
  SSEQ, SmSEQ-1/2    subsequencias                   (nao lido)
  FM                 melhor entre SM1,SM2,SmSEQ1/2   irrestrito
  JZW, ZHU           Jin et al. / Zhu                (nao lido)
  GLAH-N             Jin et al.                      (nao lido)
  RS-N               rake search                     irrestrito
  PM-N               pilot method                    irrestrito
  BB, DFBB, DFBB-L   branch-and-bound exatos         irrestrito (otimo)

F) Pecas reaproveitaveis para o A*
- BranchAndBound: esqueleto de fila/expansao/poda por reloc + LB; trocar a
  fila por prioridade em f = g + h.
- RakeSearch::updateQueue e BRPState::dominates(): eliminacao de estados
  repetidos (por varredura linear; um A* precisa de tabela hash).
- DFBB-L: aprofundamento no custo; serve como checagem cruzada. Atencao:
  o valor dele e do problema IRRESTRITO (<= otimo restrito).

G) Limitacoes e armadilhas
- Quase tudo e IRRESTRITO: RS, PM, DFBB etc. nao medem o mesmo problema que
  Min-Max e A* restritos. A adaptacao ao restrito ainda nao foi feita.
- Sem limite de tempo interno, exceto "-tl" nos branch-and-bound (o runner
  usa timeout externo).
- Deterministico: srandom(0) fixo e nenhum uso ativo de aleatoriedade
  (o random_shuffle do pilot method esta comentado). A regra de "varias
  sementes" nao se aplica a RS/PM como estao.
- Portabilidade Windows: min<size_t> em glah.cpp e srandom -> srand em
  main.cpp.
- LA_N::voluntaryMoves pode entrar em laco se todas as pilhas ficarem
  cheias (nao ocorreu nas 120 instancias do conjunto A).
- Pequenos defeitos sem efeito no que usamos: no DFBB a quebra de simetria
  "relocatedToEmpty" nunca e ativada; operator== de BRPState usa "<".

FORMATO DAS INSTANCIAS
----------------------
Linha 1:   W H N        (W pilhas, altura maxima H, N containers)
Depois, uma linha por pilha, de baixo para cima:
           h p1 p2 ... ph      (h containers; prioridade 1 sai primeiro)

O cabecalho antigo "W N" (sem H) tambem e aceito, mas nesse caso use
-maxHeight H+2, unlimited ou 2H-1 em vez de "file".

NOTA
----
Os resultados de RS e PM do repositorio original sao do problema
IRRESTRITO (qualquer topo pode ser realocado). Por isso o CSV tem o
sufixo "irrestrito". A versao restrita ainda nao foi adaptada.

=====================================================================
 Parametros da linha de comando (original)
=====================================================================
The code is C++ and follows the C++14 standard. When using the Makefile, the
executable produced is called brp. Useful command line parameters:

-i <filename>:         Specify the input file
-sf <scriptfilename>:  Save the solution to a scriptfile
-v:                    Verbose mode (displays solution; by default, the solution
                       is not displayed)
-maxHeight <arg>:      Specify Hmax. Valid values are H+2, unlimited, 2H-1 and
                       file (use the H given in a "W H N" header).
-m <algorithm>:        Specify which algorithm to use. Valid values are SM-1,
                       SM-2, SmSEQ-1, SmSEQ-2, JZW, LA-S-1, LA-<N>, GLAH-<N>,
                       RS-<N>, PM-<N>, DFBB, DFBB-L. <N> indicates a parameter
                       that is algorithm-specific; for instance to use rake
                       search with a width of 2, use RS-2.
-lb n:                 Lower bound to use in branch-and-bound.
                       Valid values are 1, 2, 3
-ub <algorithm>:       Algorithm to use to compute the initial lower bound for
                       branch-and-bound methods.
-hub <algorithm>:      Algorithm to use as an evaluation subroutine in the
                       pilot method.
-cp <procedure>:       Condensation procedure to use is SmSEQ-N algorithms.
                       Valid values are none, jin, tricoire.
-tl <limit>:           Time limit for branch-and-bound algorithms, in seconds.
