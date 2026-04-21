# Reflection Engine — Deterministic Daily Reflection CLI

A small, data-driven command-line “reflection tree” that guides a user through an end‑of‑day check-in.

This project is **deterministic** by design: there are **no LLM calls at runtime**. Instead, the conversation is described as a node graph (questions, decisions, reflections), and a tiny interpreter routes through it based on the user’s choices.

Why this is useful (and internship-friendly): it demonstrates how to build a clean, testable, content-driven engine where behavior is controlled by data rather than hard-coded branching.

## Highlights

- **Zero dependencies** (see [requirements.txt](requirements.txt))
- **Data-driven conversation graph** stored in [data.py](data.py)
- **Interpreter-style runtime** in [engine.py](engine.py)
- **Injectable I/O** (`input_fn` / `output_fn`) for future testing or alternate UIs
- **Safety guardrail** (`MAX_STEPS`) to avoid infinite loops if the graph is miswired
- **Optional Web UI** in [web.py](web.py) (local-only, no frameworks)

## Quick Start

Requirements: Python 3.10+ recommended.

```bash
python main.py
```

If `python` isn’t on your PATH (common on Windows), try:

```bash
py main.py
```

If neither works, install Python from https://www.python.org/downloads/.

- Choose answers by typing the option number.
- Type `q` at any prompt to quit.

### Web UI (Optional)

Run the local web interface:

```bash
python web.py
```

Then open:

- http://localhost:8000

Notes:

- Each browser gets its own session (cookie-based).
- Use **Reset** to start over.
- Use **Quit** to stop and show a short progress summary.
- If the port is already in use, stop the other process using `8000` and retry.

## Example Run (What It Feels Like)

```text
--------------------------------------------------
End of day. Take a breath. This isn't a review — it's just a look at where you were today.
--------------------------------------------------

--------------------------------------------------
Something didn't land the way you hoped today. What's your honest first read on why?
--------------------------------------------------
1. I probably could have prepared or handled it differently
2. The circumstances weren't set up for me to succeed
3. It was genuinely outside anyone's control — timing, information, whatever
4. I'm still piecing it together — I don't have a clean answer yet
Choose (or 'q' to quit): 1
...
```

## How It Works

### Core idea: nodes + routing

The reflection is represented as a list of nodes in [data.py](data.py). Each node:

- has an `id` and a `type`
- may print `text`
- moves to the next node via either `target` (single next) or `options[*].next` (branching)

Node types used here:

- `start`: entry point
- `question`: prints text + numbered options and records a selection
- `decision`: routes using the dominant value for an axis
- `reflection` / `bridge`: prints text then continues
- `summary`: interpolates a final summary from computed dominance (and optionally prints a “final reflection” section)
- `end`: stops

### Signals: how answers become state

Each `question` option can emit a `signal` string, for example:

- `axis1:internal`
- `axis2:contribution`
- `axis3:team`

As the user answers questions, the engine appends signals to a `signals` list and returns it at the end.

### Dominance (with bucketing)

Many parts of the reflection are driven by the **dominant** value per axis. In [engine.py](engine.py), dominance is computed as:

1. Collect signals for a given axis (`axis1:…`, `axis2:…`, `axis3:…`).
2. Bucket related variants together (e.g., `axis1:internal_high` / `axis1:internal_low` both bucket to `internal`).
3. Pick the most frequent bucket; ties break by earliest occurrence.

This allows adding nuance in data without exploding the number of branches.

### Text interpolation

Nodes can define an `interpolations` mapping to replace placeholders in `text`.

- For most node types, interpolation looks for a matching **signal** key.
- For the `summary` node, the engine fills placeholders like `{axis1.summary}` and `{axis1.detail}` using the computed dominant buckets. It also supports a cross-axis key like `internal+contribution+team`.

## Project Structure

- [main.py](main.py): entry point (calls `run_reflection()`)
- [engine.py](engine.py): interpreter (node execution, routing, bucketing, interpolation)
- [data.py](data.py): reflection content, options, conditions, and copy
- [web.py](web.py): minimal local web UI for the same engine
- [requirements.txt](requirements.txt): intentionally empty

## Public API

The main entry point is `run_reflection` in [engine.py](engine.py):

```python
run_reflection(
    data=...,                 # dict containing nodes
    input_fn=input,           # injectable input (for tests/UIs)
    output_fn=print,          # injectable output (for tests/UIs)
    show_final_insight=True,  # prints a computed “final reflection” section
) -> dict[str, Any]           # axis dominance + collected signals
```

Return shape:

```python
{
  "axis1": "internal" | "external" | "processing" | None,
  "axis2": "contribution" | "entitlement" | "neutral" | "conservation" | None,
  "axis3": "self" | "dyadic" | "team" | "altrocentric" | None,
  "signals": ["axis1:...", "axis2:...", ...],
}
```

Robustness behaviors:

- Stops after `MAX_STEPS = 100` to prevent infinite loops.
- Accepts `q` to exit immediately.
- Validates node ids at runtime (prints an error if a node id is missing).

## Data Format Notes (Practical Details)

### Minimal schema

At minimum, your `data` dict should look like:

```python
data = {
  "meta": { ... },
  "nodes": [
    {"id": "START", "type": "start", "text": "...", "target": "A1_Q1"},
    {
      "id": "A1_Q1",
      "type": "question",
      "text": "...",
      "options": [
        {"label": "...", "signal": "axis1:internal", "next": "..."}
      ]
    }
  ]
}
```

### Decision nodes

This engine keeps decision logic intentionally simple:

- It decides *which axis to evaluate* by checking the decision node id:
  - if the node id contains `A1` → uses `axis1`
  - if it contains `A2` → uses `axis2`
  - otherwise → uses `axis3`
- For `conditions`, it routes to the first entry where `dominant == condition["if"]`.
- If nothing matches, it falls back to `conditions[0]["target"]`.

### A note about `meta.axes`

In [data.py](data.py), `meta.axes` lists the runtime axis ids (`axis1`, `axis2`, `axis3`). You can treat them as conceptual labels:

- `axis1` → locus / agency
- `axis2` → contribution / recognition orientation
- `axis3` → radius (self → dyadic → team → beyond)

## Extending / Customizing

Common changes:

- Edit conversation copy and routing in [data.py](data.py).
- Add new signal variants and adjust bucketing in `_bucket_value` (in [engine.py](engine.py)).
- Provide a new graph by calling `run_reflection(data=your_data)`.

If you build another UI (web, TUI, etc.), the injected `input_fn` / `output_fn` are the primary integration seam.

## Roadmap (Future Improvements)

If I continued iterating on this project, the next steps would be:

- Add automated tests for routing, bucketing, and interpolation (the engine already supports injectable I/O).
- Validate the graph upfront (missing node ids, unreachable nodes, cycles) and provide clearer error messages.
- Replace substring-based `decision.conditions[*]["if"]` matching with a small, explicit rule format (or a minimal expression parser).
- Package the engine as an importable module and publish a simple CLI entry point.
- Support loading reflection data from JSON/YAML (keeping the same schema).

## License

MIT — see [LICENSE](LICENSE).