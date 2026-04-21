from __future__ import annotations

from typing import Any, Callable, Optional

from data import data as reflection_data


# ---------- SAFETY ----------

MAX_STEPS = 100  # prevents infinite loop


def _bucket_value(axis: str, value: str) -> str:
    if axis == "axis1":
        if value.startswith("internal") or value in {
            "growth", "growth_soft", "fixed", "shift_internal"
        }:
            return "internal"
        if value.startswith("external"):
            return "external"
        if value == "processing":
            return "processing"
        return value

    if axis == "axis2":
        if value.startswith("contribution"):
            return "contribution"
        if value.startswith("entitlement"):
            return "entitlement"
        if value in {"neutral", "conservation"}:
            return value
        return value

    # axis3
    if value in {"self", "self_confident"}:
        return "self"
    if value in {"dyadic", "curious_other"}:
        return "dyadic"
    if value in {"team", "systemic", "contribution_meaning"}:
        return "team"
    if value in {"altrocentric", "altrocentric_high", "identity_transcendent"}:
        return "altrocentric"
    return value


def _safe_pick(mapping: dict[str, str], key: Optional[str]) -> str:
    if key and key in mapping:
        return mapping[key]
    if "default" in mapping:
        return mapping["default"]
    return next(iter(mapping.values()), "")


