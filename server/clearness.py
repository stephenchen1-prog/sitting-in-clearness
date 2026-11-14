"""Sitting in Clearness: a swarm of question-only listening lenses, adapted from the
Quaker clearness committee. Used by the website (clearness_web.py) and by JARVIS
(voice and WhatsApp).

Swarm design adapted from OpenAI Swarm (MIT, github.com/openai/swarm): an Agent is a
name plus instructions. Companions take turns, one open question at a time, each
reading the updated record (Parker Palmer: questions "relaxed, gentle, humane", never
rapid-fire). No Swarm handoffs: unreliable on small local models and not needed.

Two modes:
  personal    a concern of one person's life
  governance  a matter being seasoned for a meeting for worship with attention to business

The AI never claims to be a Friend or to sense the Spirit. Each lens is only inspired
by a historical Friend, whose verified words are shown to the person.
"""
import json
import os
import re
from dataclasses import dataclass

from local_model import ask

WEB_URL = os.environ.get("CLEARNESS_URL", "https://lenovo.taile99f29.ts.net")


@dataclass(frozen=True)
class Agent:
    """Swarm-style agent: a listening lens, inspired by a historical Friend."""
    id: str
    lens: str
    listen: str      # what this lens listens for (goes to the model)
    friend: str      # shown to the person; never impersonated
    quote: str       # verified words, shown in the page


MEMBERS = [
    Agent("truth", "Listening for truth", "what is actually true, beneath the story told about it",
          "Lucretia Mott", "Truth for authority, not authority for truth."),
    Agent("fear", "Listening for fear and pressure", "where fear, pressure or tiredness may be speaking louder than a deeper sense of what is right",
          "Douglas Steere", "listen another's soul into a condition of disclosure and discovery"),
    Agent("draws", "Listening for what draws you", "what genuinely draws, what gives life, and what drains it",
          "Thomas Kelly", "Deep within us all there is an amazing inner sanctuary of the soul, a holy place, a Divine Center."),
    Agent("others", "Listening for others affected", "the other people touched by this, and the relationships among them",
          "George Fox", "walk cheerfully over the world, answering that of God in every one"),
    Agent("timing", "Listening for timing", "urgency, whether this truly must be decided now, and what waiting might show",
          "Isaac Penington", "sink down to the seed which God sows in the heart, and let that grow in thee"),
    Agent("carry", "Listening for what you carry", "what is being carried, the limits, and what a simpler way might look like",
          "John Woolman", "to turn all the treasures we possess into the channel of universal love becomes the business of our lives"),
]
BY_ID = {m.id: m for m in MEMBERS}
DEFAULT_IDS = ["truth", "fear", "draws", "others", "timing"]

SYSTEM = ("You help with a private reflective practice adapted from the Quaker clearness committee. "
          "You are an AI, not a Quaker and not a member of any meeting, and you never speak as any historical person. "
          "You only ask honest, open questions. You never advise, reassure, interpret, agree, take sides, or share opinions or stories. "
          "Never claim to sense the Spirit, the Light or a leading.")
GOV_NOTE = ("The person is a member or clerk seasoning a matter that will come before a Quaker meeting for worship with attention to business. "
            "They are NOT any of the people described in the matter; never assume they are the one who disagrees, objects or is at fault. "
            "Ask about their own experience and what they sense in the meeting. Never argue for an outcome or for one group of Friends over another.")

# ----- the clerk's check -----
_ADVICE_START = re.compile(
    r"^(have you (considered|thought about|tried|looked into)|wouldn'?t|shouldn'?t|why (don'?t|not)|could you (try|just)|"
    r"what if you|isn'?t it|don'?t you think|you (should|could|might|need)|it sounds like|i (hear|sense|notice|wonder)|"
    r"maybe you|perhaps you|is it possible|could it be|would it help|consider)", re.I)
