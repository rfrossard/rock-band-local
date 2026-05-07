#!/usr/bin/env bash
set -euo pipefail

echo "===== INÍCIO: process_mogg_full_debug.sh ====="
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
  echo "      ./process_mogg_full_debug.sh \"Nome da música\""
  echo "Exemplo:"
  echo "      ./process_mogg_full_debug.sh \"Milk and Toast and Honey\""
  exit 1
fi

SONG_NAME="$1"
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

mkdir -p "$SONGS_DIR"

echo "[DEBUG] Conteúdo de QUARANTINE_DIR:"
ls -lah "$QUARANTINE_DIR" || echo "[WARN] Falha ao listar QUARANTINE_DIR"
echo

# 1) Pasta de origem para a música (onde você coloca o .mogg)
SRC_DIR="$QUARANTINE_DIR/$SONG_NAME"
FINAL_DIR="$SONGS_DIR/$SONG_NAME"

echo "[DEBUG] SRC_DIR   = $SRC_DIR"
echo "[DEBUG] FINAL_DIR = $FINAL_DIR"
echo

if [ ! -d "$SRC_DIR" ]; then
  echo "[ERRO] SRC_DIR não existe:"
  echo "       $SRC_DIR"
  echo
  echo "Crie essa pasta e coloque dentro pelo menos um arquivo .mogg da música."
  echo "Por exemplo:"
  echo "  $QUARANTINE_DIR/$SONG_NAME/song.mogg"
  exit 1
fi

echo "[DEBUG] Conteúdo de SRC_DIR:"
ls -lah "$SRC_DIR" || echo "[WARN] Falha ao listar SRC_DIR"
echo

# 2) Encontrar um arquivo .mogg dentro de SRC_DIR
set +e
MOGG_CANDIDATES=( "$SRC_DIR"/*.mogg )
set -e

if [ ! -f "${MOGG_CANDIDATES[0]}" ]; then
  echo "[ERRO] Nenhum arquivo .mogg encontrado em SRC_DIR."
  echo "       Coloque o .mogg da música nessa pasta e rode novamente."
  exit 1
fi

MOGG_IN="${MOGG_CANDIDATES[0]}"
OGG_RAW="$SRC_DIR/song_raw.ogg"
OGG_IN="$SRC_DIR/song.ogg"
OGG_BAK="$SRC_DIR/song_backup.ogg"
OGG_OUT="$SRC_DIR/song.ogg"

echo "[DEBUG] MOGG_IN  = $MOGG_IN"
echo "[DEBUG] OGG_RAW  = $OGG_RAW"
echo "[DEBUG] OGG_IN   = $OGG_IN"
echo

# 3) Descriptografar/desempacotar MOGG -> OGG com Onyx
echo "== [ONYX] unwrap MOGG → OGG =="
"$ONYX_CLI" unwrap "$MOGG_IN" --to "$OGG_RAW"
ONYX_STATUS=$?
echo "[DEBUG] onyx unwrap exit code = $ONYX_STATUS"

if [ $ONYX_STATUS -ne 0 ]; then
  echo "[ERRO] onyx unwrap falhou. Veja a mensagem acima."
  exit 1
fi

if [ ! -f "$OGG_RAW" ]; then
  echo "[ERRO] OGG_RAW não foi gerado:"
  echo "       $OGG_RAW"
  exit 1
fi

echo
echo "[DEBUG] Formato do OGG_RAW gerado:"
ffprobe -hide_banner "$OGG_RAW" || echo "[WARN] ffprobe falhou em OGG_RAW"
echo

# 4) Reencodar OGG_RAW para 44100 Hz, stereo → song.ogg
echo "== [AUDIO] Reencodando para 44100 Hz, stereo =="

# Se já existir um song.ogg anterior, guarda como backup
if [ -f "$OGG_IN" ]; then
  mv "$OGG_IN" "$OGG_BAK"
  echo "[DEBUG] song.ogg anterior movido para song_backup.ogg"
fi

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
echo "== [AUDIO] Formato FINAL do song.ogg =="
ffprobe -hide_banner "$OGG_OUT" || echo "[WARN] ffprobe falhou em song.ogg"
echo

# 5) Preparar pasta final no songs/ (YARG)
echo "== [FILES] Preparando pasta final em songs/ =="

if [ -d "$FINAL_DIR" ]; then
  BACKUP_DIR="${FINAL_DIR}_backup_$(date +%Y%m%d_%H%M%S)"
  echo "[DEBUG] Já existe FINAL_DIR, movendo para backup:"
  echo "        $BACKUP_DIR"
  mv "$FINAL_DIR" "$BACKUP_DIR"
fi

mkdir -p "$FINAL_DIR"

echo "[DEBUG] Copiando arquivos principais para FINAL_DIR..."
# Copia áudio
cp "$OGG_OUT" "$FINAL_DIR/song.ogg"

# Copia notes.mid se existir
if [ -f "$SRC_DIR/notes.mid" ]; then
  cp "$SRC_DIR/notes.mid" "$FINAL_DIR/notes.mid"
  echo "[DEBUG] notes.mid copiado."
else
  echo "[WARN] notes.mid não encontrado em SRC_DIR; FINAL_DIR ficará sem o MIDI até você copiar."
fi

# Copia song.ini se existir
if [ -f "$SRC_DIR/song.ini" ]; then
  cp "$SRC_DIR/song.ini" "$FINAL_DIR/song.ini"
  echo "[DEBUG] song.ini copiado."
else
  echo "[WARN] song.ini não encontrado; criando um mínimo."
  cat > "$FINAL_DIR/song.ini" << EOF_INI
[song]
name = $SONG_NAME
artist = Unknown Artist
album = Unknown Album
genre = rock
year = 2000
charter = Imported from RB3
EOF_INI
fi

# 6) Mover arquivos sobressalentes para _extras dentro de FINAL_DIR
EXTRAS_DIR="$FINAL_DIR/_extras"
mkdir -p "$EXTRAS_DIR"

echo "[DEBUG] Movendo sobras de SRC_DIR para _extras..."
find "$SRC_DIR" -maxdepth 1 -type f ! -name "song.mogg" ! -name "song_raw.ogg" ! -name "song.ogg" ! -name "notes.mid" ! -name "song.ini" -print0 | while IFS= read -r -d '' f; do
  echo "  [MOVE] $(basename "$f") → _extras"
  mv "$f" "$EXTRAS_DIR/"
done

echo
echo "[DEBUG] Conteúdo final de FINAL_DIR:"
ls -lah "$FINAL_DIR"
echo
echo "[DEBUG] Conteúdo de FINAL_DIR/_extras:"
ls -lah "$EXTRAS_DIR" || echo "[WARN] _extras vazio ou não acessível"
echo

echo "===== FIM: process_mogg_full_debug.sh ====="
echo "Pasta pronta para o YARG:"
echo "  $FINAL_DIR"
echo
echo "Agora faça Scan Songs no YARG e teste essa música."