def run_reflection(
    data: dict[str, Any] = reflection_data,
    *,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
    show_final_insight: bool = True,
) -> dict[str, Any]:

    nodes = {node["id"]: node for node in data["nodes"]}
    signals: list[str] = []
    current: Optional[str] = "START"

    steps = 0
    visited = set()  # NEW: loop detection

    def get_dominant(axis: str) -> Optional[str]:
        counts: dict[str, int] = {}
        first_seen: dict[str, int] = {}

        prefix = axis + ":"
        for idx, sig in enumerate(signals):
            if not sig.startswith(prefix):
                continue
            raw_value = sig.split(":", 1)[1]
            bucket = _bucket_value(axis, raw_value)
            counts[bucket] = counts.get(bucket, 0) + 1
            first_seen.setdefault(bucket, idx)

        if not counts:
            return None

        return max(counts.keys(), key=lambda k: (counts[k], -first_seen[k]))

    def render_text(node: dict[str, Any]) -> str:
        text = node.get("text", "")

        if "interpolations" in node:
            for placeholder, mapping in node["interpolations"].items():
                if node.get("type") == "summary" and placeholder.startswith("axis"):
                    continue

                for sig in signals:
                    if sig in mapping:
                        text = text.replace("{" + placeholder + "}", mapping[sig])
                        break

        if node.get("type") == "summary" and "interpolations" in node:
            dom1 = get_dominant("axis1")
            dom2 = get_dominant("axis2")
            dom3 = get_dominant("axis3")

            interp = node["interpolations"]
            replacements = {
                "axis1.summary": _safe_pick(interp.get("axis1.summary", {}), dom1),
                "axis1.detail":  _safe_pick(interp.get("axis1.detail",  {}), dom1),
                "axis2.summary": _safe_pick(interp.get("axis2.summary", {}), dom2),
                "axis2.detail":  _safe_pick(interp.get("axis2.detail",  {}), dom2),
                "axis3.summary": _safe_pick(interp.get("axis3.summary", {}), dom3),
                "axis3.detail":  _safe_pick(interp.get("axis3.detail",  {}), dom3),
            }

            cross_key = f"{dom1}+{dom2}+{dom3}" if (dom1 and dom2 and dom3) else None
            replacements["cross_axis_insight"] = _safe_pick(
                interp.get("cross_axis_insight", {}),
                cross_key,
            )

            for placeholder, value in replacements.items():
                text = text.replace("{" + placeholder + "}", value)

        return text

    def get_input(options: list[dict[str, Any]]) -> Optional[int]:
        while True:
            user_input = input_fn("Choose (or 'q' to quit): ")

            if user_input.lower() == "q":
                output_fn("\nExited manually.")
                return None

            try:
                choice = int(user_input)
                if 1 <= choice <= len(options):
                    return choice - 1
            except ValueError:
                pass

            output_fn("Invalid input. Try again.")

    def print_final_insight() -> None:
        a1 = get_dominant("axis1")
        a2 = get_dominant("axis2")
        a3 = get_dominant("axis3")

        output_fn("\n" + "=" * 50)
        output_fn("\nBased on your responses today:")
        output_fn("FINAL REFLECTION")
        output_fn("=" * 50)

        if a1 == "internal":
            output_fn("\nYou tended to take ownership of what happened.")
        elif a1 == "external":
            output_fn("\nYou experienced the situation as the main constraint.")
        else:
            output_fn("\nYou're still processing what happened — which is valid.")

        if a2 == "contribution":
            output_fn("You focused on contributing rather than being recognized.")
        elif a2 == "entitlement":
            output_fn("You were tracking recognition and fairness today.")
        elif a2 == "neutral":
            output_fn("You showed up and did what was needed consistently.")
        else:
            output_fn("You were managing your energy and pulling back when needed.")

        if a3 == "self":
            output_fn("Your focus stayed mostly on your own workload.")
        elif a3 == "team":
            output_fn("You were thinking beyond yourself and considering others.")
        else:
            output_fn("You connected your day to something larger than yourself.")

        output_fn("\n--- Insight ---")

        if a1 == "internal" and a2 == "contribution":
            output_fn("You owned your actions and contributed — strong foundation for growth.")
        elif a1 == "external" and a2 == "entitlement":
            output_fn("You may be feeling a gap between effort and recognition — worth reflecting on.")
        elif a3 == "self":
            output_fn("Consider expanding your perspective slightly tomorrow — even one interaction can shift your day.")
        else:
            output_fn("Notice the gap between how you showed up and how you want to show up tomorrow.")

        output_fn("_" * 50)

    # ---------- MAIN LOOP ----------

    while current is not None and steps < MAX_STEPS:
        steps += 1

        # NEW: loop detection
        if current in visited:
            output_fn(f"\nError: Loop detected at node '{current}'.")
            break
        visited.add(current)

        if current not in nodes:
            output_fn(f"\nError: Node '{current}' not found.")
            break

        node = nodes[current]

        if node.get("type") == "end":
            output_fn("\n" + "-" * 50)
            output_fn(node.get("text", "Done."))
            output_fn("-" * 50)
            break

        text = render_text(node)
        if text:
            output_fn("\n" + "-" * 50)
            output_fn(text)
            output_fn("-" * 50)

        if node.get("type") == "question":
            for i, opt in enumerate(node.get("options") or []):
                output_fn(f"{i + 1}. {opt['label']}")

            idx = get_input(node["options"])
            if idx is None:
                break

            selected = node["options"][idx]
            if selected.get("signal"):
                signals.append(selected["signal"])

            current = selected["next"]

        elif node.get("type") == "decision":
            conditions = node.get("conditions") or []

            if not conditions:
                current = node.get("target")
            else:
                node_id = node["id"]

                if "A1" in node_id:
                    dom = get_dominant("axis1")
                elif "A2" in node_id:
                    dom = get_dominant("axis2")
                else:
                    dom = get_dominant("axis3")

                matched = False

                for cond in conditions:
                    if dom is not None and dom == cond["if"]:
                        current = cond["target"]
                        matched = True
                        break

                if not matched:
                    current = conditions[0]["target"]

        else:
            if show_final_insight and node.get("type") == "summary":
                print_final_insight()
            current = node.get("target")

    if steps >= MAX_STEPS:
        output_fn("\nStopped: Too many steps (possible loop issue).")

    # ✅ STRUCTURED RETURN
    return {
        "axis1": get_dominant("axis1"),
        "axis2": get_dominant("axis2"),
        "axis3": get_dominant("axis3"),
        "signals": signals,
    }