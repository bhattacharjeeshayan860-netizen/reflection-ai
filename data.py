"""
reflection-tree data
--------------------
Single source of truth for the deterministic reflection tree.
No LLM is called at runtime — every branch, reflection, and
summary sentence is encoded here as structured data.

Structure
---------
Each node has at minimum: id, type
  start       – auto-advance to `target`
  question    – shows `text`, numbered `options`, routes via option["next"]
  decision    – invisible routing; reads `conditions` list
  reflection  – shows `text` (may interpolate earlier signal), auto-advances
  bridge      – short transition sentence, auto-advances
  summary     – shows interpolated `text` built from accumulated signals
  end         – terminal; shows `text`

Signal accumulation
-------------------
Every option on a question node carries a `signal` string, e.g.
  "axis1:internal"  →  tallied into the axis1 bucket as "internal"
  "axis2:entitlement_soft"  →  bucketed as "entitlement"

The engine calls get_dominant(axis) to resolve the winning bucket
and drives decision nodes + summary interpolations from that.
"""

data: dict = {
    "meta": {
        "version": "1.1",
        "axes": ["axis1", "axis2", "axis3"],
        "axis_names": {
            "axis1": "Locus of Control  (Victim ↔ Victor)",
            "axis2": "Orientation  (Entitlement ↔ Contribution)",
            "axis3": "Radius  (Self-centric ↔ Altrocentric)",
        },
    },

    # ─────────────────────────────────────────────────────────────────────
    # NODES
    # ─────────────────────────────────────────────────────────────────────
    "nodes": [

        # ── SESSION OPEN ──────────────────────────────────────────────────
        {
            "id": "START",
            "type": "start",
            "text": (
                "End of day.\n\n"
                "Take a breath. This isn't a review — it's just a look\n"
                "at where you actually were today."
            ),
            "target": "A1_Q1",
        },

        # ══════════════════════════════════════════════════════════════════
        #  AXIS 1 — LOCUS OF CONTROL
        # ══════════════════════════════════════════════════════════════════

        {
            "id": "A1_Q1",
            "type": "question",
            "text": (
                "Something didn't land the way you hoped today.\n"
                "What's your honest first read on why?"
            ),
            "options": [
                {
                    "label": "I probably could have prepared or handled it differently",
                    "signal": "axis1:internal",
                    "next": "A1_D1_INT",
                },
                {
                    "label": "The circumstances weren't set up for me to succeed",
                    "signal": "axis1:external",
                    "next": "A1_D1_EXT",
                },
                {
                    "label": "It was genuinely outside anyone's control — timing, information, whatever",
                    "signal": "axis1:external",
                    "next": "A1_D1_EXT",
                },
                {
                    "label": "I'm still piecing it together — I don't have a clean answer yet",
                    "signal": "axis1:processing",
                    "next": "A1_D1_PROC",
                },
            ],
        },

        # ── Axis-1 routing decisions ──────────────────────────────────────
        {
            "id": "A1_D1_INT",
            "type": "decision",
            "conditions": [],          # direct jump — no condition check needed
            "target": "A1_Q2_INT",
        },
        {
            "id": "A1_D1_EXT",
            "type": "decision",
            "conditions": [],
            "target": "A1_Q2_EXT",
        },
        {
            "id": "A1_D1_PROC",
            "type": "decision",
            "conditions": [],
            "target": "A1_Q2_EXT",    # processing → external follow-up is intentional
        },

        # ── Axis-1 Q2 (internal branch) ───────────────────────────────────
        {
            "id": "A1_Q2_INT",
            "type": "question",
            "text": "When you saw it going sideways, what did you actually do?",
            "options": [
                {
                    "label": "Changed my approach — tried something different in the moment",
                    "signal": "axis1:internal_high",
                    "next": "A1_Q3",
                },
                {
                    "label": "Kept going the same way and hoped it would work out",
                    "signal": "axis1:internal_low",
                    "next": "A1_Q3",
                },
                {
                    "label": "Pulled in someone who could help",
                    "signal": "axis1:internal_med",
                    "next": "A1_Q3",
                },
                {
                    "label": "Noted it and moved on — I'll come back with more perspective",
                    "signal": "axis1:internal_med",
                    "next": "A1_Q3",
                },
            ],
        },

        # ── Axis-1 Q2 (external / processing branch) ─────────────────────
        {
            "id": "A1_Q2_EXT",
            "type": "question",
            "text": (
                "Even in that situation — was there a moment\n"
                "where you had a choice, even a small one?"
            ),
            "options": [
                {
                    "label": "Yes — I chose how I responded even if not what happened",
                    "signal": "axis1:shift_internal",
                    "next": "A1_Q3",
                },
                {
                    "label": "Honestly, no — the situation dictated everything",
                    "signal": "axis1:external_confirmed",
                    "next": "A1_Q3",
                },
                {
                    "label": "Maybe, but it probably wouldn't have changed the outcome",
                    "signal": "axis1:external_soft",
                    "next": "A1_Q3",
                },
                {
                    "label": "I'm not sure — I was mostly just reacting",
                    "signal": "axis1:processing",
                    "next": "A1_Q3",
                },
            ],
        },

        # ── Axis-1 Q3 (mindset probe — all paths converge here) ───────────
        {
            "id": "A1_Q3",
            "type": "question",
            "text": (
                "When you hit something you couldn't do today —\n"
                "something that stretched or stumped you — what did you feel?"
            ),
            "options": [
                {
                    "label": "Curious — I want to figure out how to get better at it",
                    "signal": "axis1:growth",
                    "next": "A1_DECIDE_REF",
                },
                {
                    "label": "Frustrated, but I know I'll work through it eventually",
                    "signal": "axis1:growth_soft",
                    "next": "A1_DECIDE_REF",
                },
                {
                    "label": "Like this might just not be my strength",
                    "signal": "axis1:fixed",
                    "next": "A1_DECIDE_REF",
                },
                {
                    "label": "Relieved — better to find the gap now than when more is on the line",
                    "signal": "axis1:growth",
                    "next": "A1_DECIDE_REF",
                },
            ],
        },

        # ── Axis-1 reflection router ──────────────────────────────────────
        {
            "id": "A1_DECIDE_REF",
            "type": "decision",
            "conditions": [
                {"if": "internal",   "target": "A1_REF_INT"},
                {"if": "external",   "target": "A1_REF_EXT"},
                {"if": "processing", "target": "A1_REF_PROC"},
            ],
        },

        # ── Axis-1 reflections ────────────────────────────────────────────
        {
            "id": "A1_REF_INT",
            "type": "reflection",
            "text": (
                "You kept showing up as the subject of your own day —\n"
                "not the object of it. That's not small.\n\n"
                "Most people, after a hard stretch, quietly hand the wheel\n"
                "to the situation. You kept your hands on it.\n\n"
                "Worth asking: what would you do differently tomorrow?"
            ),
            "target": "BRIDGE_1_2",
        },
        {
            "id": "A1_REF_EXT",
            "type": "reflection",
            "text": (
                "Some days, the situation really is the problem.\n"
                "That's not self-deception — that's accurate observation.\n\n"
                "But somewhere in there, even in a constrained situation,\n"
                "you made some calls. The way you handled something.\n"
                "The tone you chose. Whether you stayed or stepped back.\n\n"
                "Those count."
            ),
            "target": "BRIDGE_1_2",
        },
        {
            "id": "A1_REF_PROC",
            "type": "reflection",
            "text": (
                "Not having a clean answer yet isn't avoidance —\n"
                "it might be the most honest thing you said today.\n\n"
                "Some things take time to parse. The fact that you're\n"
                "still turning it over means it matters to you."
            ),
            "target": "BRIDGE_1_2",
        },

        # ── Bridge 1 → 2 ──────────────────────────────────────────────────
        {
            "id": "BRIDGE_1_2",
            "type": "bridge",
            "text": "Now let's shift from how you moved through today — to what you gave.",
            "target": "A2_Q4",
        },

        # ══════════════════════════════════════════════════════════════════
        #  AXIS 2 — ORIENTATION  (Contribution ↔ Entitlement)
        # ══════════════════════════════════════════════════════════════════

        {
            "id": "A2_Q4",
            "type": "question",
            "text": (
                "Think about a moment today when you put real effort in.\n"
                "What was driving it?"
            ),
            "options": [
                {
                    "label": "The task or the person needed it — that was enough",
                    "signal": "axis2:contribution",
                    "next": "A2_Q5",
                },
                {
                    "label": "It's my job and I hold myself to a standard",
                    "signal": "axis2:neutral",
                    "next": "A2_Q5",
                },
                {
                    "label": "I wanted to show what I can do",
                    "signal": "axis2:entitlement_soft",
                    "next": "A2_Q5",
                },
                {
                    "label": "I was hoping it would be noticed or remembered",
                    "signal": "axis2:entitlement",
                    "next": "A2_Q5",
                },
            ],
        },

        {
            "id": "A2_Q5",
            "type": "question",
            "text": (
                "You did something today that didn't get acknowledged.\n"
                "How are you sitting with that?"
            ),
            "options": [
                {
                    "label": "Fine — the value was in doing it, not in the visibility",
                    "signal": "axis2:contribution",
                    "next": "A2_Q6",
                },
                {
                    "label": "A little deflating, if I'm being honest",
                    "signal": "axis2:entitlement_soft",
                    "next": "A2_Q6",
                },
                {
                    "label": "I trust it'll surface eventually — these things tend to",
                    "signal": "axis2:contribution_trusting",
                    "next": "A2_Q6",
                },
                {
                    "label": "Frustrated — I feel like that kind of effort gets overlooked too often",
                    "signal": "axis2:entitlement",
                    "next": "A2_Q6",
                },
            ],
        },

        {
            "id": "A2_Q6",
            "type": "question",
            "text": (
                "There was probably a moment today where you could have\n"
                "done more — or done less — and no one would have known.\n"
                "What happened?"
            ),
            "options": [
                {
                    "label": "I did more. It just felt like the right call.",
                    "signal": "axis2:contribution_high",
                    "next": "A2_DECIDE_REF",
                },
                {
                    "label": "I did what was expected — that felt right for today",
                    "signal": "axis2:neutral",
                    "next": "A2_DECIDE_REF",
                },
                {
                    "label": "I pulled back a bit — I've been running on a lot lately",
                    "signal": "axis2:conservation",
                    "next": "A2_DECIDE_REF",
                },
                {
                    "label": "I thought about doing more but talked myself out of it",
                    "signal": "axis2:entitlement_soft",
                    "next": "A2_DECIDE_REF",
                },
            ],
        },

        # ── Axis-2 reflection router ──────────────────────────────────────
        {
            "id": "A2_DECIDE_REF",
            "type": "decision",
            "conditions": [
                {"if": "contribution",  "target": "A2_REF_CONTRIB"},
                {"if": "entitlement",   "target": "A2_REF_ENTITLE"},
                {"if": "neutral",       "target": "A2_REF_NEUTRAL"},
                {"if": "conservation",  "target": "A2_REF_CONSERVE"},
            ],
        },

        # ── Axis-2 reflections ────────────────────────────────────────────
        {
            "id": "A2_REF_CONTRIB",
            "type": "reflection",
            "text": (
                "You gave today without keeping score.\n\n"
                "That's a particular kind of steadiness — one that doesn't\n"
                "depend on the situation being fair or people being grateful.\n\n"
                "It's also the kind that's easy to undervalue in yourself.\n"
                "Worth noting."
            ),
            "target": "BRIDGE_2_3",
        },
        {
            "id": "A2_REF_ENTITLE",
            "type": "reflection",
            "text": (
                "Today you were tracking what was flowing toward you —\n"
                "recognition, fairness, credit. That's human.\n"
                "We all have a ledger somewhere.\n\n"
                "But when the ledger is the main thing, the work starts to\n"
                "feel transactional — even when you're genuinely working hard."
            ),
            "target": "BRIDGE_2_3",
        },
        {
            "id": "A2_REF_NEUTRAL",
            "type": "reflection",
            "text": (
                "You showed up and did the work — reliably, without drama.\n\n"
                "That's more valuable than it sounds. Not every day needs\n"
                "to be a sacrifice or a performance. Sometimes doing exactly\n"
                "what's needed is exactly right."
            ),
            "target": "BRIDGE_2_3",
        },
        {
            "id": "A2_REF_CONSERVE",
            "type": "reflection",
            "text": (
                "You pulled back today — and that's worth being honest about.\n\n"
                "Sometimes that's sustainable self-management. Sometimes\n"
                "it's a signal that something needs to change.\n\n"
                "The question isn't whether you pulled back —\n"
                "it's whether you know why."
            ),
            "target": "BRIDGE_2_3",
        },

        # ── Bridge 2 → 3 ──────────────────────────────────────────────────
        {
            "id": "BRIDGE_2_3",
            "type": "bridge",
            "text": "One more lens. This one zooms out — from you to the people around you.",
            "target": "A3_Q7",
        },

        # ══════════════════════════════════════════════════════════════════
        #  AXIS 3 — RADIUS  (Self-centric ↔ Altrocentric)
        # ══════════════════════════════════════════════════════════════════

        {
            "id": "A3_Q7",
            "type": "question",
            "text": "When you replay today right now — who's actually in it?",
            "options": [
                {
                    "label": "Mostly me — my tasks, my pressure, what I got done or didn't",
                    "signal": "axis3:self",
                    "next": "A3_Q8",
                },
                {
                    "label": "Me and a few specific people I worked with directly",
                    "signal": "axis3:dyadic",
                    "next": "A3_Q8",
                },
                {
                    "label": "The team — I keep thinking about how we're doing collectively, not just my part",
                    "signal": "axis3:team",
                    "next": "A3_Q8",
                },
                {
                    "label": "Someone carrying something heavy right now — they keep coming to mind",
                    "signal": "axis3:altrocentric",
                    "next": "A3_Q8",
                },
            ],
        },

        {
            "id": "A3_Q8",
            "type": "question",
            "text": (
                "Is there someone from today whose experience you\n"
                "don't fully understand — but you're a bit curious about?"
            ),
            "options": [
                {
                    "label": "Yes — someone reacted unexpectedly and I want to understand why",
                    "signal": "axis3:curious_other",
                    "next": "A3_Q9",
                },
                {
                    "label": "Not really — I have a clear enough picture of how things landed",
                    "signal": "axis3:self_confident",
                    "next": "A3_Q9",
                },
                {
                    "label": "I didn't have the bandwidth to think much about others — heads down",
                    "signal": "axis3:self",
                    "next": "A3_Q9",
                },
                {
                    "label": "Yes — I'm wondering how something rippled beyond what I could see",
                    "signal": "axis3:systemic",
                    "next": "A3_Q9",
                },
            ],
        },

        {
            "id": "A3_Q9",
            "type": "question",
            "text": (
                "If today had a point beyond just getting through it —\n"
                "what would that be?"
            ),
            "options": [
                {
                    "label": "Honestly, getting through it well is the point some days",
                    "signal": "axis3:self",
                    "next": "A3_DECIDE_REF",
                },
                {
                    "label": "Contributing something useful — even something small",
                    "signal": "axis3:contribution_meaning",
                    "next": "A3_DECIDE_REF",
                },
                {
                    "label": "Being the kind of person I want to be — in the small moments too",
                    "signal": "axis3:identity_transcendent",
                    "next": "A3_DECIDE_REF",
                },
                {
                    "label": "Something larger than my work — for the team or the people we actually serve",
                    "signal": "axis3:altrocentric_high",
                    "next": "A3_DECIDE_REF",
                },
            ],
        },

        # ── Axis-3 reflection router ──────────────────────────────────────
        {
            "id": "A3_DECIDE_REF",
            "type": "decision",
            "conditions": [
                {"if": "self",         "target": "A3_REF_SELF"},
                {"if": "dyadic",       "target": "A3_REF_DYADIC"},
                {"if": "team",         "target": "A3_REF_TEAM"},
                {"if": "altrocentric", "target": "A3_REF_ALTO"},
            ],
        },

        # ── Axis-3 reflections ────────────────────────────────────────────
        {
            "id": "A3_REF_SELF",
            "type": "reflection",
            "text": (
                "Today's frame was mostly about you — your tasks, your load,\n"
                "your outcomes. That's not a character flaw.\n\n"
                "When pressure is high and bandwidth is low, the radius\n"
                "narrows automatically. It's almost physiological.\n\n"
                "But it's worth knowing: most of what feels like isolated\n"
                "pressure is actually shared. You're probably not the only\n"
                "one carrying something today."
            ),
            "target": "SUMMARY",
        },
        {
            "id": "A3_REF_DYADIC",
            "type": "reflection",
            "text": (
                "You kept at least one other person in frame today —\n"
                "and you're still curious about how they experienced things.\n\n"
                "That curiosity is rarer than it sounds. Most people close\n"
                "the day with their own account of events and leave it there.\n\n"
                "You haven't."
            ),
            "target": "SUMMARY",
        },
        {
            "id": "A3_REF_TEAM",
            "type": "reflection",
            "text": (
                "Your frame today was wider than yourself. You were tracking\n"
                "how the whole thing was landing — not just your part of it.\n\n"
                "That kind of awareness tends to be contagious in teams,\n"
                "often without people realizing where it's coming from."
            ),
            "target": "SUMMARY",
        },
        {
            "id": "A3_REF_ALTO",
            "type": "reflection",
            "text": (
                "You ended the day thinking about someone else —\n"
                "or something larger than the immediate situation.\n\n"
                "That's not performance. It's actually the most reliable\n"
                "source of meaning there is: finding yourself embedded in\n"
                "something that matters beyond your own account of the day."
            ),
            "target": "SUMMARY",
        },

        # ══════════════════════════════════════════════════════════════════
        #  SUMMARY + END
        # ══════════════════════════════════════════════════════════════════

        {
            "id": "SUMMARY",
            "type": "summary",
            "text": (
                "Today's picture:\n\n"
                "On agency       —  you leaned {axis1.summary}.\n"
                "                   {axis1.detail}\n\n"
                "On contribution —  you leaned {axis2.summary}.\n"
                "                   {axis2.detail}\n\n"
                "On radius       —  {axis3.summary}.\n"
                "                   {axis3.detail}\n\n"
                "─────────────────────────────────────────────\n"
                "One thing to carry into tomorrow:\n"
                "{cross_axis_insight}"
            ),
            "interpolations": {
                "axis1.summary": {
                    "internal":   "toward ownership",
                    "external":   "toward reading the context as the constraint",
                    "processing": "toward sitting with uncertainty",
                },
                "axis1.detail": {
                    "internal":   "You kept seeing yourself as having a hand in what happened.",
                    "external":   "Sometimes accurate. Sometimes the most useful question is where the small choices were hiding.",
                    "processing": "That's honest. Not everything resolves in a single day.",
                },
                "axis2.summary": {
                    "contribution": "toward giving",
                    "entitlement":  "toward tracking what you were owed",
                    "neutral":      "toward reliable, steady delivery",
                    "conservation": "toward protecting your reserves",
                },
                "axis2.detail": {
                    "contribution": "You were giving without much of a ledger.",
                    "entitlement":  "The work was real — and so was the tracking.",
                    "neutral":      "You showed up and did the job. That's not nothing.",
                    "conservation": "Worth knowing if the pullback was intentional or a signal.",
                },
                "axis3.summary": {
                    "self":        "today's frame was mostly yours alone",
                    "dyadic":      "you held at least one other person in the story",
                    "team":        "you were thinking in terms of us, not just me",
                    "altrocentric":"someone beyond your immediate circle stayed in mind",
                },
                "axis3.detail": {
                    "self":        "Tomorrow, one moment of noticing someone else's day might be enough.",
                    "dyadic":      "That curiosity about someone else's experience — follow it if you get the chance.",
                    "team":        "That wider awareness matters more than people realize.",
                    "altrocentric":"The thing beyond yourself that you kept thinking about — that might be where the real work is.",
                },
                "cross_axis_insight": {
                    "internal+contribution+team":       "You owned your day and gave to it. See if the team noticed something you didn't.",
                    "internal+contribution+self":       "Agency and effort were both present. Tomorrow, let someone else into the frame.",
                    "internal+contribution+altrocentric":"You moved well, gave freely, and thought beyond yourself. That's the full picture.",
                    "internal+contribution+dyadic":     "Solid agency, real giving. The curiosity about that other person — follow it.",
                    "internal+entitlement+self":        "You moved well but kept score. The next version might be moving well and letting the score go.",
                    "internal+entitlement+team":        "Sharp agency, wide radius — the entitlement thread is the one worth watching.",
                    "internal+neutral+self":            "You were in control and did the work. A small widening of frame tomorrow could compound that.",
                    "external+entitlement+self":        "Three lenses, one pattern: what the world owes you. There's something underneath that worth sitting with.",
                    "external+contribution+altrocentric":"You gave even when the situation was hard. That's a quiet kind of leadership.",
                    "external+contribution+team":       "The context constrained you — but you kept giving and thinking in terms of us.",
                    "external+entitlement+team":        "The situation felt unfair and you were tracking that — but you kept the team in view. Both are real.",
                    "processing+contribution+altrocentric":"Still working it out inside — and yet you were thinking about others. That matters.",
                    "processing+neutral+self":          "Uncertain about the day, steady in delivery, focused inward. A full day in one phrase.",
                    "default":                          "Notice the gap between how you showed up and how you wanted to. That gap is where tomorrow lives.",
                },
            },
            "target": "END",
        },

        {
            "id": "END",
            "type": "end",
            "text": "That's it. See you tomorrow.",
        },
    ],
}