#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

QUARANTINE_DIR="$BASE_DIR/songs_invalid_mogg_quarantine_2026-04-26"
SONGS_DIR="$BASE_DIR/songs"

echo "Base:           $BASE_DIR"
echo "Quarantine dir: $QUARANTINE_DIR"
echo "Songs YARG:     $SONGS_DIR"
echo

if [ "$#" -lt 1 ]; then
  echo "Uso:"
  echo "  ./process_quarantine_song.sh \"Nome da pasta ou arquivo base\""
  echo "Exemplo (pasta):"
  echo "  ./process_quarantine_song.sh \"Dressed For Success\""
  echo "Exemplo (arquivo rb3con):"
  echo "  ./process_quarantine_song.sh \"Dressed For Success_rb3con\""
  exit 1
fi

INPUT_NAME="$1"

# Se o usuário passar "Dressed For Success_rb3con", o nome "bonito" vira "Dressed For Success"
SONG_NAME="$(echo "$INPUT_NAME" | sed 's/_rb3con.*//')"

SRC_DIR="$QUARANTINE_DIR/$SONG_NAME"
FINAL_DIR="$SONGS_DIR/$SONG_NAME"

echo "Nome da música (bonito): $SONG_NAME"
echo "Pasta origem/quarentena: $SRC_DIR"
echo "Pasta final YARG:        $FINAL_DIR"
echo

if [ ! -d "$SRC_DIR" ]; then
  echo "Erro: pasta de origem não encontrada:"
  echo "  $SRC_DIR"
  echo "Certifique-se de que a pasta existe em:"
  echo "  $QUARANTINE_DIR"
  exit 1
fi

mkdir -p "$SONGS_DIR"

OGG_IN="$SRC_DIR/song.ogg"
OGG_BAK="$SRC_DIR/song_backup.ogg"
OGG_OUT="$SRC_DIR/song.ogg"

if [ ! -f "$OGG_IN" ]; then
  echo "  ! Aviso: não encontrei $OGG_IN na pasta de origem."
  echo "    Verifique se a conversão com Onyx gerou o áudio."
else
  echo "== 1) Formato ATUAL do song.ogg =="
  ffprobe -hide_banner "$OGG_IN" || {
    echo "  ! ffprobe falhou ao ler o song.ogg. Mantendo arquivo como está."
  }

  echo
  echo "== 2) Reencodando para 44100 Hz, stereo =="

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
    echo "== 3) Formato NOVO do song.ogg =="
    ffprobe -hide_banner "$OGG_OUT" || {
      echo "  ! ffprobe falhou ao ler o song.ogg reencodado."
    }
  fi
fi

echo
echo "== 4) Movendo pasta final para songs/ do YARG =="

if [ -d "$FINAL_DIR" ]; then
  BACKUP_DIR="${FINAL_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
  echo "  > Já existe $FINAL_DIR, movendo para backup:"
  echo "    $BACKUP_DIR"
  mv "$FINAL_DIR" "$BACKUP_DIR"
fi

mkdir -p "$(dirname "$FINAL_DIR")"
mv "$SRC_DIR" "$FINAL_DIR"

echo
echo "Pasta pronta para o YARG:"
echo "  $FINAL_DIR"
echo
echo "Agora vá no YARG → Settings → Songs → Scan Songs e teste essa música."
