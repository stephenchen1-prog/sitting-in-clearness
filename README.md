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
- **Privacy:** the meeting is kept on the visitor's device. To form questions, words are sent through Vercel's AI Gateway to a model provider such as Google; this code stores and logs nothing, and the page says so plainly. "Lay this down" erases everything on the device. Set `CLEARNESS_BACKEND=ollama` to run fully on your own machine instead.
- **Always works:** if no AI is reachable, each lens draws on hand-written open questions, and mirroring gives back the person's own sentences.

**Live:** https://sitting-in-clearness.vercel.app

## How it's built

- `web/index.html`: the whole page. Plain HTML, CSS and JavaScript, with no build step and no trackers.
- `server/clearness.py`: the committee. Its "swarm" design is adapted from [OpenAI Swarm](https://github.com/openai/swarm) (MIT): each companion is an agent made of a name plus instructions. Companions take turns; a clerk's check sets aside any question that carries advice.
- `server/clearness_web.py`: the API. It accepts only committee data and builds every prompt itself, with rate limits and size limits.
- `server/model.py`: Vercel AI Gateway by default (Gemma 4, then Gemini Flash-Lite, then GPT-4o-mini); or OpenRouter (`CLEARNESS_BACKEND=openrouter`), or a local Ollama (`CLEARNESS_BACKEND=ollama`).
- `app.py`: the Vercel entry point. The whole site is one Flask app.

## Deploy (Vercel)

`vercel deploy --prod`. On Vercel the AI Gateway authenticates with the project's own identity, so no API key is needed; the account needs a card on file to unlock Gateway's free credits. Without it, the hand-written fallback questions are used.

## Run it yourself

```bash
pip install flask waitress
CLEARNESS_BACKEND=ollama python server/clearness_web.py     # http://127.0.0.1:8450 (after: ollama pull llama3.2)
```

## Sources

The practice follows Parker Palmer's guidance on clearness committees and Britain Yearly Meeting's *Quaker Faith & Practice* (12.22–12.25). Every quotation shown was checked against its source; corrections are welcome at ai@whiteknightlaw.org.

## License

MIT. See `LICENSE`.
