#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

# Onde estão os rb3con "problemáticos"
RB3_SRC_DIR="$BASE_DIR/songs_invalid_mogg_quarantine_2026-04-26"

# Onde o YARG lê as músicas
SONGS_DIR="$BASE_DIR/songs"

# Caminho do onyx-cli (ajuste se estiver em outro lugar)
ONYX_CLI="$BASE_DIR/onyx-cli"

if [ ! -x "$ONYX_CLI" ]; then
  echo "Erro: onyx-cli não encontrado ou sem permissão de execução em:"
  echo "  $ONYX_CLI"
  exit 1
fi

if [ "$#" -lt 1 ]; then
  echo "Uso:"
  echo "  ./process_rb3con.sh \"Nome do arquivo .rb3con\""
  echo "Exemplo:"
  echo "  ./process_rb3con.sh \"Dressed For Success_rb3con\""
  exit 1
fi

CON_NAME="$1"
CON_PATH="$RB3_SRC_DIR/$CON_NAME"

if [ ! -f "$CON_PATH" ]; then
  echo "Erro: arquivo .rb3con não encontrado:"
  echo "  $CON_PATH"
  exit 1
fi

echo "Base:        $BASE_DIR"
echo "RB3 fonte:   $RB3_SRC_DIR"
echo "Songs YARG:  $SONGS_DIR"
echo "RB3CON:      $CON_PATH"
echo

# Nome de pasta "bonito" para o YARG, removendo o sufixo interno
# Ex.: 'Roxette - Almost Unreal_rb3con - o515028333_almostunreal_ro' -> 'Roxette - Almost Unreal'
SONG_NAME="$(echo "$CON_NAME" | sed 's/_rb3con.*//')"
WORK_DIR="$BASE_DIR/_tmp_yarg_convert/$SONG_NAME"
FINAL_DIR="$SONGS_DIR/$SONG_NAME"

echo "Nome da música: $SONG_NAME"
echo "Pasta de trabalho: $WORK_DIR"
echo "Pasta final YARG:  $FINAL_DIR"
echo

mkdir -p "$WORK_DIR"
mkdir -p "$SONGS_DIR"

echo "== 1) Convertendo RB3CON com Onyx =="
"$ONYX_CLI" \
  song convert \
  --input "$CON_PATH" \
  --output "$WORK_DIR" \
  --format clonehero

echo
echo "Onyx terminou a conversão."
echo

# Esperamos que o Onyx tenha gerado pelo menos:
#  - $WORK_DIR/song.ogg
#  - $WORK_DIR/notes.mid
#  - $WORK_DIR/song.ini (ou equivalente)
OGG_IN="$WORK_DIR/song.ogg"
OGG_BAK="$WORK_DIR/song_backup.ogg"
OGG_OUT="$WORK_DIR/song.ogg"

if [ ! -f "$OGG_IN" ]; then
  echo "  ! Aviso: Onyx não gerou $OGG_IN (pode ser chart sem áudio ou erro na conversão)."
else
  echo "== 2) Testando e ajustando áudio para YARG =="

  echo "  > Formato ATUAL do song.ogg:"
  ffprobe -hide_banner "$OGG_IN" || {
    echo "  ! ffprobe falhou ao ler o song.ogg. Mantendo arquivo como está."
  }

  echo
  echo "  > Reencodando para 44100 Hz, stereo..."
  mv "$OGG_IN" "$OGG_BAK"

  ffmpeg -y -i "$OGG_BAK" \
    -ar 44100 -ac 2 \
    "$OGG_OUT"

  if [ $? -ne 0 ]; then
    echo "  ! Erro ao reencodar OGG, restaurando arquivo original"
    mv "$OGG_BAK" "$OGG_IN"
  else
    echo "  > Reencode concluído. Arquivo original mantido como song_backup.ogg"
    echo
    echo "  > Formato NOVO do song.ogg:"
    ffprobe -hide_banner "$OGG_OUT" || {
      echo "  ! ffprobe falhou ao ler o song.ogg reencodado."
    }
  fi
fi

echo
echo "== 3) Movendo pasta final para songs/ do YARG =="

# Se já existir uma pasta com o mesmo nome em songs/, faz backup
if [ -d "$FINAL_DIR" ]; then
  BACKUP_DIR="${FINAL_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
  echo "  > Já existe $FINAL_DIR, movendo para backup:"
  echo "    $BACKUP_DIR"
  mv "$FINAL_DIR" "$BACKUP_DIR"
fi

mkdir -p "$(dirname "$FINAL_DIR")"
mv "$WORK_DIR" "$FINAL_DIR"

echo
echo "Processo concluído."
echo "Pasta pronta para o YARG:"
echo "  $FINAL_DIR"
echo
echo "Agora vá no YARG → Settings → Songs → Scan Songs e teste essa música."
