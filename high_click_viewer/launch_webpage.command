#!/bin/zsh

# Launch the High-Click Viewer locally and open it in the default browser.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PORT=8000
for candidate in $(seq 8000 8010); do
	if ! lsof -iTCP:"$candidate" -sTCP:LISTEN >/dev/null 2>&1; then
		PORT="$candidate"
		break
	fi
done

URL="http://localhost:${PORT}/high_click_viewer/index.html"

cd "$WORKSPACE_ROOT" || exit 1

echo "Starting local server in $WORKSPACE_ROOT on port $PORT..."
python3 -m http.server "$PORT" --directory "$WORKSPACE_ROOT" &
SERVER_PID=$!

# Wait for server readiness before opening the browser.
for _ in {1..30}; do
	if curl -sSf "http://localhost:${PORT}/index.html" >/dev/null 2>&1; then
		break
	fi
	sleep 0.2
done

open "$URL"

echo "Viewer opened at $URL"
echo "Server PID: $SERVER_PID"
echo "Press Ctrl+C to stop the server."

wait "$SERVER_PID"
