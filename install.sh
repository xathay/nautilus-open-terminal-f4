#!/usr/bin/env bash
# Instala/desinstala a extensão nautilus-open-terminal-f4 via symlink.
set -euo pipefail

SRC_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
EXT_DIR="${HOME}/.local/share/nautilus-python/extensions"
LINK="${EXT_DIR}/open_terminal_f4.py"
GSCHEMA="com.github.stunkymonkey.nautilus-open-any-terminal"

restart_nautilus() {
	if command -v nautilus >/dev/null 2>&1; then
		nautilus -q >/dev/null 2>&1 || true
		echo "Nautilus reiniciado — abra uma pasta e aperte F4."
	fi
}

if [[ "${1:-}" == "--uninstall" ]]; then
	rm -f "$LINK"
	echo "Symlink removido: $LINK"
	restart_nautilus
	exit 0
fi

mkdir -p "$EXT_DIR"
ln -sf "${SRC_DIR}/open_terminal_f4.py" "$LINK"
echo "Symlink criado: $LINK -> ${SRC_DIR}/open_terminal_f4.py"

# Zera o keybinding das GSettings oficiais para não registrar um accel-app morto (F4).
if command -v gsettings >/dev/null 2>&1 && gsettings list-schemas 2>/dev/null | grep -qx "$GSCHEMA"; then
	gsettings set "$GSCHEMA" keybindings '' || true
	echo "GSettings ${GSCHEMA} keybindings zerado."
fi

restart_nautilus
