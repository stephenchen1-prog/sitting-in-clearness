# Sitting in Clearness

A quiet way to sit with a concern, or with a matter for meeting, adapted from the Quaker
clearness committee: one honest, open question at a time, with silence in between.
Nothing here gives advice.

It is **not** a clearness committee and cannot replace one. For a weighty matter, ask your meeting.

A project of [White Knight Law Inc.](https://whiteknightlaw.org), a nonprofit that builds open-source tools to serve people.

## What it does

- **Two ways in:** a personal concern, or a matter being seasoned for meeting for worship with attention to business. The start page lists examples of the hardest questions meetings carry.
- **Six listening lenses,** each offered *in the spirit of* a historical Friend, with a verified quotation: Lucretia Mott (truth), Douglas Steere (fear and pressure), Thomas Kelly (what draws you), George Fox (others affected), Isaac Penington (timing), John Woolman (what you carry). The Friends are companions, not voices. The AI never speaks as them.
- **One question at a time,** with quiet in between. Pass on anything. Passed questions stay "still in the room".
- **A closing that gives your own words back** (only phrases you wrote, checked word for word), names queries that may be in the room but not yet said, and offers one plain affirmation.
- **A doorway to Friends:** a short introduction to Quakers, links to QuakerSpeak, FGC, Friends Journal and Quakers in Britain, and a meeting finder with a ready-to-send "may I visit?" email.
- **Private by design:** words stay on the visitor's device; the server forms questions with a small local model (Ollama) and stores and logs nothing. "Lay this down" erases everything.

## How it's built

- `web/index.html`: the whole page. Plain HTML, CSS and JavaScript, with no build step and no trackers.
- `server/clearness.py`: the committee. Its "swarm" design is adapted from [OpenAI Swarm](https://github.com/openai/swarm) (MIT): each companion is an agent made of a name plus instructions. Companions take turns; a clerk's check sets aside any question that carries advice.
- `server/clearness_web.py`: the API. It accepts only committee data and builds every prompt itself, with rate limits and size limits.
- `server/local_model.py`: local Ollama only. It never calls a cloud AI.

## Run it

```bash
pip install flask waitress
ollama pull llama3.2
python server/clearness_web.py      # http://127.0.0.1:8450
```

To share it publicly from that machine: `tailscale funnel --bg 8450`.
The `web/` folder can also be hosted as a static site (see `vercel.json`); `web/config.js` points it at the API.

## Sources

The practice follows Parker Palmer's guidance on clearness committees and Britain Yearly Meeting's *Quaker Faith & Practice* (12.22–12.25). Every quotation shown was checked against its source; corrections are welcome at ai@whiteknightlaw.org.

## License

MIT. See `LICENSE`.
