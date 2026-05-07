#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
SONGS_DIR="$BASE_DIR/songs"

echo "===== INÍCIO: configure_yarg_lyrics.sh ====="
echo

echo "Base:  $BASE_DIR"
echo "Songs: $SONGS_DIR"
echo

if [ "$#" -lt 1 ]; then
  echo "[ERRO] Uso incorreto."
  echo "      ./configure_yarg_lyrics.sh \"Nome da pasta da música\""
  echo "Exemplo:"
  echo "      ./configure_yarg_lyrics.sh \"Almost Unreal\""
  echo "      ./configure_yarg_lyrics.sh \"Dressed For Success\""
  exit 1
fi

SONG_NAME="$1"
SONG_DIR="$SONGS_DIR/$SONG_NAME"

echo "[DEBUG] SONG_NAME = $SONG_NAME"
echo "[DEBUG] SONG_DIR  = $SONG_DIR"
echo

if [ ! -d "$SONG_DIR" ]; then
  echo "[ERRO] Pasta da música não encontrada:"
  echo "       $SONG_DIR"
  exit 1
fi

INI_PATH="$SONG_DIR/song.ini"
MID_PATH="$SONG_DIR/notes.mid"

if [ ! -f "$INI_PATH" ]; then
  echo "[WARN] song.ini não encontrado; criando um do zero."
else
  echo "[DEBUG] song.ini encontrado:"
  echo "       $INI_PATH"
fi

if [ ! -f "$MID_PATH" ]; then
  echo "[WARN] notes.mid NÃO encontrado."
  echo "       Sem MIDI não haverá chart de vocal para sincronizar letras."
else
  echo "[DEBUG] notes.mid encontrado:"
  echo "       $MID_PATH"
fi

echo
echo "[INFO] Atualizando song.ini com configuração de vocals para YARG..."

cat > "$INI_PATH" << EOF_INI
[song]
name = $SONG_NAME
artist = Imported from RB3
album = Unknown Album
genre = rock
year = 2000
charter = RB3 Import

# Vocals / lyrics config
has_vocals = true
vocal_gender = male
vocal_tonic_note = 60      ; C4 como default
pro_drums = false
eof_lyric_conversion = true
eof_lyric_format = 0       ; formato padrão de lyrics no MIDI

# YARG / Clone Hero style settings
song_length = 0
diff_band = 0
diff_guitar = 0
diff_bass = 0
diff_drums = 0
diff_vocals = 0
EOF_INI

echo
echo "[DEBUG] Novo conteúdo de song.ini:"
cat "$INI_PATH"
echo

echo "===== FIM: configure_yarg_lyrics.sh ====="
echo "song.ini atualizado com flags de vocals."
echo "Agora rode o YARG → Scan Songs e teste se as lyrics aparecem."
