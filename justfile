default:
    @just --list

risk-console:
    @uv run dgcheater-realtime risk-console

frontend-console host="127.0.0.1" port="8060":
    @bun run --cwd frontend/graph-stream build
    @uv run dgcheater-realtime-api --host "{{host}}" --port {{port}}

frontend-console-api host="127.0.0.1" port="8060":
    @uv run dgcheater-realtime-api --host "{{host}}" --port {{port}}

frontend-console-ui:
    @bun run --cwd frontend/graph-stream dev

risk-console-demo output="output/realtime/manual-risk-results.json":
    @uv run dgcheater-realtime risk-console --script docs/online-deployment/examples/risk-console-script.json --output "{{output}}"

risk-console-demo-json:
    @uv run dgcheater-realtime risk-console --script docs/online-deployment/examples/risk-console-script.json --print-json

risk-console-script script output="output/realtime/manual-risk-results.json":
    @uv run dgcheater-realtime risk-console --script "{{script}}" --output "{{output}}"
