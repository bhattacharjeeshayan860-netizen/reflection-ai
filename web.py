from http.server import BaseHTTPRequestHandler, HTTPServer
import html as html_lib
import re
import secrets
import urllib.parse

from engine import run_reflection

PORT = 8000
MAX_CHOICES = 60  # safety: prevents runaway sessions

# Store session state (single-user by default)
sessions: dict[str, dict] = {}


class WebIO:
    def __init__(self, choices: list[str]):
        self.buffer: list[str] = []
        self._choices = choices
        self._idx = 0

    def output(self, text: str) -> None:
        self.buffer.append(text)

    def input(self, prompt: str) -> str:
        if self._idx < len(self._choices):
            value = self._choices[self._idx]
            self._idx += 1
            return str(value)
        return "q"


def _get_session(session_id: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = {
            "history": [],
            "last_output": [],
            "ended": False,
        }
    return sessions[session_id]


def _parse_cookies(cookie_header: str | None) -> dict[str, str]:
    if not cookie_header:
        return {}
    result: dict[str, str] = {}
    for part in cookie_header.split(";"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        result[k.strip()] = v.strip()
    return result


def _new_session_id() -> str:
    return secrets.token_urlsafe(12)


_OPTION_RE = re.compile(r"^\s*(\d+)\.\s+(.*)\s*$")


def _extract_options(lines: list[str]) -> list[tuple[str, str]]:
    options: list[tuple[str, str]] = []
    for line in lines:
        match = _OPTION_RE.match(line)
        if match:
            options.append((match.group(1), match.group(2)))
    return options


def _render_session_output(session: dict) -> None:
    io = WebIO(session["history"])
    run_reflection(
        input_fn=io.input,
        output_fn=io.output,
        show_final_insight=True,
    )

    # UI-only cleanup: on partial runs we auto-send "q" once history runs out;
    # hide the engine's quit message so the page still looks like a prompt.
    session["last_output"] = [
        line for line in io.buffer if line.strip() not in {"Exited manually."}
    ]


_SEP = "-" * 50


def _flatten_lines(buffer: list[str]) -> list[str]:
    lines: list[str] = []
    for entry in buffer:
        if entry is None:
            continue
        text = str(entry).replace("\r\n", "\n")
        parts = text.split("\n")
        for part in parts:
            # Preserve empty lines, but normalize separator line formatting
            cleaned = part
            if cleaned.startswith(_SEP):
                cleaned = _SEP
            lines.append(cleaned)
    return lines


def _compact_view(full_output: list[str]) -> tuple[list[str], list[tuple[str, str]]]:
    flat = _flatten_lines(full_output)
    all_options = _extract_options(flat)

    if all_options:
        # Find the last contiguous options block.
        last_opt_idx = None
        for i in range(len(flat) - 1, -1, -1):
            if _OPTION_RE.match(flat[i] or ""):
                last_opt_idx = i
                break

        if last_opt_idx is None:
            return flat[-30:], all_options

        # If the run finished, the transcript still contains old option lines.
        # Detect a final reflection/end marker *after* the last options line and
        # switch to an end-of-flow view with no options.
        tail_after_opts = flat[last_opt_idx + 1 :]
        if any("FINAL REFLECTION" in (ln or "") for ln in tail_after_opts) or any(
            "That's it. See you tomorrow." in (ln or "") for ln in tail_after_opts
        ):
            eq = "=" * 50
            if any((ln or "").strip() == eq for ln in flat):
                k = max(i for i, ln in enumerate(flat) if (ln or "").strip() == eq)
                start = max(0, k - 3)
                return flat[start:], []

            k = max(i for i, ln in enumerate(flat) if "FINAL REFLECTION" in (ln or ""))
            start = max(0, k - 4)
            return flat[start:], []

        start_opt_idx = last_opt_idx
        while start_opt_idx - 1 >= 0 and _OPTION_RE.match(flat[start_opt_idx - 1] or ""):
            start_opt_idx -= 1

        # Walk backwards to include the nearest question block delimited by separators.
        sep_count = 0
        start_idx = start_opt_idx
        for j in range(start_opt_idx - 1, -1, -1):
            if (flat[j] or "").strip() == _SEP:
                sep_count += 1
                if sep_count >= 2:
                    start_idx = j
                    break

        block = [ln for ln in flat[start_idx:last_opt_idx + 1] if (ln is not None)]
        # IMPORTANT: only return options from the *current* block
        block_options = _extract_options(block)
        return block, block_options

    # No options → likely summary/end. Show a clean tail, preferring the final reflection section.
    # Prefer starting from the final reflection header block printed by engine.py.
    eq = "=" * 50
    if any((ln or "").strip() == eq for ln in flat):
        k = max(i for i, ln in enumerate(flat) if (ln or "").strip() == eq)
        # Include a little context above the separator if present.
        start = max(0, k - 3)
        return flat[start:], []

    key = "FINAL REFLECTION"
    if any(key in (ln or "") for ln in flat):
        k = max(i for i, ln in enumerate(flat) if key in (ln or ""))
        start = max(0, k - 4)
        return flat[start:], []

    # Fallback tail.
    return flat[-40:], []


def _current_option_numbers(session: dict) -> set[str]:
    _render_session_output(session)
    _, options = _compact_view(session["last_output"])
    return {n for n, _ in options}


def _push_flash(session: dict, message: str) -> None:
    session.setdefault("flash", [])
    session["flash"].append(message)


def _compute_progress(session: dict) -> dict:
    # Compute dominance from answers so far without advancing further.
    io = WebIO(session["history"])
    result = run_reflection(
        input_fn=io.input,
        output_fn=lambda _text: None,
        show_final_insight=False,
    )
    return result


class Handler(BaseHTTPRequestHandler):

    def _get_or_create_session(self) -> tuple[str, dict, bool]:
        cookies = _parse_cookies(self.headers.get("Cookie"))
        session_id = cookies.get("rid")
        is_new = False
        if not session_id:
            session_id = _new_session_id()
            is_new = True
        session = _get_session(session_id)
        return session_id, session, is_new

    def do_GET(self):
        session_id, session, is_new = self._get_or_create_session()

        # First-load: generate the initial prompt + options.
        if not session["last_output"]:
            _render_session_output(session)

        if session.get("ended"):
            view_lines = _flatten_lines(session["last_output"])
            options: list[tuple[str, str]] = []
            progress = None
        else:
            view_lines, options = _compact_view(session["last_output"])
            progress = _compute_progress(session)

        flash_messages: list[str] = session.pop("flash", []) if session.get("flash") else []

        answers = len(session.get("history", []))
        signals_count = len(progress.get("signals", [])) if progress else 0
        total_ticks = 10
        filled_ticks = min(total_ticks, answers)
        ticks_html = "".join(
            f"<div class=\"tick{' filled' if i < filled_ticks else ''}\"></div>" for i in range(total_ticks)
        )

        page = f"""
        <html>
        <head>
            <title>Reflection UI</title>
            <style>
                body {{
                    font-family: Arial;
                    background: #0f172a;
                    color: #e2e8f0;
                    max-width: 700px;
                    margin: auto;
                    padding: 20px;
                }}
                h1 {{
                    margin: 0 0 8px;
                }}
                .box {{
                    background: #1e293b;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                }}
                .panel {{
                    background: #0b1220;
                    border: 1px solid #334155;
                    border-radius: 10px;
                    padding: 12px 14px;
                    margin: 12px 0 16px;
                }}
                .panel-title {{
                    font-weight: 700;
                    margin-bottom: 8px;
                }}
                .ticks {{
                    display: flex;
                    gap: 6px;
                    margin: 10px 0 8px;
                }}
                .tick {{
                    flex: 1;
                    height: 10px;
                    background: #1e293b;
                    border-radius: 999px;
                }}
                .tick.filled {{
                    background: #3b82f6;
                }}
                .grid {{
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 8px 14px;
                }}
                .topbar {{
                    display: flex;
                    gap: 10px;
                    margin: 10px 0 16px;
                }}
                .topbar form {{
                    margin: 0;
                }}
                .muted {{
                    color: #94a3b8;
                    font-size: 0.95rem;
                }}
                .flash {{
                    background: rgba(239, 68, 68, 0.12);
                    border: 1px solid rgba(239, 68, 68, 0.45);
                    padding: 10px 12px;
                    border-radius: 10px;
                    margin-bottom: 12px;
                }}
                .line {{
                    margin: 0.35rem 0;
                    white-space: pre-wrap;
                }}
                .options {{
                    display: grid;
                    gap: 10px;
                    margin-top: 14px;
                }}
                button {{
                    width: 100%;
                    padding: 12px;
                    margin: 5px 0;
                    border: none;
                    border-radius: 6px;
                    background: #3b82f6;
                    color: white;
                    cursor: pointer;
                    text-align: left;
                }}
                button:hover {{
                    background: #2563eb;
                }}
                .input-row {{
                    display: flex;
                    gap: 10px;
                    margin-top: 14px;
                }}
                input {{
                    flex: 1;
                    padding: 10px;
                    border-radius: 8px;
                    border: 1px solid #334155;
                    background: #0b1220;
                    color: #e2e8f0;
                }}
                .submit {{
                    width: auto;
                    min-width: 140px;
                    text-align: center;
                }}
                .danger {{
                    background: #ef4444;
                }}
                .danger:hover {{
                    background: #dc2626;
                }}
                .secondary {{
                    background: #334155;
                }}
                .secondary:hover {{
                    background: #475569;
                }}
            </style>
        </head>
        <body>
            <h1>Daily Reflection</h1>
            <div class="muted">Fast, deterministic reflection — no LLM calls.</div>
            <div class="topbar">
                <form method="POST">
                    <button class="secondary" type="submit" name="action" value="reset">Reset</button>
                </form>
                <form method="POST">
                    <button class="danger" type="submit" name="action" value="quit">Quit</button>
                </form>
            </div>

            <div class="panel">
                <div class="panel-title">Progress</div>
                <div class="muted">Answers so far</div>
                <div class="ticks">{ticks_html}</div>
                <div class="grid">
                    <div><span class="muted">Answers:</span> {answers}</div>
                    <div><span class="muted">Insights collected:</span> {signals_count}</div>
                </div>
            </div>

            <div class="box">
        """

        if flash_messages:
            page += "<div class=\"flash\">"
            for msg in flash_messages[-3:]:
                page += f"<div class=\"line\">{html_lib.escape(msg)}</div>"
            page += "</div>"

        for line in view_lines:
            page += f"<div class=\"line\">{html_lib.escape(line)}</div>"

        page += "</div>"

        if options:
            page += "<div class=\"muted\">Click an option, or type a number:</div>"
            page += "<form method=\"POST\" class=\"options\">"
            for number, label in options:
                page += (
                    f"<button type=\"submit\" name=\"choice\" value=\"{html_lib.escape(number)}\">"
                    f"{html_lib.escape(number)}. {html_lib.escape(label)}"
                    "</button>"
                )
            page += "</form>"
        else:
            if not session.get("ended"):
                page += "<div class=\"muted\">No more options — summary/end reached.</div>"

        page += """
            <form method="POST" class="input-row">
                <input name="choice" inputmode="numeric" autocomplete="off" placeholder="Enter option number (e.g. 1)">
                <button class="submit" type="submit">Submit</button>
            </form>
        """

        page += "</body></html>"

        self.send_response(200)
        if is_new:
            self.send_header("Set-Cookie", f"rid={session_id}; Path=/; SameSite=Lax")
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))

    def do_POST(self):
        session_id, session, is_new = self._get_or_create_session()

        length = int(self.headers['Content-Length'])
        body = self.rfile.read(length).decode()
        params = urllib.parse.parse_qs(body)

        action = params.get("action", [""])[0].strip().lower()
        if action == "reset":
            session["history"] = []
            session["last_output"] = []
            session["ended"] = False
            _render_session_output(session)
            self.send_response(303)
            if is_new:
                self.send_header("Set-Cookie", f"rid={session_id}; Path=/; SameSite=Lax")
            self.send_header("Location", "/")
            self.end_headers()
            return

        if action == "quit":
            progress = _compute_progress(session)
            session["ended"] = True
            session["last_output"] = [
                "PROGRESS SUMMARY",
                "--------------------------------------------------",
                f"answers: {len(session.get('history', []))}",
                f"insights collected: {len(progress.get('signals', []))}",
                "",
                "Use Reset to start over.",
            ]
            self.send_response(303)
            if is_new:
                self.send_header("Set-Cookie", f"rid={session_id}; Path=/; SameSite=Lax")
            self.send_header("Location", "/")
            self.end_headers()
            return

        choice = params.get("choice", [""])[0]

        choice = choice.strip()
        if choice == "":
            choice = "1"

        # Validate choice against the *current* options, so bad input doesn't mess up the session.
        valid_numbers = _current_option_numbers(session)
        if valid_numbers and choice not in valid_numbers:
            _push_flash(session, f"Invalid choice '{choice}'. Pick one of: {', '.join(sorted(valid_numbers, key=int))}.")
            self.send_response(303)
            if is_new:
                self.send_header("Set-Cookie", f"rid={session_id}; Path=/; SameSite=Lax")
            self.send_header("Location", "/")
            self.end_headers()
            return

        if len(session["history"]) >= MAX_CHOICES:
            session["last_output"] = [
                "Session paused to avoid an endless loop.",
                "Use Reset to start over.",
            ]
            self.send_response(303)
            if is_new:
                self.send_header("Set-Cookie", f"rid={session_id}; Path=/; SameSite=Lax")
            self.send_header("Location", "/")
            self.end_headers()
            return

        session["history"].append(choice)
        _render_session_output(session)

        self.send_response(303)
        if is_new:
            self.send_header("Set-Cookie", f"rid={session_id}; Path=/; SameSite=Lax")
        self.send_header("Location", "/")
        self.end_headers()


def run():
    print(f"Open http://localhost:{PORT}")
    try:
        HTTPServer(("localhost", PORT), Handler).serve_forever()
    except OSError as e:
        # Common on Windows when the port is already in use.
        print(f"Failed to bind to port {PORT}: {e}")
        print("If you already have a server running, stop it and retry.")


if __name__ == "__main__":
    run()