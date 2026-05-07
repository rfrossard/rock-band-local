#!/usr/bin/env bash
set -euo pipefail

# Diretório base (projeto atual)
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
SONGS_DIR="$BASE_DIR/songs"

echo "Base:  $BASE_DIR"
echo "Songs: $SONGS_DIR"
echo

shopt -s nullglob

# Se for passado um argumento, processa só a pasta de música indicada;
# caso contrário, processa TODAS as pastas dentro de songs/.
if [ "$#" -ge 1 ]; then
  TARGET_DIRS=( "$SONGS_DIR/$1" )
else
  TARGET_DIRS=( "$SONGS_DIR"/* )
fi

if [ "${#TARGET_DIRS[@]}" -eq 0 ]; then
  echo "Nenhuma pasta de música encontrada em $SONGS_DIR."
  exit 0
fi

for SONG_DIR in "${TARGET_DIRS[@]}"; do
  if [ ! -d "$SONG_DIR" ]; then
    echo "  ! Ignorando (não é pasta): $SONG_DIR"
    echo
    continue
  fi

  OGG_IN="$SONG_DIR/song.ogg"
  OGG_BAK="$SONG_DIR/song_backup.ogg"
  OGG_OUT="$SONG_DIR/song.ogg"

  echo "==============================="
  echo "Pasta YARG: $SONG_DIR"

  if [ -f "$OGG_IN" ]; then
    echo "  > Reencodando $OGG_IN para formato compatível com YARG (44100 Hz, stereo)..."
    mv "$OGG_IN" "$OGG_BAK"

    ffmpeg -y -i "$OGG_BAK" \
      -ar 44100 -ac 2 \
      "$OGG_OUT"

    if [ $? -ne 0 ]; then
      echo "  ! Erro ao reencodar OGG, restaurando arquivo original"
      mv "$OGG_BAK" "$OGG_IN"
    else
      echo "  > Reencode concluído. Arquivo original mantido como song_backup.ogg"
    fi
  else
    echo "  ! Aviso: não encontrei $OGG_IN (pode ser chart sem áudio ou conversão ainda não feita)."
  fi

  echo
done

echo "Reencode de áudio concluído."
