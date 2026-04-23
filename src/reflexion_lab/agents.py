from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
from .mock_runtime import FAILURE_MODE_BY_QID
from .api_runtime import actor_answer, evaluator, reflector, planner, plan_evaluator, metrics
from .schemas import AttemptTrace, QAExample, ReflectionEntry, RunRecord

@dataclass
class BaseAgent:
    agent_type: Literal["react", "reflexion"]
    max_attempts: int = 1
    reflection_memory: list[str] = field(default_factory=list)
    memory_limit: int = 3

    def compress_memory(self):
        if len(self.reflection_memory) > self.memory_limit:
            summarized = "Summarized past lessons: Always complete multi-hop reasoning and verify entities."
            self.reflection_memory = [summarized] + self.reflection_memory[-(self.memory_limit - 1):]

    def run(self, example: QAExample) -> RunRecord:
        reflections: list[ReflectionEntry] = []
        traces: list[AttemptTrace] = []
        final_answer = ""
        final_score = 0
        current_max_attempts = self.max_attempts
        attempt_id = 1
        while attempt_id <= current_max_attempts:
            metrics.reset()
            candidate_plans = planner(example)
            best_plan = ""
            best_score = -1
            for p in candidate_plans:
                score = plan_evaluator(p)
                if score > best_score:
                    best_score = score
                    best_plan = p
            plan = best_plan
            
            answer = actor_answer(example, attempt_id, self.agent_type, self.reflection_memory, plan)
            judge = evaluator(example, answer)
            trace = AttemptTrace(attempt_id=attempt_id, answer=answer, score=judge.score, reason=judge.reason, token_estimate=0, latency_ms=0, plan=plan, candidate_plans=candidate_plans)
            final_answer = answer
            final_score = judge.score
            if judge.score == 1:
                trace.token_estimate = metrics.tokens
                trace.latency_ms = metrics.latency_ms
                traces.append(trace)
                break
            
            if self.agent_type == "reflexion" and attempt_id == current_max_attempts:
                if example.difficulty == "hard" and current_max_attempts < 5:
                    current_max_attempts += 2

            if self.agent_type == "reflexion" and attempt_id < current_max_attempts:
                reflection = reflector(example, attempt_id, judge)
                reflections.append(reflection)
                self.reflection_memory.append(f"Lesson: {reflection.lesson}\nStrategy: {reflection.next_strategy}")
                self.compress_memory()
                trace.reflection = reflection
            
            trace.token_estimate = metrics.tokens
            trace.latency_ms = metrics.latency_ms
            traces.append(trace)
            attempt_id += 1
        total_tokens = sum(t.token_estimate for t in traces)
        total_latency = sum(t.latency_ms for t in traces)
        failure_mode = "none" if final_score == 1 else FAILURE_MODE_BY_QID.get(example.qid, "wrong_final_answer")
        return RunRecord(qid=example.qid, question=example.question, gold_answer=example.gold_answer, agent_type=self.agent_type, predicted_answer=final_answer, is_correct=bool(final_score), attempts=len(traces), token_estimate=total_tokens, latency_ms=total_latency, failure_mode=failure_mode, reflections=reflections, traces=traces)

class ReActAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_type="react", max_attempts=1)

class ReflexionAgent(BaseAgent):
    def __init__(self, max_attempts: int = 3) -> None:
        super().__init__(agent_type="reflexion", max_attempts=max_attempts)