_ADVICE_ANY = re.compile(r"\b(you should|we should|the meeting should|i would|i'd suggest|my advice|if i were you|i recommend|you ought)\b", re.I)
_TWO_PART = re.compile(r",?\s+(and|or)\s+(what|how|where|when|who|why|do|does|is|are)\b", re.I)  # two questions in one
_STOP = {"you", "your", "the", "a", "to", "of", "and", "is", "it", "in", "what", "how", "do", "that", "this", "are", "we", "for"}


def _words(s: str) -> set:
    return set(re.findall(r"[a-z0-9']+", s.lower())) - _STOP


def is_open(q: str) -> bool:
    q = q.strip().strip('"“”').strip()
    return (q.endswith("?") and 8 <= len(q) <= 180 and not re.search(r"[.!]\s+\S", q[:-1])
            and q.count("?") == 1 and not _TWO_PART.search(q)
            and not _ADVICE_START.match(q) and not _ADVICE_ANY.search(q))


def is_repeat(q: str, earlier: list) -> bool:
    w = _words(q)
    for e in earlier:
        e_w = _words(e)
        if q.strip().lower() == e.strip().lower():
            return True
        if w and e_w and len(w & e_w) / min(len(w), len(e_w)) > 0.6:
            return True
    return False


def _json(text: str):
    for cand in (text, *re.findall(r"```(?:json)?\s*(.*?)```", text, re.S)):
        try:
            return json.loads(cand)
        except (ValueError, TypeError):
            continue
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except ValueError:
            return None
    return None


def parse_question(text: str):
    """Accept {"question": ...}, {"questions": [...]}, or a bare string. Returns str ('' = silence) or None."""
    data = _json(text)
    if isinstance(data, dict):
        if "question" in data:
            return str(data.get("question") or "").strip().strip('"“”')
        qs = data.get("questions")
        if isinstance(qs, list):
            return str(qs[0]).strip().strip('"“”') if qs else ""
    if isinstance(data, str):
        return data.strip()
    return None


def run(prompt: str, *, governance=False, json_mode=False, temperature=0.7, max_tokens=120) -> str:
    return ask(SYSTEM + ("\n" + GOV_NOTE if governance else ""), prompt,
               temperature=temperature, max_tokens=max_tokens, json_mode=json_mode)


def _clean(s) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


