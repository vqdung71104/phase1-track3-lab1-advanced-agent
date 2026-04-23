# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_mini.json
- Mode: api
- Records: 109
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.3056 | 1.0 | 0.6944 |
| Avg attempts | 1 | 1 | 0 |
| Avg token estimate | 2145.41 | 758 | -1387.41 |
| Avg latency (ms) | 13849.19 | 16830 | 2980.81 |

## Failure modes
```json
{
  "none": 34,
  "wrong_final_answer": 73,
  "incomplete_multi_hop": 1,
  "entity_drift": 1
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- memory_compression
- adaptive_max_attempts
- plan_then_execute
- mini_lats_branching
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
Reflexion helps when the first attempt stops after the first hop or drifts to a wrong second-hop entity. The tradeoff is higher attempts, token cost, and latency. In a real report, students should explain when the reflection memory was useful, which failure modes remained, and whether evaluator quality limited gains.
