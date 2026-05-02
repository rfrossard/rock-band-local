#!/bin/bash
# ────────────────────────────────────────────────────────────
#  Fross Garage Band — Launch YARG with BepInEx
#  Double-click to start YARG with the Download Music plugin
# ────────────────────────────────────────────────────────────
YARG="/Applications/YARG.app"
RUN_SCRIPT="$YARG/run_bepinex.sh"

if [ ! -f "$RUN_SCRIPT" ]; then
    osascript -e 'display alert "run_bepinex.sh not found" message "Make sure BepInEx is installed in YARG.app"'
    exit 1
fi

cd "$YARG"
chmod +x "$RUN_SCRIPT"
exec "$RUN_SCRIPT"
