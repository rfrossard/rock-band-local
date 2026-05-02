"""
Rock Band Local — Constants
Cores, fret indices, mapeamentos e enums do jogo.
Tema visual baseado no YARG (dark neon).
"""
import pygame

# ── Resolução padrão ───────────────────────────────────────────────────────────
SCREEN_W = 1280
SCREEN_H = 720

# ── Cores base ────────────────────────────────────────────────────────────────
BLACK   = (0, 0, 0)
WHITE   = (255, 255, 255)
GRAY    = (120, 120, 140)
DGRAY   = (30, 30, 40)
RED     = (220, 30, 30)

# ── YARG Dark Theme ───────────────────────────────────────────────────────────
# Fundo muito escuro, quase preto — assinatura visual do YARG
COLOR_BG          = (8, 8, 14)          # fundo principal (#08080E)
COLOR_BG_DARK     = (5, 5, 10)          # mais escuro ainda
COLOR_PANEL       = (14, 14, 22)        # painéis/cards
COLOR_PANEL_LIGHT = (22, 22, 34)        # painéis mais claros
COLOR_BORDER      = (40, 40, 60)        # bordas sutis
COLOR_ACCENT      = (80, 80, 180)       # destaque roxo-azulado

# Highway YARG — escuro com linhas tênues
COLOR_HIGHWAY     = (12, 12, 20)        # fundo do highway
COLOR_HIGHWAY_SP  = (10, 20, 45)        # highway durante Star Power
COLOR_LINE        = (35, 35, 55)        # linhas divisórias verticais
COLOR_LINE_BEAT   = (50, 50, 80)        # linha de beat (mais visível)
COLOR_LINE_MEASURE= (70, 70, 110)       # linha de compasso

# Gems — cores neon vibrantes estilo YARG
FRET_GREEN  = (0, 220, 60)             # verde neon
FRET_RED    = (235, 20, 20)            # vermelho vivo
FRET_YELLOW = (255, 220, 0)            # amarelo saturado
FRET_BLUE   = (20, 120, 255)           # azul elétrico
FRET_ORANGE = (255, 120, 0)            # laranja vivo

FRET_COLORS = [FRET_GREEN, FRET_RED, FRET_YELLOW, FRET_BLUE, FRET_ORANGE]

# Glow/halo das gems — versão mais brilhante de cada cor
FRET_GLOW = [
    (80, 255, 120),    # green glow
    (255, 80, 80),     # red glow
    (255, 250, 80),    # yellow glow
    (60, 160, 255),    # blue glow
    (255, 170, 60),    # orange glow
]

# Cor interior das gems (brilho interno)
FRET_INNER = [
    (200, 255, 210),   # green inner
    (255, 200, 200),   # red inner
    (255, 255, 200),   # yellow inner
    (200, 220, 255),   # blue inner
    (255, 230, 200),   # orange inner
]

# Pads — Bateria (mesmas cores neon)
PAD_KICK   = (255, 140, 0)
PAD_RED    = (235, 20, 20)
PAD_YELLOW = (255, 220, 0)
PAD_BLUE   = (20, 120, 255)
PAD_GREEN  = (0, 220, 60)

PAD_COLORS = [PAD_KICK, PAD_RED, PAD_YELLOW, PAD_BLUE, PAD_GREEN]
PAD_LABELS = ["KICK", "RED", "YEL", "BLU", "GRN"]

# Vocal
VOCAL_COLOR = (200, 80, 255)

# UI cores
COLOR_STAR      = (255, 210, 0)         # estrela / ouro
COLOR_STAR_DIM  = (80, 65, 0)          # estrela vazia
COLOR_OVERDRIVE = (128, 207, 255)       # Star Power / overdrive (azul-branco YARG)
COLOR_SP_BAR    = (100, 180, 255)       # barra de SP (azul)
COLOR_SP_ACTIVE = (180, 230, 255)       # SP ativo (mais brilhante)
COLOR_MULT_BG   = (30, 80, 180)         # fundo do bubble de multiplicador (azul YARG)
COLOR_MULT_SP   = (180, 100, 255)       # mult durante SP (roxo)
COLOR_CROWD_OK  = (60, 200, 100)        # crowd meter metade positiva (verde)
COLOR_CROWD_BAD = (200, 60, 60)         # crowd meter baixo (vermelho)

COLOR_HIT_PERFECT = (255, 240, 80)      # PERFECT!
COLOR_HIT_GREAT   = (80, 255, 120)      # GREAT!
COLOR_HIT_GOOD    = (80, 180, 255)      # GOOD
COLOR_HIT_OK      = (180, 180, 180)     # OKAY
COLOR_HIT_MISS    = (255, 60, 60)       # MISS
COLOR_HIT_GOOD_OLD= (255, 255, 100)     # legacy compat
COLOR_HIT_MISS_OLD= (180, 40, 40)       # legacy compat

COLOR_SCORE     = (255, 255, 255)       # texto de score

# ── Instrumentos ──────────────────────────────────────────────────────────────
INSTRUMENT_GUITAR  = "guitar"
INSTRUMENT_BASS    = "bass"
INSTRUMENT_DRUMS   = "drums"
INSTRUMENT_VOCALS  = "vocals"
INSTRUMENT_KEYS    = "keys"

