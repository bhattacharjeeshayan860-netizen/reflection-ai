# Reflection Engine (Deterministic Daily Reflection Tree)

A small, data-driven CLI that walks you through an end‑of‑day reflection. It’s **deterministic** (no LLM calls at runtime): the conversation is a directed graph of nodes (questions, reflections, decisions), and the engine routes you through it based on your selections.

This repo is intentionally lightweight:

- No external dependencies (see [requirements.txt](requirements.txt))
- The reflection content lives in a single data structure (see [data.py](data.py))
- The runtime is a small interpreter that executes that tree (see [engine.py](engine.py))

## Quick Start

Requirements: Python 3.10+ recommended.

Run:

```bash
python main.py
```

Quit any time by typing `q` when prompted.

## How It Works

### 1) Nodes define a reflection “tree” (actually a graph)

The reflection is represented as a list of nodes in [data.py](data.py). Each node has an `id` and a `type`, and points to the next node via either:

- `target` (single next node), or
- `options` (multiple choices; each option has a `next`)

Node types used here:

- `start`: entry point
- `question`: shows text + numbered options and collects a selection
- `decision`: routes based on the “dominant” signal for an axis
- `reflection` / `bridge`: displays text and continues
- `summary`: prints a computed summary + optional final insight
- `end`: stops

### 2) Options emit “signals”

Every `question` option can emit a `signal` like:

- `axis1:internal`
- `axis2:contribution`
- `axis3:team`

As you answer questions, the engine appends these signals to a `signals` list (returned by `run_reflection`).

### 3) Dominant axis values are computed (with bucketing)

Some node transitions and summary text depend on the **dominant** value per axis. The engine:

1. Filters signals by axis prefix (`axis1:`, `axis2:`, `axis3:`)
2. Buckets related values together (for example `axis1:internal_high` and `axis1:internal_low` both bucket to `internal`)
3. Picks the most frequent bucket; ties break by “first seen” (earlier answers win)

This makes the reflection stable and interpretable: you can add nuanced signals without exploding the number of branches.

### 4) Summaries interpolate text based on computed dominance

The `summary` node in [data.py](data.py) contains placeholders like `{axis1.summary}` and mappings under `interpolations`. The engine replaces placeholders using the dominant per axis (plus an optional cross‑axis key like `internal+contribution+team`).

Separately, there is also a built-in “final insight” printer that outputs a short, human-readable interpretation of the three axes.

## Project Layout

- [main.py](main.py): tiny entry point that calls `run_reflection()`
- [engine.py](engine.py): the reflection interpreter (node runner, routing, interpolation)
- [data.py](data.py): reflection content + branching rules as plain Python data
- [requirements.txt](requirements.txt): empty by design

## Engine API

The primary entry point is `run_reflection` in [engine.py](engine.py):

```python
run_reflection(
    data=...,                 # dict containing nodes
    input_fn=input,           # injectable for tests / UIs
    output_fn=print,          # injectable for tests / UIs
    show_final_insight=True,  # prints a computed “final reflection” section
) -> list[str]                # returns collected signals
```

Notable safety/robustness behaviors:

- A hard cap on steps (`MAX_STEPS = 100`) prevents infinite loops if the graph is miswired.
- Entering `q` exits cleanly.
- If a node id can’t be found, the engine prints an error and stops.

## Data Schema (What `data.py` Must Provide)

At minimum:

```python
data = {
  "meta": { ... },
  "nodes": [
    {
      "id": "START",
      "type": "start",
      "text": "...",
      "target": "A1_Q1",
    },
    {
      "id": "A1_Q1",
      "type": "question",
      "text": "...",
      "options": [
        {"label": "...", "signal": "axis1:internal", "next": "..."},
      ],
    },
    ...
  ]
}
```

Supported fields (as used in this project):

- `id` (string, required): unique node identifier
- `type` (string, required): `start`, `question`, `decision`, `reflection`, `bridge`, `summary`, `end`
- `text` (string, optional): printed when the node runs
- `target` (string, optional): next node id for non-question nodes
- `options` (list, for `question`): each option has `label`, optional `signal`, and `next`
- `conditions` (list, for `decision`): list of `{ "if": "...", "target": "..." }`
- `interpolations` (dict, optional): placeholder → mapping of signal/dominant keys to replacement text

Note: the engine’s `decision` logic is intentionally simple and currently assumes which axis to evaluate by checking the node id (it looks for `A1`, `A2`, otherwise treats it as `A3`). If you rename decision nodes, keep that convention or update the engine.

## Extending / Customizing

Common changes:

- Edit the reflection content, options, and routing in [data.py](data.py).
- Add new nuanced signals (e.g., `axis2:contribution_trusting`) and decide how they should bucket in `_bucket_value` in [engine.py](engine.py).
- Provide a new `data` dict at runtime by calling `run_reflection(data=your_data)`.

If you build a different UI (web, TUI, etc.), the injected `input_fn`/`output_fn` are the main integration seam.

## License

Add a license if you plan to distribute publicly.
