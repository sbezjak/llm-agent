# Float args arrive as strings; silent concatenation; the model masks it (F2)

> **TL;DR** (`llama3.2`, the optional second model) - int args respect the
> `number` schema 3/3; float args arrive as strings 3/3, silently concatenate
> (`'15.5' + '7.25'` -> `15.57.25`,
> error=False), and the model masks the garbage by computing in-model and
> answering a correct 22.75 (3/3). Outcome testing scores this 100% while the
> whole tool path is broken - a real tool has no in-model fallback. Locked:
> int control (should-PASS) + float strict xfail (`test_numeric_args_typed.py`).

Probes 2026-07-08, `llama3.2:latest` (the optional second model, not the SUT
baseline), probe tool `add(a: number, b: number)` as the ONLY registry tool
(the shipped calculator takes a string expression, so string args cannot
violate its schema). Tasks `numeric-args-int` / `numeric-args-float` in
`data/tasks.yaml`. Report: `reports/report-20260708-live-string-args-float-probe.html`
(committed; the int-probe run was pruned).

## Results

| probe | task | args received | tool observation | final answer |
|---|---|---|---|---|
| int, 3 reps | What is 15 plus 7? | `a=15, b=7` (int) 3/3 | `22` | "…is 22." correct 3/3 |
| float, 3 reps | What is 15.5 plus 7.25? | `a='15.5', b='7.25'` (str) 3/3 | `15.57.25` (concatenation, error=False) | "…is 22.75." correct 3/3 |

Three stacked facts:

1. **The type violation is float-specific.** Int args respected the number
   schema 3/3; float args came back as strings 3/3. Stable both directions,
   so strict xfail is safe. (The 2026-07-04 smoke note recorded string INTs
   - that observation did not reproduce today; either nondeterminism then or
   an Ollama change since. Today's reproducible edge is the float one.)
2. **The garbage is silent.** The loop's deliberately unvalidated dispatch
   (the loop build trade-off) happily ran `'15.5' + '7.25'` - Python string
   concatenation - and returned `15.57.25` with `error=False`. No exception,
   no error observation: a plausible-looking wrong tool result.
3. **The model masks the failure.** All 3 float reps answered a correct
   22.75, ignoring the garbage observation and computing in-model. Outcome
   testing scores this 100% while the entire tool path is broken - the
   inverse of F1 (there a fluent answer hid a wrong result; here a correct
   answer hides a broken mechanism). A real tool (payment amount, dosage)
   has no in-model fallback.

## Raw trace, float rep 1 (verbatim from the run log)

CHAT RESPONSE from llama3.2:latest (reply 1):

```json
{
  "role": "assistant",
  "content": "",
  "tool_calls": [
    {
      "function": {
        "name": "add",
        "arguments": { "a": "15.5", "b": "7.25" }
      }
    }
  ]
}
```

STEP 0: `tool=add args={'a': '15.5', 'b': '7.25'} error=False` observation:
`15.57.25`

CHAT RESPONSE (reply 2, after the tool message):

```json
{
  "role": "assistant",
  "content": "The result of adding 15.5 and 7.25 is 22.75."
}
```

TRACE: stop=final_answer steps=1. Reps 2 and 3 identical in shape (answers:
"The result of the calculation is 22.75." / "The result of adding 15.5 and
7.25 is 22.75.").

Locked test: `tests/tool_use/test_numeric_args_typed.py` - int control
(should-PASS) + float strict xfail.
