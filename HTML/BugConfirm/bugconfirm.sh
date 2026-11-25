#!/usr/bin/env bash
set -euo pipefail

: "${HG_ROOT:?HG_ROOT must be an absolute HanGuang application path}"
: "${HG_WORK_ROOT:?HG_WORK_ROOT must be an absolute physical work-directory path}"

APP_DIR="${HG_ROOT%/}/HTML/BugConfirm"
RUNTIME_DIR="${HG_WORK_ROOT%/}/HTML/BugConfirm"
PID_FILE="$RUNTIME_DIR/.bugconfirm.pid"
PORT_FILE="$RUNTIME_DIR/.bugconfirm.port"
LOG_FILE="$RUNTIME_DIR/.bugconfirm.log"
REQUESTED_PORT="${HG_BUGCONFIRM_PORT:-}"
PORT="${REQUESTED_PORT:-8786}"

mkdir -p "$RUNTIME_DIR"

is_running() {
  [[ -f "$PID_FILE" ]] && kill -0 "$(<"$PID_FILE")" 2>/dev/null
}

is_port_free() {
  node -e 'const net=require("net");const s=net.createServer();s.once("error",()=>process.exit(1));s.listen(Number(process.argv[1]),"127.0.0.1",()=>s.close(()=>process.exit(0)))' "$1"
}

choose_port() {
  local candidate
  for candidate in $(seq 8786 8806); do
    if is_port_free "$candidate"; then printf '%s\n' "$candidate"; return 0; fi
  done
  return 1
}

saved_port() {
  local stored
  if [[ -s "$PORT_FILE" ]]; then
    IFS= read -r stored < "$PORT_FILE"
    printf '%s\n' "$stored"
  else
    printf '%s\n' "$PORT"
  fi
}

case "${1:-start}" in
  start)
    if is_running; then
      PORT="$(saved_port)"
      echo "BugConfirm is already running at http://127.0.0.1:$PORT"
      exit 0
    fi
    rm -f "$PID_FILE"
    if ! is_port_free "$PORT"; then
      if [[ -n "$REQUESTED_PORT" ]]; then
        echo "Port $PORT is already in use. Choose another port: HG_BUGCONFIRM_PORT=8790 ./bugconfirm.sh start" >&2
        exit 1
      fi
      PORT="$(choose_port)" || { echo "No free localhost port found between 8786 and 8806." >&2; exit 1; }
      echo "Port 8786 is in use; using $PORT instead."
    fi
    printf '%s\n' "$PORT" >"$PORT_FILE"
    (cd "$APP_DIR" && HG_BUGCONFIRM_PORT="$PORT" nohup node server.js >>"$LOG_FILE" 2>&1 & echo $! >"$PID_FILE")
    sleep 0.3
    if is_running; then echo "BugConfirm started: http://127.0.0.1:$PORT"; else rm -f "$PORT_FILE"; echo "Failed to start. See $LOG_FILE" >&2; exit 1; fi
    ;;
  stop)
    if is_running; then kill "$(<"$PID_FILE")"; rm -f "$PID_FILE" "$PORT_FILE"; echo "BugConfirm stopped."; else rm -f "$PID_FILE" "$PORT_FILE"; echo "BugConfirm is not running."; fi
    ;;
  restart) "$0" stop; "$0" start ;;
  status) if is_running; then PORT="$(saved_port)"; echo "Running at http://127.0.0.1:$PORT (PID $(<"$PID_FILE"))"; else echo "Not running."; fi ;;
  *) echo "Usage: $0 {start|stop|restart|status}" >&2; exit 2 ;;
esac
