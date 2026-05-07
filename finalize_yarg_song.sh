#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"

WORK_ROOT="$BASE_DIR/_tmp_yarg_convert"
SONGS_DIR="$BASE_DIR/songs"

echo "Base:       $BASE_DIR"
echo "Work root:  $WORK_ROOT"
echo "Songs YARG: $SONGS_DIR"
echo

if [ "$#" -lt 1 ] ; then
  echo "Uso:"
  echo "  ./finalize_yarg_song.sh \"Nome da música\""
  echo "Exemplo:"
  echo "  ./finalize_yarg_song.sh \"Roxette - Almost Unreal\""
  exit 1
fi

SONG_NAME="$1"
WORK_DIR="$WORK_ROOT/$SONG_NAME"
FINAL_DIR="$SONGS_DIR/$SONG_NAME"

echo "Nome da música:    $SONG_NAME"
echo "Pasta de trabalho: $WORK_DIR"
echo "Pasta final YARG:  $FINAL_DIR"
echo

if [ ! -d "$WORK_DIR" ]; then
  echo "Erro: pasta de trabalho não encontrada:"
  echo "  $WORK_DIR"
  echo "Crie essa pasta rodando o Onyx com saída apontando para ela."
  exit 1
fi

mkdir -p "$SONGS_DIR"

OGG_IN="$WORK_DIR/song.ogg"
OGG_BAK="$WORK_DIR/song_backup.ogg"
OGG_OUT="$WORK_DIR/song.ogg"

if [ ! -f "$OGG_IN" ]; then
  echo "  ! Aviso: não encontrei $OGG_IN na pasta de trabalho."
  echo "    Verifique se o Onyx gerou o áudio."
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
mv "$WORK_DIR" "$FINAL_DIR"

echo
echo "Pasta pronta para o YARG:"
echo "  $FINAL_DIR"
echo
echo "Agora vá no YARG → Settings → Songs → Scan Songs e teste essa música."
