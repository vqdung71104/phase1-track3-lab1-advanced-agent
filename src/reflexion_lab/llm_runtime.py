from __future__ import annotations
import json
import requests
from .schemas import QAExample, JudgeResult, ReflectionEntry
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM, PLANNER_SYSTEM, PLAN_EVALUATOR_SYSTEM

MODEL = "llama3.2:3b"
OLLAMA_URL = "http://localhost:11434/api/chat"

class LLMMetrics:
    def __init__(self):
        self.tokens = 0
        self.latency_ms = 0

    def reset(self):
        self.tokens = 0
        self.latency_ms = 0

    def add(self, eval_count: int, eval_duration_ns: int):
        self.tokens += eval_count
        self.latency_ms += int(eval_duration_ns / 1_000_000)

metrics = LLMMetrics()

def call_ollama(system_prompt: str, user_prompt: str, json_format: bool = False) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False
    }
    if json_format:
        payload["format"] = "json"
        
    try:
        print(f"--- [LLM Request] Calling {MODEL} ---")
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        eval_count = data.get("eval_count", 0)
        duration_ms = int(data.get("total_duration", 0) / 1_000_000)
        metrics.add(eval_count, data.get("total_duration", 0))
        print(f"--- [LLM Response] Success! Tokens: {eval_count}, Latency: {duration_ms}ms ---")
        return data["message"]["content"]
    except Exception as e:
        print(f"!!! [LLM Error] Ollama failed: {e} !!!")
        return "{}" if json_format else "Error"

def planner(example: QAExample) -> list[str]:
    sys_prompt = PLANNER_SYSTEM + "\nOutput a JSON array of 3 strings, each being a different plan."
    user_prompt = f"Question: {example.question}"
    content = call_ollama(sys_prompt, user_prompt, json_format=True)
    try:
        plans = json.loads(content)
        if isinstance(plans, list):
            return plans[:3]
    except:
        pass
    return ["Plan A: Think step by step and answer.", "Plan B: Extract entity and find attribute."]

def plan_evaluator(plan: str) -> int:
    sys_prompt = PLAN_EVALUATOR_SYSTEM + "\nOutput a JSON object with a single key 'score' (integer 1-10)."
    user_prompt = f"Plan: {plan}"
    content = call_ollama(sys_prompt, user_prompt, json_format=True)
    try:
        data = json.loads(content)
        return int(data.get("score", 5))
    except:
        return 5

def actor_answer(example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[str], plan: str = "") -> str:
    context_str = "\n".join([f"[{c.title}] {c.text}" for c in example.context])
    memory_str = "\n".join(reflection_memory) if reflection_memory else "None"
    user_prompt = f"Context:\n{context_str}\n\nReflection Memory:\n{memory_str}\n\nPlan:\n{plan}\n\nQuestion: {example.question}\n\nAnswer:"
    return call_ollama(ACTOR_SYSTEM, user_prompt)

def evaluator(example: QAExample, answer: str) -> JudgeResult:
    user_prompt = f"Gold Answer: {example.gold_answer}\nPredicted Answer: {answer}"
    content = call_ollama(EVALUATOR_SYSTEM, user_prompt, json_format=True)
    try:
        data = json.loads(content)
        return JudgeResult(**data)
    except:
        return JudgeResult(score=0, reason="Failed to parse evaluator response.")

def reflector(example: QAExample, attempt_id: int, judge: JudgeResult) -> ReflectionEntry:
    context_str = "\n".join([f"[{c.title}] {c.text}" for c in example.context])
    user_prompt = f"Context:\n{context_str}\n\nQuestion: {example.question}\nFeedback: {judge.reason}\n\nOutput JSON with 'lesson' and 'next_strategy'."
    content = call_ollama(REFLECTOR_SYSTEM, user_prompt, json_format=True)
    try:
        data = json.loads(content)
        return ReflectionEntry(attempt_id=attempt_id, failure_reason=judge.reason, lesson=data.get("lesson", ""), next_strategy=data.get("next_strategy", ""))
    except:
        return ReflectionEntry(attempt_id=attempt_id, failure_reason=judge.reason, lesson="Error", next_strategy="Error")