class Meeting:
    LIMITS = {"concern": 2000, "need": 600, "answer": 2000, "question": 300, "rounds": 6, "per_round": 12}

    def __init__(self, concern: str, member_ids=None, need: str = "", mode: str = "personal"):
        self.concern = concern.strip()
        self.need = need.strip()
        self.mode = "governance" if mode == "governance" else "personal"
        self.members = [BY_ID[i] for i in (member_ids or DEFAULT_IDS) if i in BY_ID]
        self.rounds = []  # each: list of {"m": id, "q": str, "a": str, "passed": bool}

    @property
    def gov(self) -> bool:
        return self.mode == "governance"

    @classmethod
    def from_dict(cls, d: dict, member_ids=None) -> "Meeting":
        """Rebuild a meeting from the browser's state, clipped to safe sizes. Raises ValueError."""
        L = cls.LIMITS
        if not isinstance(d, dict):
            raise ValueError("meeting must be an object")
        concern = str(d.get("concern") or "").strip()[:L["concern"]]
        if not concern:
            raise ValueError("concern is empty")
        m = cls(concern, member_ids, str(d.get("need") or "")[:L["need"]], str(d.get("mode") or "personal"))
        rounds = d.get("rounds") or []
        if not isinstance(rounds, list):
            raise ValueError("rounds must be a list")
        for r in rounds[-L["rounds"]:]:
            if not isinstance(r, list):
                continue
            m.rounds.append([{"m": q["m"], "q": str(q.get("q") or "")[:L["question"]],
                              "a": str(q.get("a") or "")[:L["answer"]], "passed": bool(q.get("passed"))}
                             for q in r[:L["per_round"]]
                             if isinstance(q, dict) and isinstance(q.get("m"), str) and q["m"] in BY_ID])
        return m

    def all_questions(self) -> list:
        return [q for r in self.rounds for q in r]

    def own_words(self) -> str:
        parts = [self.concern, self.need] + [q["a"] for q in self.all_questions() if not q["passed"]]
        return "\n".join(p for p in parts if p.strip())

    def _context(self) -> str:
        """Short enough for a small local model: the matter, the need, the last three exchanges."""
        t = ("Matter before the meeting: " if self.gov else "Concern: ") + self.concern[:800]
        if self.need:
            t += "\nWhat they most need to listen for: " + self.need[:300]
        recent = [q for q in self.all_questions() if q["q"]][-3:]
        if recent:
            t += "\nMost recent exchanges:"
            for q in recent:
                ans = "(they passed)" if q["passed"] else (q["a"].strip()[:400] or "(answered silently)")
                t += f"\n- Q: {q['q']}\n  A: {ans}"
        return t

    # ----- the swarm's moves -----
    def question_for(self, member: Agent):
        """One open question from this lens, or None if no honest question rises (silence is faithful)."""
        earlier = [q["q"] for q in self.all_questions() if q["q"]]
        follow = "Follow their last answer rather than opening a new topic. Fewer words." if earlier else "Begin gently."
        about = ("about their own experience of this matter, the meeting's life together, and what they sense in the meeting"
                 if self.gov else "about their own feelings, values or experience")
        prompt = f"""{self._context()}
Questions already asked (do not repeat or rephrase): {"; ".join(earlier[-12:]) or "none yet"}
Your listening: {member.listen}.
Write ONE open question, under 18 words, that only this person can answer, {about}. {follow}
Ask a single thing; never join two questions with "and".
Begin with What, How, Where, When or Who. Never use "should", "have you considered", or "what if you".
If no honest question rises, reply {{"question": ""}}.
Reply only as JSON: {{"question": "...?"}}"""
        for temp in (0.7, 0.9):
            got = parse_question(run(prompt, governance=self.gov, json_mode=True, temperature=temp, max_tokens=80))
            if got is None:
                continue
            if got == "":
                if earlier:
                    return None
                continue
            if is_open(got) and not is_repeat(got, earlier):
                return got.strip().strip('"“”')
        return None

    def queries(self, limit: int = 3) -> list:
        """Queries that may be present in the room but not yet addressed. Open questions only."""
        earlier = [q["q"] for q in self.all_questions() if q["q"]]
        where = "in the meeting as it considers this matter" if self.gov else "in this person's situation"
        prompt = f"""{self._context()}
Name up to {limit} queries that may be present {where} but have not yet been spoken: things unsaid that may need to be held.
Write each as a short open question, under 16 words, in the plain style of Quaker queries, beginning "How", "Where", "What" or "Who".
Do not answer them, take sides, name anyone, or advise.
Reply only as JSON: {{"queries": ["...?", "...?"]}}"""
        data = _json(run(prompt, governance=self.gov, json_mode=True, temperature=0.6, max_tokens=180))
        items = data.get("queries", []) if isinstance(data, dict) else []
        out = []
        for q in items if isinstance(items, list) else []:
            q = _clean(q).strip('"“”')
            if is_open(q) and not is_repeat(q, earlier + out):
                out.append(q)
        return out[:limit]

    def reflect(self, limit: int = 4) -> list:
        """Mirroring: the person's own words given back. Only phrases found word-for-word are kept."""
        words = self.own_words()
        data = _json(run(f"""The person below invited mirroring. Choose up to {limit} short phrases (3 to 20 words) that they themselves wrote, copied exactly, which seemed to matter most to them. Add nothing else.

What they wrote:
{words[:3000]}

Reply only as JSON: {{"quotes": ["...", "..."]}}""", json_mode=True, temperature=0.3, max_tokens=200))
        quotes = data.get("quotes", []) if isinstance(data, dict) else []
        hay = _clean(words).lower()
        out = []
        for q in quotes if isinstance(quotes, list) else []:
            q = _clean(q).strip('"“”.')
            if 3 <= len(q.split()) <= 25 and q.lower() in hay and q not in out:
                out.append(q)
        if not out and self.concern:
            out = [re.split(r"(?<=[.!?])\s", self.concern)[0][:200]]
        return out[:limit]

    def affirm(self):
        """One grounded affirmation, citing the person's own words. None if it can't be done honestly."""
        words = self.own_words()
        text = run(f"""Speaking directly to the person, name one quality they showed in this reflection, such as honesty, care or courage, citing a few of their own words in quotation marks. One sentence that begins "You showed". No praise of any decision, no encouragement toward any choice, no advice.

What they wrote:
{words[:3000]}

Write only the sentence.""", temperature=0.5, max_tokens=80).strip()
        hay = _clean(words).lower()
        quoted = re.findall(r"[\"“]([^\"”]{3,200})[\"”]", text)
        if not quoted or any(_clean(q).lower().strip(" .,") not in hay for q in quoted):
            return None
        if "?" in text or _ADVICE_ANY.search(text) or re.search(r"\bshould\b", text, re.I) or len(text) > 300:
            return None
        return re.sub(r"^the person showed", "You showed", text, flags=re.I)


