# Streaming Prototype Performance

## Scope

- Dataset: `dgraph_fin`
- Replayed events: `5000`
- Scored unique nodes: `9986`

## Latency and Throughput

- Total runtime: `0.1130` seconds
- Model scoring runtime: `0.0784` seconds
- Event throughput: `44231.03` events/second
- Scored-node throughput: `88338.22` nodes/second
- Pure scoring throughput: `127411.78` nodes/second
- Average node scoring latency: `0.0078` ms
- P50 node scoring latency: `0.0078` ms
- P95 node scoring latency: `0.0078` ms
- P99 node scoring latency: `0.0078` ms
- Average event end-to-end latency: `0.0226` ms

## Risk Level Distribution

- critical: 80
- high: 760
- low: 3043
- medium: 1117

## Interpretation

This is a single-machine replay prototype rather than a Kafka/Flink deployment. It gives the project a measured online-scoring baseline and a concrete path for replacing the CSV replay source with a streaming message queue.
