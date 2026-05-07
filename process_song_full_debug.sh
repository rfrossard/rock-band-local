#!/usr/bin/env bash
set -euo pipefail

echo "===== INÍCIO: process_song_full_debug.sh ====="
echo

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
QUARANTINE_DIR="$BASE_DIR/songs_invalid_mogg_quarantine_2026-04-26"
SONGS_DIR="$BASE_DIR/songs"

echo "[DEBUG] BASE_DIR         = $BASE_DIR"
echo "[DEBUG] QUARANTINE_DIR   = $QUARANTINE_DIR"
echo "[DEBUG] SONGS_DIR        = $SONGS_DIR"
echo

# 1) Validar argumento
if [ "$#" -lt 1 ]; then
  echo "[ERRO] Uso incorreto."
  echo "      ./process_song_full_debug.sh \"Nome da música ou arquivo rb3con\""
  echo "Exemplo:"
  echo "      ./process_song_full_debug.sh \"Milk and Toast and Honey_rb3con\""
  echo "      ./process_song_full_debug.sh \"Milk and Toast and Honey\""
  exit 1
fi

INPUT_NAME="$1"
echo "[DEBUG] INPUT_NAME       = $INPUT_NAME"

# 2) Nome "bonito" (sem sufixo _rb3con ...)
SONG_NAME="$(echo "$INPUT_NAME" | sed 's/_rb3con.*//')"
echo "[DEBUG] SONG_NAME        = $SONG_NAME"
echo

# 3) Checar diretórios base
if [ ! -d "$QUARANTINE_DIR" ]; then
  echo "[ERRO] QUARANTINE_DIR não existe:"
  echo "       $QUARANTINE_DIR"
  exit 1
fi

mkdir -p "$SONGS_DIR"

echo "[DEBUG] Conteúdo de QUARANTINE_DIR:"
ls -lah "$QUARANTINE_DIR" || echo "[WARN] Falha ao listar QUARANTINE_DIR"
echo

# 4) Encontrar arquivo rb3con correspondente (se existir)
RB3_FILE="$QUARANTINE_DIR/$INPUT_NAME"

if [ -f "$RB3_FILE" ]; then
  echo "[DEBUG] Arquivo RB3 encontrado:"
  echo "        $RB3_FILE"
else
  echo "[WARN] Arquivo RB3 não encontrado com INPUT_NAME exato:"
  echo "       $RB3_FILE"
  echo "[WARN] Tentando achar algo que comece com SONG_NAME..."
  RB3_GLOB="$QUARANTINE_DIR/$SONG_NAME"*
  set +e
  CANDIDATES=( $RB3_GLOB )
  set -e
  if [ "${#CANDIDATES[@]}" -gt 0 ] && [ -f "${CANDIDATES[0]}" ]; then
    RB3_FILE="${CANDIDATES[0]}"
    echo "[DEBUG] Primeiro candidato encontrado:"
    echo "        $RB3_FILE"
  else
    echo "[WARN] Nenhum arquivo rb3con correspondente encontrado (ok se você já converteu manualmente com o Onyx)."
  fi
fi

echo

# 5) Pasta de saída final para o YARG
FINAL_DIR="$SONGS_DIR/$SONG_NAME"
echo "[DEBUG] FINAL_DIR        = $FINAL_DIR"
echo

# 6) Pasta de trabalho onde o Onyx deve ter gerado os arquivos
#    (PONTO DE INTEGRAÇÃO com o Onyx — você pode mudar isso se quiser)
WORK_DIR="$FINAL_DIR"
echo "[DEBUG] WORK_DIR (esperado) = $WORK_DIR"
echo

# 7) Checar se WORK_DIR existe e tem algum conteúdo
if [ ! -d "$WORK_DIR" ]; then
  echo "[ERRO] WORK_DIR não existe:"
  echo "       $WORK_DIR"
  echo
  echo "Sugestão:"
  echo "  - Converta o arquivo RB3 com o Onyx apontando a saída para:"
  echo "      $WORK_DIR"
  echo "  - Depois rode este script novamente."
  exit 1
fi

echo "[DEBUG] Conteúdo de WORK_DIR antes de qualquer alteração:"
ls -lah "$WORK_DIR" || echo "[WARN] Falha ao listar WORK_DIR"
echo

# 8) Conferir arquivos mínimos esperados
OGG_IN="$WORK_DIR/song.ogg"
MID_FILE="$WORK_DIR/notes.mid"
INI_FILE="$WORK_DIR/song.ini"

if [ ! -f "$OGG_IN" ]; then
  echo "[ERRO] Não encontrei song.ogg em WORK_DIR:"
  echo "       $OGG_IN"
  echo
  echo "Isso normalmente significa que o Onyx não gerou o áudio corretamente."
  echo "Verifique manualmente a conversão antes de continuar."
  exit 1
fi

if [ ! -f "$MID_FILE" ]; then
  echo "[WARN] notes.mid não encontrado em WORK_DIR:"
  echo "       $MID_FILE"
else
  echo "[DEBUG] notes.mid encontrado."
fi

if [ ! -f "$INI_FILE" ]; then
  echo "[WARN] song.ini não encontrado em WORK_DIR:"
  echo "       $INI_FILE"
else
  echo "[DEBUG] song.ini encontrado."
fi

echo

# 9) Testar e reencodar áudio
OGG_BAK="$WORK_DIR/song_backup.ogg"
OGG_OUT="$WORK_DIR/song.ogg"

echo "== [AUDIO] Formato ATUAL do song.ogg =="
ffprobe -hide_banner "$OGG_IN" || {
  echo "[ERRO] ffprobe falhou ao ler o song.ogg. Abortando."
  exit 1
}

echo
echo "== [AUDIO] Reencodando para 44100 Hz, stereo =="

mv "$OGG_IN" "$OGG_BAK"

ffmpeg -y -i "$OGG_BAK" \
  -ar 44100 -ac 2 \
  "$OGG_OUT"

FFMPEG_STATUS=$?
echo "[DEBUG] ffmpeg exit code = $FFMPEG_STATUS"

if [ $FFMPEG_STATUS -ne 0 ]; then
  echo "[ERRO] Erro ao reencodar OGG, restaurando arquivo original."
  mv "$OGG_BAK" "$OGG_IN"
  exit 1
else
  echo "[INFO] Reencode concluído. Arquivo original mantido como song_backup.ogg"
fi

echo
echo "== [AUDIO] Formato NOVO do song.ogg =="
ffprobe -hide_banner "$OGG_OUT" || {
  echo "[WARN] ffprobe falhou ao ler o song.ogg reencodado."
}

echo
echo "===== FIM: process_song_full_debug.sh ====="
echo "Pasta final (para o YARG):"
echo "  $FINAL_DIR"
echo
echo "Agora vá no YARG → Settings → Songs → Scan Songs e teste essa música."
