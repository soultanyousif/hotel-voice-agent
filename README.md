# موظف استقبال سعودي - Saudi Hotel Voice Agent

A voice-based hotel receptionist that speaks Saudi Arabic and looks and feels
like a phone call. Guests hold the mic, speak, and the agent transcribes,
checks room prices/availability and handles bookings against a live
database, then replies back out loud in a Saudi voice while a call-style
screen shows whether it's listening, thinking, or speaking.

Built as a demo/portfolio project, inspired by [Sarj AI](https://www.linkedin.com/company/sarj_ai/posts/)
and [Sawt](https://www.linkedin.com/company/usesawt/posts/).

## How it works
guest voice --> ASR (Groq, whisper-large-v3)
--> LLM + tools (Groq, qwen/qwen3.8-27b)
|-- get_room_types
|-- check_availability
|-- propose_booking
|-- confirm_booking
--> reply text
--> TTS (Groq, canopylabs/orpheus-arabic-saudi) --> spoken reply, played inline in the call screen


Every stage -- transcription, reasoning/tool-calling, and speech synthesis --
runs on Groq's hosted infrastructure. That wasn't the original design: TTS
first ran locally (Habibi-TTS, voice-cloned from a reference clip), but on
the hardware available for this project, local inference took upwards of
three minutes per reply -- unusable for anything meant to feel like a real
conversation. Moving both ASR and TTS to Groq's API removed the hardware
bottleneck entirely and brought reply generation down to a few seconds.

## Call-style interface

`app.py` renders a dark, phone-sized call screen instead of a generic form:
a round avatar with a pulsing ring while the agent talks and a breathing
animation while it thinks, the agent's name, and a one-word status label
("في انتظارك" / "يفكر..." / "يتكلم..."). No transcript or waveform is shown
on screen, since a real call doesn't show you a transcript either.

The reply audio is embedded directly into the page as a base64 data URI on
every turn, instead of being handed to Gradio's own audio player. This
matters for two reasons: a fresh `<audio autoplay>` element is created for
each reply, so playback always starts from the very beginning rather than
partway through, and it starts on its own without a second click, since the
mic click that started the turn already counts as the user gesture browsers
require for autoplay.

The avatar image (`Saudi_man_emoji.png`) needs to sit in the same folder as
`app.py` to load; if it's missing, the screen falls back to a plain circle.

## Accurate tool calling under real constraints

The agent never invents a price, availability, or booking number -- every
factual claim it makes is required to come from an actual tool call against
the database, not the model's own guess. This took real, iterative hardening,
not just a system prompt:

- `confirm_booking` will only execute if its arguments exactly match the
  agent's last successful `propose_booking` call. This closes off a real
  failure mode that showed up during testing, where the model would
  occasionally try to confirm a booking with fabricated guest details that
  were never actually proposed to (or seen by) the guest.
- The system prompt requires the final booking number to be read back
  exactly as the `confirm_booking` tool returns it -- digits only, no
  reformatting into a reference code, no extra words tacked on. This was
  added after testing surfaced the model inventing a plausible-looking
  alphanumeric confirmation code instead of the real numeric id.
- The call's closing line is pinned to a fixed example the model can only
  vary slightly, after an earlier version of the prompt let it improvise a
  sign-off and it occasionally produced a nonsense phrase instead of a real
  one.
- If the model produces a malformed or disallowed tool call, the code
  retries once forcing a plain-text reply instead of crashing the
  conversation -- and if that retry also fails, it falls back to a canned
  apology rather than letting an exception take down the whole session.

The result: on a smaller, faster model, booking data stayed correct and
consistent across repeated test runs, even when the model's own
conversational text occasionally stumbled.

## Conversation flow

The system prompt walks the call through a fixed order: greeting and name,
check-in/check-out dates, room type, price and availability for that type,
number of guests, a name confirmation, a booking proposal the guest must
explicitly approve, the actual confirmation with the real booking number,
and a closing line. If the guest volunteers several of these at once or out
of order, the agent skips straight to whatever's still missing instead of
re-asking for something it already has.

## Limitations

- **Built on weak local hardware.** Development happened on a machine without
  a capable GPU, which directly shaped the architecture: local TTS was
  abandoned in favor of Groq's hosted API not by preference but by necessity.
  The upside is a design that now runs identically well on any machine,
  since nothing compute-heavy happens locally at all.
- **No custom voice.** Switching to Groq's hosted TTS traded a
  voice cloned from a real reference clip for one of Orpheus's fixed preset
  Saudi voices. Faster and simpler, at the cost of a unique voice identity.
- **Turn-based, not full-duplex.** The interaction is record -> stop -> wait
  -> hear reply, not a continuously listening phone call. True hands-free
  calling would need streaming ASR and voice-activity detection, which is a
  larger build than this project covers.
- **Small, fast model, imperfect text.** The model occasionally produces
  repetitive or slightly malformed conversational text. Booking data
  integrity and the exact booking number are protected at the prompt and
  code level regardless (see above); general reply wording quality is not
  fully guaranteed.
- **Dependent on external, rate-limited, sometimes-preview APIs.** ASR, LLM,
  and TTS all run on Groq's free tier, and the TTS model is in Preview
  status per Groq's own docs. Behavior, availability, or pricing could
  change without this project's control.

## Project structure

hotel-voice-agent/
├── app.py Gradio call-style voice interface
├── agent.py system prompt, tool definitions, LLM call loop
├── speech.py ASR + TTS wrappers (both Groq-hosted)
├── hotel_db.py mock database module
├── hotel.db generated by hotel_db.py, not committed
├── system_prompt.txt
├── requirements.txt
├── .env.example copy to .env and add your GROQ_API_KEY
├── Saudi_man_emoji.png avatar shown on the call screen
├── notebook/
│ └── exploration.ipynb
├── test_conversation.py scripted happy-path booking test
├── test_unavailable.py scripted no-availability test
└── test_speech.py standalone TTS smoke test


## Setup

Requires Python 3.11+ and a free [Groq API key](https://console.groq.com/keys).

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux
# then edit .env and add your GROQ_API_KEY
```

Before TTS will work, accept `canopylabs/orpheus-arabic-saudi`'s model terms
at console.groq.com (one-time, per Groq account) -- requests fail with a
clear error until this is done.

```bash
python hotel_db.py            # seeds hotel.db with demo room types/bookings
python app.py                 # launches the voice interface
```

## Testing

```bash
python test_conversation.py   # full scripted booking flow
python test_unavailable.py    # confirms it correctly refuses when a room type is full
python test_speech.py         # standalone TTS check
```

## Notes

- This is a portfolio/demo project, not a production booking system -- the
  "hotel" and its inventory are entirely fictional.
- ASR, TTS, and the LLM all run through Groq's hosted API, so usage is
  subject to Groq's own pricing and rate limits (see console.groq.com).