INSTRUMENTS = [INSTRUMENT_GUITAR, INSTRUMENT_BASS, INSTRUMENT_DRUMS, INSTRUMENT_VOCALS]

# ── Dificuldades ──────────────────────────────────────────────────────────────
DIFF_EASY   = "easy"
DIFF_MEDIUM = "medium"
DIFF_HARD   = "hard"
DIFF_EXPERT = "expert"

DIFFICULTIES = [DIFF_EASY, DIFF_MEDIUM, DIFF_HARD, DIFF_EXPERT]

# Mapeamento para tracks no .chart
CHART_TRACK = {
    (INSTRUMENT_GUITAR, DIFF_EASY):   "EasySingle",
    (INSTRUMENT_GUITAR, DIFF_MEDIUM): "MediumSingle",
    (INSTRUMENT_GUITAR, DIFF_HARD):   "HardSingle",
    (INSTRUMENT_GUITAR, DIFF_EXPERT): "ExpertSingle",
    (INSTRUMENT_BASS, DIFF_EASY):     "EasyDoubleBass",
    (INSTRUMENT_BASS, DIFF_MEDIUM):   "MediumDoubleBass",
    (INSTRUMENT_BASS, DIFF_HARD):     "HardDoubleBass",
    (INSTRUMENT_BASS, DIFF_EXPERT):   "ExpertDoubleBass",
    (INSTRUMENT_DRUMS, DIFF_EASY):    "EasyDrums",
    (INSTRUMENT_DRUMS, DIFF_MEDIUM):  "MediumDrums",
    (INSTRUMENT_DRUMS, DIFF_HARD):    "HardDrums",
    (INSTRUMENT_DRUMS, DIFF_EXPERT):  "ExpertDrums",
    (INSTRUMENT_VOCALS, DIFF_EASY):   "EasyVocals",
    (INSTRUMENT_VOCALS, DIFF_MEDIUM): "MediumVocals",
    (INSTRUMENT_VOCALS, DIFF_HARD):   "HardVocals",
    (INSTRUMENT_VOCALS, DIFF_EXPERT): "ExpertVocals",
}

# ── Scoring ───────────────────────────────────────────────────────────────────
NOTE_BASE_SCORE    = 50
SUSTAIN_SCORE_PPS  = 25   # pontos por segundo em sustain
STAR_POWER_MULT    = 2    # multiplicador durante Star Power
MAX_MULTIPLIER     = 4
NOTES_PER_MULT     = 10   # notas para subir 1 nível de multiplicador

# Streak para cada nível de multiplicador
MULT_THRESHOLDS = [0, 10, 20, 30]  # streak necessária para 1x, 2x, 3x, 4x

# ── Hit windows ───────────────────────────────────────────────────────────────
HIT_PERFECT_MS = 20
HIT_GOOD_MS    = 45
HIT_OK_MS      = 70

# ── Telas do jogo (estados) ───────────────────────────────────────────────────
STATE_MAIN_MENU      = "main_menu"
STATE_SONG_SELECT    = "song_select"
STATE_INSTRUMENT_SEL = "instrument_select"
STATE_GAMEPLAY       = "gameplay"
STATE_RESULTS        = "results"
STATE_CALIBRATION    = "calibration"
STATE_RHYTHMVERSE    = "rhythmverse"
STATE_SETTINGS       = "settings"
STATE_QUIT           = "quit"

# ── Fontes ────────────────────────────────────────────────────────────────────
FONT_TITLE_SIZE  = 72
FONT_LARGE_SIZE  = 48
FONT_MEDIUM_SIZE = 32
FONT_SMALL_SIZE  = 22
FONT_TINY_SIZE   = 16

# ── Highway 3D Perspectiva (estilo YARG) ────────────────────────────────────────
HIGHWAY_X_OFFSET    = 200    # X inicial da highway no modo single (legacy)
HIGHWAY_WIDTH       = 220    # largura total da highway de 5 frets (legacy)
FRET_WIDTH          = 40     # largura de cada lane (legacy)
FRET_GAP            = 3
NOTE_HEIGHT         = 18
NOTE_RADIUS         = 14     # raio base das gems (maior que antes)
HIT_LINE_Y_RATIO    = 0.82   # posição Y da linha de hit (% da tela)

# Perspectiva 3D
HWY_BOTTOM_W        = 380    # largura do highway na linha de hit (bottom/near)
HWY_TOP_W           = 120    # largura do highway no topo (far/future)
HWY_TOP_Y_RATIO     = 0.03   # topo do highway como fração da altura da tela
HWY_HIT_Y_RATIO     = 0.82   # hit line como fração da altura da tela
HWY_VANISH_Y_RATIO  = -0.20  # ponto de fuga (acima da tela)

# Tamanho das hit targets (círculos coloridos na hit line)
HIT_TARGET_RADIUS   = 28     # raio dos botões circulares na linha de hit

# ── Vocals ────────────────────────────────────────────────────────────────────
VOCAL_PITCH_MIN    = 60    # Hz
VOCAL_PITCH_MAX    = 1200  # Hz
VOCAL_HIT_CENTS    = 50    # margem de acerto em centavos
