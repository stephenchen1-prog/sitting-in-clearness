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
- **Privacy:** the meeting is kept on the visitor's device. To form questions, words are sent through OpenRouter to free open-source models; this code stores and logs nothing, but free-model providers may retain what they receive, and the page says so plainly. "Lay this down" erases everything on the device. Set `CLEARNESS_BACKEND=ollama` to run fully on your own machine instead.

## How it's built

- `web/index.html`: the whole page. Plain HTML, CSS and JavaScript, with no build step and no trackers.
- `server/clearness.py`: the committee. Its "swarm" design is adapted from [OpenAI Swarm](https://github.com/openai/swarm) (MIT): each companion is an agent made of a name plus instructions. Companions take turns; a clerk's check sets aside any question that carries advice.
- `server/clearness_web.py`: the API. It accepts only committee data and builds every prompt itself, with rate limits and size limits.
- `server/model.py`: OpenRouter free models by default, tried in order; or a local Ollama.
- `api/committee.py`: the Vercel serverless entry point.

## Deploy (Vercel)

The `web/` folder is the static site, and `api/committee.py` is the function. Set one environment variable in the Vercel project: `OPENROUTER_API_KEY`. Optionally set `CLEARNESS_MODELS` to a comma-separated list of OpenRouter model ids.

## Run it yourself

```bash
pip install flask waitress
OPENROUTER_API_KEY=... python server/clearness_web.py      # http://127.0.0.1:8450
# or fully local: CLEARNESS_BACKEND=ollama (after: ollama pull llama3.2)
```

## Sources

The practice follows Parker Palmer's guidance on clearness committees and Britain Yearly Meeting's *Quaker Faith & Practice* (12.22–12.25). Every quotation shown was checked against its source; corrections are welcome at ai@whiteknightlaw.org.

## License

MIT. See `LICENSE`.
