#!/usr/bin/env bash
set -euo pipefail

echo "===== INÍCIO: process_rb3_full_debug.sh ====="
echo

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
QUARANTINE_DIR="$BASE_DIR/songs_invalid_mogg_quarantine_2026-04-26"
SONGS_DIR="$BASE_DIR/songs"
ONYX_CLI="$BASE_DIR/onyx-cli"

echo "[DEBUG] BASE_DIR       = $BASE_DIR"
echo "[DEBUG] QUARANTINE_DIR = $QUARANTINE_DIR"
echo "[DEBUG] SONGS_DIR      = $SONGS_DIR"
echo "[DEBUG] ONYX_CLI       = $ONYX_CLI"
echo

if [ "$#" -lt 1 ]; then
  echo "[ERRO] Uso incorreto."
  echo "      ./process_rb3_full_debug.sh \"Nome do arquivo rb3con\""
  echo "Exemplo:"
  echo "      ./process_rb3_full_debug.sh \"Almost Unreal_rb3con\""
  echo "      ./process_rb3_full_debug.sh \"Dressed For Success_rb3con\""
  exit 1
fi

RB3_NAME="$1"
echo "[DEBUG] RB3_NAME       = $RB3_NAME"

SONG_NAME="$(echo "$RB3_NAME" | sed 's/_rb3con.*//')"
echo "[DEBUG] SONG_NAME      = $SONG_NAME"
echo

if [ ! -x "$ONYX_CLI" ]; then
  echo "[ERRO] onyx-cli não encontrado ou sem execução:"
  echo "       $ONYX_CLI"
  exit 1
fi

if [ ! -d "$QUARANTINE_DIR" ]; then
  echo "[ERRO] QUARANTINE_DIR não existe:"
  echo "       $QUARANTINE_DIR"
  exit 1
fi

echo "[DEBUG] Conteúdo de QUARANTINE_DIR:"
ls -lah "$QUARANTINE_DIR" || echo "[WARN] Falha ao listar QUARANTINE_DIR"
echo

RB3_FILE="$QUARANTINE_DIR/$RB3_NAME"
if [ ! -f "$RB3_FILE" ]; then
  echo "[ERRO] Arquivo rb3con não encontrado:"
  echo "       $RB3_FILE"
  exit 1
fi
echo "[DEBUG] RB3_FILE       = $RB3_FILE"
echo

EXTRACT_DIR="$BASE_DIR/_rb3_extract_$SONG_NAME"
echo "[DEBUG] EXTRACT_DIR    = $EXTRACT_DIR"
rm -rf "$EXTRACT_DIR"
mkdir -p "$EXTRACT_DIR"

echo "== [ONYX] extract RB3CON → pasta =="
"$ONYX_CLI" extract "$RB3_FILE" --to "$EXTRACT_DIR"
EXTRACT_STATUS=$?
echo "[DEBUG] onyx extract exit code = $EXTRACT_STATUS"
if [ $EXTRACT_STATUS -ne 0 ]; then
  echo "[ERRO] onyx extract falhou. Veja mensagens acima."
  exit 1
fi

echo
echo "[DEBUG] Conteúdo de EXTRACT_DIR:"
ls -R "$EXTRACT_DIR" || echo "[WARN] Falha ao listar EXTRACT_DIR"
echo

SONGS_SUBDIR="$EXTRACT_DIR/songs"
if [ ! -d "$SONGS_SUBDIR" ]; then
  echo "[ERRO] Pasta 'songs' não encontrada em EXTRACT_DIR:"
  echo "       $SONGS_SUBDIR"
  exit 1
fi

# 1) Encontrar a primeira subpasta de música dentro de songs/
MUSIC_DIR=""
while IFS= read -r -d '' d; do
  MUSIC_DIR="$d"
  break
done < <(find "$SONGS_SUBDIR" -mindepth 1 -maxdepth 1 -type d -print0)

if [ -z "$MUSIC_DIR" ]; then
  echo "[ERRO] Nenhuma subpasta de música encontrada em:"
  echo "       $SONGS_SUBDIR"
  exit 1
fi

echo "[DEBUG] MUSIC_DIR      = $MUSIC_DIR"
echo

# 2) Encontrar o primeiro .mogg em MUSIC_DIR
MOGG_IN=""
while IFS= read -r -d '' f; do
  MOGG_IN="$f"
  break
done < <(find "$MUSIC_DIR" -maxdepth 1 -type f -name '*.mogg' -print0)

if [ -z "$MOGG_IN" ]; then
  echo "[ERRO] Nenhum arquivo .mogg encontrado em MUSIC_DIR:"
  echo "       $MUSIC_DIR"
  exit 1
fi

echo "[DEBUG] MOGG_IN        = $MOGG_IN"

