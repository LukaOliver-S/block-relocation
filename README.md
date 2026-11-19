=====================================================================
 Block Relocation Problem - como executar
=====================================================================

ESTRUTURA
---------
include/        headers (.h)
src/            fontes (.cpp)
scripts/        gerar_instancias.py, rodar_experimentos.py, json2dat.py
instancias/
  A/            conjunto pequeno (W=3..5, H=4..5, N<=20), gerado por script
  caserta/      instancias da literatura (Caserta, Voss & Sniedovich, 2011)
  brp_instances/instances/   instancias da disciplina (17 arquivos .json,
                10 instancias cada, ver LEIAME.md)
  brp_txt/      as mesmas instancias em .txt (170 arquivos), geradas por
                scripts/json2dat.py
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

2.1) CONVERTER AS INSTANCIAS DA DISCIPLINA (JSON -> TXT)
--------------------------------------------------------
O programa le .txt, nao .json. Para usar as instancias de
instancias/brp_instances/instances/ (brp_W{W}_H{H}_N{N}.json):

  python scripts/json2dat.py instancias/brp_instances/instances instancias/brp_txt

Gera 1 arquivo por instancia: instancias/brp_txt/brp_W3_H4_N8_id1.txt
(o sufixo _idK e o id da instancia dentro do JSON, de 1 a 10). O
cabecalho "W H N" vem do metadata do JSON, entao rode sempre com
-maxHeight file:

  .\brp.exe -i instancias\brp_txt\brp_W3_H4_N8_id1.txt -m LA-1 -maxHeight file

Atencao: essas instancias sao do BRP RESTRITO (so se relocam os
containers acima do alvo). Hoje so o LA-1 respeita essa regra; os demais
metodos (DFBB, RS, PM, SM, SmSEQ, GLAH) ainda podem fazer movimentos
voluntarios e nao sao comparaveis com as referencias.

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
(colunas: conjunto, instancia, W, H, N, metodo, relocacoes, tempo_s, status;
 status = ok | timeout | erro(<codigo>)).
As sequencias de movimentos ficam em resultados/solucoes/.

5) OBTER O PASSO A PASSO QUE O ALGORITMO FEZ
--------------------------------------------
Qualquer metodo (-m RS-5, PM-3, LA-1, DFBB, ...) registra todas as operacoes
que realizou. Para ve-las:

  Terminal:   .\brp.exe -i instancias\caserta\data3-3-1.txt -m RS-5 -maxHeight file -v
  Arquivo:    .\brp.exe -i instancias\caserta\data3-3-1.txt -m RS-5 -maxHeight file -sf passos.txt

Com -v a saida e, por exemplo:
      Relocate from 1 to 2   (1)
      Retrieve from 1        (3)
Com -sf o arquivo traz a instancia e a sequencia completa:
      retrieving 1 from 0       (0)
      relocating x from 1 to 2  (1)

Pilhas sao numeradas a partir de 0. "Relocate" e uma realocacao (conta no Z);
"Retrieve" e a saida do container (nao conta). O numero entre parenteses e a
posicao da operacao na sequencia.
O runner (scripts/rodar_experimentos.py) ja passa -sf a cada execucao e grava
os passos em resultados/solucoes/<metodo>/<conjunto>_<instancia>.txt.

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

=====================================================================
 PLANO DE TRABALHO (o que falta fazer e como)
=====================================================================
Objetivo do estudo (para os resultados serem comparaveis entre equipes):
- Instancias: (A) conjunto pequeno (W=3..5, H=4..5, N<=20) com otimos
  obtidos pelo A*; (B) instancias da literatura (Caserta, Voss &
  Sniedovich, 2011), em instancias/caserta/.
- Baselines: Min-Max (Caserta et al., 2012) e A* com h(n) = numero de
  bloqueadores. Alem de rake search e pilot method.
- Metricas: numero de reshuffles (= realocacoes, nRelocations()),
  gap = (Z - Z*) / Z*  em relacao ao otimo (A) ou ao melhor valor conhecido
  (B), e tempo de execucao.
- Regras: mesmo limite de tempo por instancia; metodos aleatorios com
  varias sementes (media e melhor); registrar os passos de cada solucao
  (ver secao 5).

