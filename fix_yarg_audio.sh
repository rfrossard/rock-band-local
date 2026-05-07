#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
SONGS_DIR="$BASE_DIR/songs"

echo "Base:  $BASE_DIR"
echo "Songs: $SONGS_DIR"
echo

if [ "$#" -lt 1 ]; then
  echo "Uso:"
  echo "  ./fix_yarg_audio.sh \"Nome da pasta da música\""
  echo "Exemplo:"
  echo "  ./fix_yarg_audio.sh \"Roxette - Almost Unreal\""
  echo "  ./fix_yarg_audio.sh \"Dressed For Success\""
  exit 1
fi

SONG_NAME="$1"
SONG_DIR="$SONGS_DIR/$SONG_NAME"

echo "Pasta da música no YARG:"
echo "  $SONG_DIR"
echo

if [ ! -d "$SONG_DIR" ]; then
  echo "Erro: pasta não encontrada:"
  echo "  $SONG_DIR"
  exit 1
fi

OGG_IN="$SONG_DIR/song.ogg"
OGG_BAK="$SONG_DIR/song_backup.ogg"
OGG_OUT="$SONG_DIR/song.ogg"

if [ ! -f "$OGG_IN" ]; then
  echo "  ! Aviso: não encontrei $OGG_IN."
  echo "    Verifique se a conversão gerou o song.ogg corretamente."
  exit 1
fi

echo "== 1) Formato ATUAL do song.ogg =="
ffprobe -hide_banner "$OGG_IN" || {
  echo "  ! ffprobe falhou ao ler o song.ogg. Abortando."
  exit 1
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
  exit 1
else
  echo "  > Reencode concluído. Arquivo original mantido como song_backup.ogg"
fi

echo
echo "== 3) Formato NOVO do song.ogg =="
ffprobe -hide_banner "$OGG_OUT" || {
  echo "  ! ffprobe falhou ao ler o song.ogg reencodado."
}

echo
echo "Áudio ajustado para:"
echo "  $SONG_DIR"
echo "Agora faça Scan Songs no YARG e teste essa música."
