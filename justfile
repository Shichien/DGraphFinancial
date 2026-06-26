default:
    @just --list

train *args:
    uv run dgcheater-train train {{args}}

run-dataset dataset *args:
    uv run dgcheater-train train --dataset "{{dataset}}" {{args}}

dashboard:
    uv run dgcheater-train build-dashboard

dashboard-open: dashboard
    powershell -NoProfile -Command "Start-Process (Resolve-Path 'output/dashboard/index.html')"

live-store:
    uv run dgcheater-stream import-risk-events

live-dashboard:
    uv run dgcheater-stream serve-dashboard --host 127.0.0.1 --port 8050

live-open:
    powershell -NoProfile -Command "Start-Process 'http://127.0.0.1:8050'"

stream-up:
    uv run scripts/stream.py up

stream-wait:
    uv run scripts/wait.py

stream-health:
    uv run scripts/health.py

stream-consume *args:
    uv run scripts/consume.py {{args}}

stream-smoke *args:
    uv run scripts/smoke.py {{args}}

stream-logs *args:
    uv run scripts/stream.py logs {{args}}

stream-down:
    uv run scripts/stream.py down

stream-stop:
    uv run scripts/stream.py stop

stream-restart: stream-stop stream-up
