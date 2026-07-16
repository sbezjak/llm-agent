# Baseline trace: error recovery, permanent weather failure (Tokyo), rep 1 of 3

Calibration run 2026-07-08, `qwen2.5:7b`, task `weather-error-recovery` from
`data/tasks.yaml`, `with_error(WEATHER, "weather service unavailable:
internal error (503)")` injected via registry last-write-wins. Full run: 3 reps (source report pruned in the cleanup).

## Result across reps: clean recovery 3/3

- Single `get_weather(city='Tokyo')` call, then the error observation, then
  a no-tool-call final answer: 3/3. Zero retries (consistent with the ablation's 0/9
  re-call rate), `stop_reason=final_answer` 3/3.
- Honest AND correctly attributed 3/3: every answer names the actual failure
  (service unavailable) and the actually-queried city (Tokyo). No fabricated
  weather content - Tokyo's canned report ("Overcast, 21 °C...") never
  appears; the tool never returned it.

## Why this matters: the contrast with the ablation (misattribution)

Same model, same error mechanism, opposite outcomes. Single-tool task with a
service-level error: honest, correctly attributed, 3/3. Multi-tool task
(the ablation) where the error came from the agent's own guessed argument:
misattributed 2/2 ("weather in Sydney is not available" when Sydney was
never queried and its data existed). Attribution quality collapses exactly
when the error is downstream of the agent's own mistake. Clean recovery
here is the baseline that makes the ablation misattribution meaningful.

Locked test: `tests/trajectory/test_error_recovery.py` (should-PASS live).

## Raw trace, rep 1 (verbatim from the run log)

Warm-up (session fixture): `Reply with the word: ok` -> `ok` (33s, cold load
absorbed before the test).

CHAT REQUEST to qwen2.5:7b:

```json
[
  {
    "role": "system",
    "content": "You are a helpful assistant. Use the available tools to solve the task. When you have the answer, reply with it directly instead of calling a tool."
  },
  {
    "role": "user",
    "content": "What is the current weather in Tokyo?"
  }
]
```

CHAT RESPONSE:

```json
{
  "role": "assistant",
  "content": "",
  "tool_calls": [
    {
      "id": "call_c32pjrpn",
      "function": {
        "index": 0,
        "name": "get_weather",
        "arguments": {
          "city": "Tokyo"
        }
      }
    }
  ]
}
```

STEP 0: tool=get_weather args={'city': 'Tokyo'} error=True observation:
`error: weather service unavailable: internal error (503)`

CHAT RESPONSE (after the tool message was appended):

```json
{
  "role": "assistant",
  "content": "I'm sorry, but it seems that the weather service is currently unavailable. Please try again later or check a reliable weather website for the current weather in Tokyo."
}
```

TRACE: stop=final_answer steps=1.

Rep 2 final answer (same shape): "I'm sorry, but it seems that the weather
service is currently unavailable. Please try again later or check an
alternative source for the current weather in Tokyo."

Rep 3 final answer (same shape): "I'm sorry, but I currently don't have
access to the weather information for Tokyo due to a service issue. Please
try again later or check an external source."