# ---------------- Chat adapter (JARVIS voice + WhatsApp): one question at a time ----------------
_HELP = ("Sitting in Clearness, adapted from the Quaker clearness committee. It is not a real committee: "
         "for anything weighty, ask your meeting. Say 'clearness' and your concern to begin, or 'clearness meeting' and a "
         "business matter. Answer each question or say 'pass'. Say 'close' to end, or 'end clearness' to stop.")
_CLERK_OPEN = ("We will ask only honest, open questions. You may pass on any of them. "
               "Nothing here is shared, and this concern will not be raised with you again. ")
_state = {"meeting": None, "phase": None, "turn": 0, "current": None}


def active() -> bool:
    return _state["meeting"] is not None


def _next_question() -> str:
    m = _state["meeting"]
    n = len(m.members)
    while _state["turn"] < n * 2:
        member = m.members[_state["turn"] % n]
        if _state["turn"] % n == 0:
            m.rounds.append([])
        _state["turn"] += 1
        q = m.question_for(member)
        if q:
            entry = {"m": member.id, "q": q, "a": "", "passed": False}
            m.rounds[-1].append(entry)
            _state.update(current=entry, phase="asking")
            return f"{member.lens}, in the spirit of {member.friend}: {q}"
    _state["phase"] = "closing"
    return "The questions have run their course. Say 'close' to end with your own words given back."


def _end(msg: str) -> str:
    _state.update(meeting=None, phase=None, turn=0, current=None)  # nothing is kept
    return msg


def handle(text: str) -> str:
    raw = text.strip()
    key = raw.lower().strip(" .!?")
    if key in ("clearness help", "clearness"):
        return _HELP
    if key in ("clearness link", "clearness website", "clearness app"):
        return f"Sitting in Clearness: {WEB_URL}"
    if key in ("end clearness", "stop clearness", "cancel clearness"):
        return _end("Closed. Nothing was kept.")
    if not active():
        gov = bool(re.match(r"^clearness meeting\b", raw, re.I))
        concern = re.sub(r"^clearness( meeting| committee)?[:,]?\s*", "", raw, flags=re.I)
        _state.update(meeting=Meeting(concern, mode="governance" if gov else "personal"), phase="silence", turn=0, current=None)
        return _CLERK_OPEN + "Take a minute of silence. Say 'ready' when you are."
    phase, m = _state["phase"], _state["meeting"]
    if key == "close" or phase == "closing":
        if key != "close":
            return "Say 'close' to end, or 'end clearness' to stop now."
        out = "Your own words, given back:\n" + "\n".join(f'"{q}"' for q in m.reflect())
        qs = m.queries()
        if qs:
            out += "\n\nPerhaps in the room, not yet addressed:\n" + "\n".join(f"- {q}" for q in qs)
        aff = m.affirm()
        if aff:
            out += "\n\n" + aff
        return _end(out + "\n\nA good clearness process does not end here. For anything weighty, ask your meeting.")
    if phase == "silence":
        return _next_question()
    q = _state["current"]
    if key == "pass":
        q["passed"] = True
    else:
        q["a"] = raw
    return _next_question()