ETAPA 0 - FEITO
  Compila, le o formato "W H N", gera o conjunto A, roda RS-N e PM-N em A e
  B e grava os passos (-sf). Esses resultados sao do problema IRRESTRITO.

ETAPA 1 - Definir o problema (decisao da equipe, antes de implementar)
  Restrito (so se pode realocar o topo da pilha que contem o proximo
  container a sair) ou irrestrito? A lista do estudo pede o restrito.
  Registrar a decisao aqui e usar a mesma em todos os metodos. H = a
  capacidade fixa dada no cabecalho da instancia (-maxHeight file).

ETAPA 2 - Min-Max (baseline)
  Como: a politica base BRPPolicy (src/brppolicy.cpp) ja so realoca o topo
  da pilha do alvo e escolhe o destino pela regra descrita em D). Basta
  expor um nome em src/genpolicy.cpp, por exemplo:
      } else if (name == "MM") {
          return make_unique<BRPPolicy>();
  Depois: -m MM. Conferir no artigo de Caserta et al. (2012) a regra e o
  desempate (aqui, a pilha de menor indice) e ajustar se diferir.

ETAPA 3 - A* restrito (baseline e fonte dos otimos do conjunto A)
  Como: novo metodo em src/astar.cpp + include/astar.h, herdando de
  BRPPolicy (solve() devolve shared_ptr<BRPState>) e registrado em
  genpolicy.cpp (ex.: "ASTAR").
  - No: configuracao das pilhas apos as recuperacoes automaticas; g = numero
    de realocacoes (nRelocations()); h = LB1() (bloqueadores, admissivel).
  - Sucessores: o topo da pilha do alvo vai para cada outra pilha com
    altura < H (no maximo W-1 filhos); depois retrieveNext() em laco.
  - Fila de prioridade por f = g + h (desempate: maior g) e tabela hash de
    estados visitados (as pilhas podem ser ordenadas para a chave).
  - Base de partida: src/branchandbound.cpp (fila, expansao, poda).
  - Limite de tempo proprio (o repositorio so tem -tl nos B&B).
  - Os passos da solucao saem de graca em -v / -sf.

ETAPA 4 - Otimos do conjunto A
  Rodar o A* em todas as instancias de A; guardar Z* em
  resultados/otimos_A.csv (instancia, Z*, tempo). Instancias que o A* nao
  resolver no tempo ficam fora do conjunto A (ou marcadas como "sem otimo").
  Sanidade: o DFBB (irrestrito) deve dar Z <= Z* restrito.

ETAPA 5 - Rake search e pilot method restritos
  Hoje geram movimentos de qualquer pilha. Para o restrito:
  - src/rakesearch.cpp, genSuccMoves(): so movimentos com origem em
    stackForItem(next()).
  - src/pilotmethod.cpp, genSuccMoves(): idem; e nao usar voluntaryMoves()
    (herdado de LA_N) no passo seguinte ao relocate.
  - As heuristicas que completam a solucao (FM -> SM-1/2, SmSEQ-1/2) tambem
    usam movimentos voluntarios; ler src/safemoves.cpp e src/subsequence.cpp
    e limita-las, ou trocar por Min-Max (ETAPA 2) como completador.
  Um sinalizador (ex.: -restrito) evita duplicar o codigo.

ETAPA 6 - Executar tudo
  Em scripts/rodar_experimentos.py: METODOS = ["MM", "ASTAR", "RS-5",
  "PM-3"], mesmo TIMEOUT para todos, MAX_N conforme a capacidade do A*.
  RS, PM, MM e A* sao deterministicos (sem sementes). Se algum colega
  incluir metodo aleatorio: varias sementes, reportar media e melhor.

ETAPA 7 - Metricas e relatorio
  - Gap = (Z - Z*) / Z*. Se Z* = 0, o gap e indefinido: reportar 0 quando
    Z = 0 (e o valor absoluto caso contrario) e dizer isso no relatorio.
  - Conjunto B: Z* so existe para as instancias pequenas; para as demais,
    usar o melhor valor conhecido (menor Z entre todos os metodos ou os
    valores publicados na pagina da Univ. de Viena).
  - Medias por classe (W, H). Figuras em graficos/.

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
