# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_mini1.json
- Mode: mock
- Records: 2
- Agents: react, reflexion

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 1.0 | 1.0 | 0.0 |
| Avg attempts | 1 | 1 | 0 |
| Avg token estimate | 763 | 758 | -5 |
| Avg latency (ms) | 9326 | 16830 | 7504 |

## Failure modes
```json
{
  "none": 2
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
