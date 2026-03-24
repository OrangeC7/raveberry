#!/usr/bin/env bash
set -Eeuo pipefail

SERVICE="$(systemctl list-unit-files --type=service --no-legend | awk '{print $1}' | grep -Ei 'raveberry.*\.service$' | head -n1 || true)"
[[ -n "$SERVICE" ]] || { echo "No Raveberry service found."; exit 1; }

NEWT_DIR="$HOME/.config/raveberry"
NEWT_FILE="$NEWT_DIR/newt_command.sh"
TMUX_SESSION="raveberry-newt"

# Ensure tmux exists (auto installs if missing)
if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found. Installing..."
  sudo apt update
  sudo apt install -y tmux
fi

# Ask once for NEWT command and store securely
if [[ ! -f "$NEWT_FILE" ]]; then
  mkdir -p "$NEWT_DIR"
  read -r -p "Paste your full NEWT command: " NEWT_COMMAND
  [[ -n "${NEWT_COMMAND:-}" ]] || { echo "Empty NEWT command. Aborting."; exit 1; }

  {
    echo '#!/usr/bin/env bash'
    echo 'set -Eeuo pipefail'
    printf '%s\n' "$NEWT_COMMAND"
  } > "$NEWT_FILE"

  chmod 700 "$NEWT_DIR"
  chmod 600 "$NEWT_FILE"
  echo "Saved NEWT command to $NEWT_FILE"
fi

# Start Raveberry service
sudo systemctl start "$SERVICE"
sudo systemctl status --no-pager "$SERVICE"

# Start NEWT in tmux (if not already running)
if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
  echo "NEWT tmux session already running: $TMUX_SESSION"
else
  tmux new-session -d -s "$TMUX_SESSION" "bash '$NEWT_FILE'"
  echo "Started NEWT in tmux session: $TMUX_SESSION"
fi

echo "Done."
echo "View NEWT logs: tmux attach -t $TMUX_SESSION"
echo "Detach from tmux: Ctrl+b then d"
