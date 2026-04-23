from __future__ import annotations
import json
import os
import requests
import time
from dotenv import load_dotenv

# Nạp các biến môi trường từ file .env
load_dotenv()

from .schemas import QAExample, JudgeResult, ReflectionEntry
from .prompts import ACTOR_SYSTEM, EVALUATOR_SYSTEM, REFLECTOR_SYSTEM, PLANNER_SYSTEM, PLAN_EVALUATOR_SYSTEM

MODEL = "gpt-4o-mini"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

API_KEY = os.environ.get("OPENAI_API_KEY", "")

class LLMMetrics:
    def __init__(self):
        self.tokens = 0
        self.latency_ms = 0

    def reset(self):
        self.tokens = 0
        self.latency_ms = 0

    def add(self, eval_count: int, eval_duration_ms: int):
        self.tokens += eval_count
        self.latency_ms += eval_duration_ms

metrics = LLMMetrics()

def call_openai(system_prompt: str, user_prompt: str, json_format: bool = False) -> str:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7
    }
    if json_format:
        payload["response_format"] = {"type": "json_object"}
        
    start_time = time.time()
    try:
        print(f"--- [API Request] Calling {MODEL} ---")
        response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        duration_ms = int((time.time() - start_time) * 1000)
        eval_count = data.get("usage", {}).get("total_tokens", 0)
        metrics.add(eval_count, duration_ms)
        print(f"--- [API Response] Success! Tokens: {eval_count}, Latency: {duration_ms}ms ---")
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"!!! [API Error] OpenAI failed: {e} !!!")
        if hasattr(e, 'response') and getattr(e, 'response', None) is not None:
            print(f"Details: {e.response.text}")
        return "{}" if json_format else "Error"

def planner(example: QAExample) -> list[str]:
    sys_prompt = PLANNER_SYSTEM + "\nOutput a JSON object with a single key 'plans' containing an array of 3 strings, each being a different plan."
    user_prompt = f"Question: {example.question}"
    content = call_openai(sys_prompt, user_prompt, json_format=True)
    try:
        data = json.loads(content)
        plans = data.get("plans", [])
        if isinstance(plans, list) and len(plans) > 0:
            return plans[:3]
    except Exception as e:
        print("Parse error in planner:", e)
    return ["Plan A: Think step by step and answer.", "Plan B: Extract entity and find attribute."]

def plan_evaluator(plan: str) -> int:
    sys_prompt = PLAN_EVALUATOR_SYSTEM + "\nOutput a JSON object with a single key 'score' (integer 1-10)."
    user_prompt = f"Plan: {plan}"
    content = call_openai(sys_prompt, user_prompt, json_format=True)
    try:
        data = json.loads(content)
        return int(data.get("score", 5))
    except:
        return 5

def actor_answer(example: QAExample, attempt_id: int, agent_type: str, reflection_memory: list[str], plan: str = "") -> str:
    context_str = "\n".join([f"[{c.title}] {c.text}" for c in example.context])
    memory_str = "\n".join(reflection_memory) if reflection_memory else "None"
    user_prompt = f"Context:\n{context_str}\n\nReflection Memory:\n{memory_str}\n\nPlan:\n{plan}\n\nQuestion: {example.question}\n\nAnswer:"
    return call_openai(ACTOR_SYSTEM, user_prompt)

def evaluator(example: QAExample, answer: str) -> JudgeResult:
    sys_prompt = EVALUATOR_SYSTEM + "\nOutput a JSON object matching the JudgeResult schema (score, reason, missing_evidence, spurious_claims)."
    user_prompt = f"Gold Answer: {example.gold_answer}\nPredicted Answer: {answer}"
    content = call_openai(sys_prompt, user_prompt, json_format=True)
    try:
        data = json.loads(content)
        return JudgeResult(**data)
    except:
        return JudgeResult(score=0, reason="Failed to parse evaluator response.")

def reflector(example: QAExample, attempt_id: int, judge: JudgeResult) -> ReflectionEntry:
    sys_prompt = REFLECTOR_SYSTEM + "\nOutput a JSON object with 'lesson' and 'next_strategy'."
    context_str = "\n".join([f"[{c.title}] {c.text}" for c in example.context])
    user_prompt = f"Context:\n{context_str}\n\nQuestion: {example.question}\nFeedback: {judge.reason}\n\nProvide the reflection."
    content = call_openai(sys_prompt, user_prompt, json_format=True)
    try:
        data = json.loads(content)
        return ReflectionEntry(attempt_id=attempt_id, failure_reason=judge.reason, lesson=data.get("lesson", ""), next_strategy=data.get("next_strategy", ""))
    except:
        return ReflectionEntry(attempt_id=attempt_id, failure_reason=judge.reason, lesson="Error", next_strategy="Error")