# 3) Encontrar o primeiro .mid em MUSIC_DIR (se existir)
MID_IN=""
while IFS= read -r -d '' f; do
  MID_IN="$f"
  break
done < <(find "$MUSIC_DIR" -maxdepth 1 -type f -name '*.mid' -print0)

if [ -n "$MID_IN" ]; then
  echo "[DEBUG] MID_IN         = $MID_IN"
else
  echo "[WARN] Nenhum .mid encontrado em MUSIC_DIR."
fi
echo

# 4) Desencriptar MOGG → OGG bruto
OGG_RAW="$MUSIC_DIR/song_raw.ogg"
echo "== [ONYX] unwrap MOGG → OGG =="
"$ONYX_CLI" unwrap "$MOGG_IN" --to "$OGG_RAW"
UNWRAP_STATUS=$?
echo "[DEBUG] onyx unwrap exit code = $UNWRAP_STATUS"
if [ $UNWRAP_STATUS -ne 0 ]; then
  echo "[ERRO] onyx unwrap falhou. Veja mensagens acima."
  exit 1
fi

if [ ! -f "$OGG_RAW" ]; then
  echo "[ERRO] OGG_RAW não foi gerado:"
  echo "       $OGG_RAW"
  exit 1
fi

echo
echo "== [AUDIO] Formato OGG_RAW =="
ffprobe -hide_banner "$OGG_RAW" || echo "[WARN] ffprobe falhou em OGG_RAW"
echo

# 5) Reencodar OGG_RAW → song.ogg (44100 Hz, stereo)
OGG_OUT="$MUSIC_DIR/song.ogg"
echo "== [AUDIO] Reencodando para 44100 Hz, stereo =="

ffmpeg -y -i "$OGG_RAW" \
  -ar 44100 -ac 2 \
  "$OGG_OUT"

FFMPEG_STATUS=$?
echo "[DEBUG] ffmpeg exit code = $FFMPEG_STATUS"
if [ $FFMPEG_STATUS -ne 0 ]; then
  echo "[ERRO] ffmpeg falhou ao reencodar."
  exit 1
fi

echo
echo "== [AUDIO] Formato FINAL de song.ogg =="
ffprobe -hide_banner "$OGG_OUT" || echo "[WARN] ffprobe falhou em song.ogg"
echo

# 6) Preparar pasta final em songs/ para o YARG
FINAL_DIR="$SONGS_DIR/$SONG_NAME"
echo "[DEBUG] FINAL_DIR      = $FINAL_DIR"
echo "== [FILES] Preparando pasta final em songs/ =="

if [ -d "$FINAL_DIR" ]; then
  BACKUP_DIR="${FINAL_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
  echo "[DEBUG] Já existe FINAL_DIR, movendo para backup:"
  echo "        $BACKUP_DIR"
  mv "$FINAL_DIR" "$BACKUP_DIR"
fi

mkdir -p "$FINAL_DIR"

cp "$OGG_OUT" "$FINAL_DIR/song.ogg"

if [ -n "$MID_IN" ] && [ -f "$MID_IN" ]; then
  cp "$MID_IN" "$FINAL_DIR/notes.mid"
  echo "[DEBUG] notes.mid copiado."
else
  echo "[WARN] notes.mid não disponível; FINAL_DIR ficará sem MIDI até você copiar."
fi

INI_PATH="$FINAL_DIR/song.ini"
cat > "$INI_PATH" << EOF_INI
[song]
name = $SONG_NAME
artist = Imported from RB3
album = Unknown Album
genre = rock
year = 2000
charter = RB3 Import
EOF_INI
echo "[DEBUG] song.ini gerado em:"
echo "        $INI_PATH"

EXTRAS_DIR="$FINAL_DIR/_extras"
mkdir -p "$EXTRAS_DIR"

echo
echo "[DEBUG] Movendo arquivos extras de EXTRACT_DIR para _extras..."
find "$EXTRACT_DIR" -type f ! -name "song.ogg" ! -name "song_raw.ogg" \
  ! -name "notes.mid" ! -name "song.ini" \
  -print0 | while IFS= read -r -d '' f; do
    BASENAME="$(basename "$f")"
    echo "  [MOVE] $BASENAME → _extras"
    mv "$f" "$EXTRAS_DIR/"
  done

echo
echo "[DEBUG] Conteúdo final de FINAL_DIR:"
ls -lah "$FINAL_DIR"
echo
echo "[DEBUG] Conteúdo de FINAL_DIR/_extras:"
ls -lah "$EXTRAS_DIR" || echo "[WARN] _extras vazio ou não acessível"
echo

echo "===== FIM: process_rb3_full_debug.sh ====="
echo "Pasta pronta para o YARG:"
echo "  $FINAL_DIR"
echo
echo "Agora faça Scan Songs no YARG e teste essa música."
