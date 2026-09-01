#!/usr/bin/env bash
# HATO Festival — prepare a GIF for the campaign asset policy.
# Usage: ./tooling/prepare_gif.sh <input.gif-or-url> <output-name>
# Produces: assets/<output-name>.gif (≤2MB, white bg keyed transparent)
#           assets/<output-name>_static.png (reduced-motion fallback)
# Requires: ffmpeg (brew install ffmpeg)
set -e
IN="$1"; NAME="$2"
[ -z "$NAME" ] && { echo "usage: prepare_gif.sh <input.gif|url> <name>"; exit 1; }
TMP=$(mktemp -d)
case "$IN" in http*) curl -sL "$IN" -o "$TMP/in.gif";; *) cp "$IN" "$TMP/in.gif";; esac

# Key out white background, crop vignette edges, compress under 2MB
ffmpeg -v error -i "$TMP/in.gif" -filter_complex \
"[0:v]crop=iw*0.86:ih*0.86:(iw-iw*0.86)/2:(ih-ih*0.86)/2,fps=12,scale=300:-1:flags=lanczos,colorkey=0xFFFFFF:0.28:0.03,split[a][b];[a]palettegen=reserve_transparent=1:max_colors=128[p];[b][p]paletteuse=alpha_threshold=170:dither=bayer:bayer_scale=3" \
-y "assets/${NAME}.gif"
ffmpeg -v error -i "assets/${NAME}.gif" -vf "select=eq(n\,20)" -vframes 1 -y "assets/${NAME}_static.png"

SIZE=$(stat -f%z "assets/${NAME}.gif" 2>/dev/null || stat -c%s "assets/${NAME}.gif")
echo "assets/${NAME}.gif → $SIZE bytes"
[ "$SIZE" -gt 2097152 ] && echo "⚠️  OVER 2MB cap — reduce scale/fps in this script and re-run" && exit 1
echo "✅ Under 2MB. Next: update the section manifest's hero.art url to:"
echo "   https://raw.githubusercontent.com/metavisionrs/hato-festival-config/main/assets/${NAME}.gif"
echo "   (+ reducedMotionFallback → ${NAME}_static.png), bump \"revision\", commit & push."
