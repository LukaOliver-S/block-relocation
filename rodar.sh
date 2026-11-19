#!/usr/bin/env bash
# Compila (se algum .cpp/.h mudou desde o ultimo build) e roda o brp.
# Uso: ./rodar.sh -i instancias/brp_txt/brp_W3_H4_N8_id1.txt -m LA-1 -maxHeight file
set -e
cd "$(dirname "$0")"
EXE=brp.exe
if [ ! -f "$EXE" ] || [ -n "$(find src include \( -name '*.cpp' -o -name '*.h' \) -newer "$EXE" -print -quit)" ]; then
  echo ">> compilando..."
  g++ -std=c++14 -O3 -static -Wall -pedantic -Wno-sign-compare -Wno-unused -Iinclude src/*.cpp -o "$EXE"
fi
./"$EXE" "$@"
