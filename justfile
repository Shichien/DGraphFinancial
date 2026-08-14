default:
    @just --list

risk-console:
    @uv run dgcheater-realtime risk-console

frontend-console host="127.0.0.1" port="8060":
    @npm --prefix frontend/graph-stream ci
    @npm --prefix frontend/graph-stream run build
    @uv run dgcheater-realtime-api --host "{{host}}" --port {{port}}

frontend-console-api host="127.0.0.1" port="8060":
    @uv run dgcheater-realtime-api --host "{{host}}" --port {{port}}

frontend-console-ui:
    @npm --prefix frontend/graph-stream ci
    @npm --prefix frontend/graph-stream run dev

risk-console-demo output="tmp/realtime/manual-risk-results.json":
    @uv run dgcheater-realtime risk-console --script docs/online-deployment/examples/risk-console-script.json --output "{{output}}"

risk-console-demo-json:
    @uv run dgcheater-realtime risk-console --script docs/online-deployment/examples/risk-console-script.json --print-json

risk-console-script script output="tmp/realtime/manual-risk-results.json":
    @uv run dgcheater-realtime risk-console --script "{{script}}" --output "{{output}}"
