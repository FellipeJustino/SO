#!/usr/bin/env bash
# Benchmark de gravacao de UMA particao por rodada.
# Cenario 1 = pasta "grande" (zips de 1 GB); cenario 2 = pasta "pequeno" (txt de ~1 KB).
# Para cada repeticao, cada arquivo e copiado para a particao, com cp + sync cronometrados.
# Os arquivos de teste sao apagados ao fim de cada repeticao.
#
# Uso:  bash benchmark_cluster.sh <ponto_montagem> <participante> <descricao_run>
# Ex.:  bash benchmark_cluster.sh /media/felps/fat32 A fat32_cluster_max
# Saida: Média_Tempo/<descricao_run>/
set -u

REPS="${REPS:-10}"
TRABALHO="${TRABALHO:-/home/felps/Documentos/Faculdade/6° Período/Sistemas Operacionais/Trabalho}"
SAIDA="${SAIDA:-$TRABALHO/Média_Tempo}"
TESTE="${TESTE:-0}"   # 1 = modo de teste (nao exige ponto de montagem real)
CENARIOS=("grande" "pequeno")

if [ $# -ne 3 ]; then
  echo "Uso: $0 <ponto_montagem> <participante> <descricao_run>"
  exit 1
fi
MONTAGEM="$1"
P="$2"
RUN="$3"

if [ "$TESTE" != 1 ] && ! mountpoint -q "$MONTAGEM"; then
  echo "ERRO: $MONTAGEM nao esta montado"; exit 1
fi
if [ ! -d "$MONTAGEM" ] || [ ! -w "$MONTAGEM" ]; then
  echo "ERRO: sem permissao de escrita em $MONTAGEM"; exit 1
fi
echo "Participante $P -> $MONTAGEM ($(findmnt -rno FSTYPE --target "$MONTAGEM" 2>/dev/null || echo '?')) | rodada: $RUN"

for c in "${CENARIOS[@]}"; do
  if [ ! -d "$TRABALHO/$c" ]; then
    echo "ERRO: pasta de origem ausente: $TRABALHO/$c"; exit 1
  fi
done

DIR="$SAIDA/$RUN"
mkdir -p "$DIR" || { echo "ERRO: nao foi possivel criar $DIR"; exit 1; }
RAW="$DIR/tempos_brutos.csv"
echo "participante;cenario;repeticao;arquivo;tempo_us" > "$RAW"

destino="$MONTAGEM/teste_bench_$P"
# Remove a pasta de teste mesmo se o script parar por erro ou interrupcao
trap 'rm -rf -- "$destino"' EXIT

for rep in $(seq 1 "$REPS"); do
  mkdir -p "$destino" || { echo "ERRO: nao foi possivel criar $destino"; exit 1; }

  for c in "${CENARIOS[@]}"; do
    while IFS= read -r -d '' f; do
      nome="$(basename "$f")"
      t0=$(date +%s%N)
      if ! cp -- "$f" "$destino/$nome"; then
        echo "ERRO: falha ao copiar '$nome' (repeticao $rep, cenario $c). Teste interrompido."
        exit 1
      fi
      if ! sync -f "$destino/$nome"; then
        echo "ERRO: falha no sync de '$nome' (repeticao $rep). Teste interrompido."
        exit 1
      fi
      t1=$(date +%s%N)
      tam_origem=$(stat -c %s "$f")
      tam_copia=$(stat -c %s "$destino/$nome" 2>/dev/null || echo -1)
      if [ "$tam_origem" != "$tam_copia" ]; then
        echo "ERRO: tamanho diferente em '$nome' (origem $tam_origem, copia $tam_copia). Teste interrompido."
        exit 1
      fi
      echo "$P;$c;$rep;$nome;$(( (t1 - t0) / 1000 ))" >> "$RAW"
    done < <(find "$TRABALHO/$c" -maxdepth 1 -type f -print0 | sort -z)
    echo "[rep $rep/$REPS] cenario $c concluido"
  done

  rm -rf -- "$destino"
done

MEDIAS="$DIR/medias_por_arquivo.csv"
RESUMO="$DIR/resumo_por_cenario.csv"

awk -F';' 'NR>1 {
  k=$1";"$2";"$4; soma[k]+=$5; n[k]++
} END {
  for (k in soma) printf "%s;%d;%.3f\n", k, n[k], soma[k]/n[k]/1000
}' "$RAW" | sort -t';' -k1,1 -k2,2 -k3,3V | { echo "participante;cenario;arquivo;repeticoes;media_ms"; cat; } > "$MEDIAS"

awk -F';' 'NR>1 {
  k=$1";"$2; soma[k]+=$5; n[k]++
} END {
  for (k in soma) printf "%s;%d;%.3f\n", k, n[k], soma[k]/n[k]/1000
}' "$RAW" | sort -t';' -k1,1 -k2,2 | { echo "participante;cenario;arquivos_medidos;media_ms_por_arquivo"; cat; } > "$RESUMO"

echo "Concluido. Resultados em: $DIR"
echo "  - $RAW"
echo "  - $MEDIAS"
echo "  - $RESUMO"
