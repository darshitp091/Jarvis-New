# Jarvis — local-first personal AI assistant

Local senses (wake word → Whisper STT → brain → Edge TTS), cloud thinking via an
OpenAI-compatible provider, and a tool registry that lets the assistant act on
your machine (apps, media, Spotify via UI, browser/scrape, files, screen/OCR,
camera vision, approval-gated ethical-security and code fixes).

Designed to idle comfortably under 4 GB RAM. The "brain" runs in the cloud; the
senses and fast models run locally.

## Quick start

```bat
cd C:\Users\patel\jarvis
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

:: one-time: Tesseract OCR engine (for screen text reading)
winget install UB-Mannheim.TesseractOCR

copy .env.example .env
:: edit .env and paste your JARVIS_LLM_API_KEY (and model id if you know it)

python verify.py
```

`verify.py` prints a PASS/FAIL table for:
system info, LLM provider (`/v1/models` + one chat completion), Edge TTS,
faster-whisper STT, screen capture + OCR, webcam frame.

Fix any FAILs before moving on. Artifacts land in `data/`.

## Layout

```
jarvis/
├── core/
│   ├── config.py        # env/.env → settings (single source of truth)
│   ├── brain.py         # OpenAI-compatible wrapper (chat/stream/tool_turn)
│   └── __init__.py
├── abilities/           # each file self-registers tools
│   ├── apps.py          # open_app, close_app, list_running_apps
│   ├── media.py         # play/pause/toggle/next/previous (WinRT, no Spotify key)
│   ├── files.py         # read_file, write_file, list_dir
│   └── sysinfo.py       # system_info
├── tools_registry.py    # tool schemas + dispatch
├── agent_loop.py        # think -> tool-call -> observe -> answer
├── main.py              # CLI REPL
├── verify.py            # Phase 0 smoke tests
├── test_tools.py        # registry/dispatch smoke test
├── requirements.txt
├── .env.example
└── README.md
```

## Status

- **Phase 0 (verify):** 9/9 PASS — system, LLM `/models` + chat, Edge TTS,
  Whisper tiny-int8, screen+OCR, webcam.
- **Phase 1 (CLI brain + tools):** DONE — `python main.py "..."` runs the full
  think→act→observe loop. Media control via WinRT (controls Spotify/browser/VLC
  with NO Spotify API key).
- **Phase 2 (memory + vision):** DONE —
  - **Obsidian-backed long-term memory** (`core/memory.py`): each fact is a
    markdown note in `vault/Memory/` (YAML frontmatter + tags); every action is
    appended to a daily note in `vault/Journal/`. A SQLite index
    (`data/memory_index.db`) is derived from the vault for fast recall.
  - **Vision** (`core/vision.py`): `look_at_screen` / `look_at_me`.
- **Phase 3 (full abilities):** DONE — voice loop, deep OS control, browser,
  coding, proactive watcher, runtime skills, ethical-security (gated),
  self-correction.
- **Phase 4 (command-less / "alive"):** DONE —
  - **Wake-word always-listening** (`assistant.py`, `senses/wakeword.py`).
  - **Emotion/mood loop** (`senses/mood.py`, `assess_mood`).
  - **Ambient proactive dialogue** (`proactive.py --speak --mood`).
- **Phase 5 (conversation + persona):** DONE —
  - **Multi-turn conversation memory** (`core/conversation.py`): REPL and voice
    modes keep the last ~12 turns and can persist a session to `data/`. Add
    `clear` in the REPL to reset, `quit` to save.
  - **Continuous voice conversation** (`assistant.py`): after "hey jarvis" you
    keep talking naturally (no re-wake); say "stop"/"bye" to end; idle timeout
    returns to wake-word listening.
  - **JARVIS persona** (`agent_loop.py`): calm, capable, quietly witty, Hinglish-
    aware; addresses you by name.
  - **Streaming TTS** (`senses/voice.py::StreamingSpeaker`): replies are spoken
    sentence-by-sentence for a responsive feel.
- **Phase 6 (utilities):** DONE —
  - **Reminders & timers** (`abilities/reminders.py`): `set_reminder` /
    `list_reminders`; due reminders are spoken by the proactive watcher.
  - **RAG over local files** (`abilities/rag.py`): `index_folder` / `search_files`.
  - **Everyday tools** (`abilities/utilities.py`): `current_time`, `weather`
    (free, no key), `calculate`, `convert_units`, `translate`.
  - **Notes & todos** (`abilities/notes.py`): `add_note` (→ Obsidian),
    `add_todo`, `list_todos`, `clipboard_save`, `clipboard_history`.
- **Phase 7 (automation & productivity):** DONE —
  - **Playwright browser automation** (`abilities/browser_auto.py`): `browse`
    (real JS-rendered page text), `screenshot_url`. Chromium installed.
  - **Live system monitor** (`abilities/sysinfo.py`): `system_monitor`.
  - **Productivity** (`abilities/productivity.py`): `ocr_screen`, `find_files`,
    `organize_folder` (dry-run + approval), `draft_email` (opens mailto, no send).
- **59 tools total.** One-shot mode never blocks on approval (deny by default;
  `--yes` to auto-approve). Console forced to UTF-8 so Hindi output never crashes.




## Run it

```bat
:: ALWAYS-LISTENING (say "hey jarvis") + CONTINUOUS conversation -- command-less!
python assistant.py

:: CLI (type or one-shot) -- keeps conversation context in the REPL
python main.py                       :: interactive REPL (multi-turn, 'clear' to reset)
python main.py "open notepad"        :: one-shot (sensitive tools denied)
python main.py --yes "set volume 30" :: one-shot, auto-approve sensitive tools

:: Push-to-talk voice (press Enter to talk, it speaks back)
python voice_main.py

:: Background health watcher + ambient dialogue
python proactive.py --fast --speak          :: spoken system alerts
python proactive.py --fast --speak --mood   :: also periodic mood reads

:: Re-run the full stack check
python verify.py
```

## Tools (59)

apps (open/close/list) · media (play/pause/toggle/next/prev) · files (read/write/list/find) ·
system info + `system_monitor` · memory (remember/recall) · vision (look_at_screen/look_at_me) ·
mood (assess_mood) · volume/brightness/clipboard (+ `clipboard_save`, `clipboard_history`) ·
keyboard/mouse (type/press/click) · windows (list/focus) · power (lock/sleep/shutdown/restart) ·
wifi · web (open_url/search_web/fetch_page) · **Playwright** (`browse`, `screenshot_url`) ·
code (run_python/apply_code_fix) · security (audit/check_port) · create_skill ·
reminders (`set_reminder`, `list_reminders`) · RAG (`index_folder`, `search_files`) ·
utilities (`current_time`, `weather`, `calculate`, `convert_units`, `translate`) ·
notes (`add_note`, `add_todo`, `list_todos`) · productivity (`ocr_screen`, `find_files`,
`organize_folder`, `draft_email`).



```
vault/
  Memory/   20261123-183243-patel-s-dog-s-name-is-bruno.md   # one note per fact
  Journal/  2026-11-23.md                                     # daily action log
```

Open `C:\Users\patel\jarvis\vault` as a vault in Obsidian. The `.md` files are
the source of truth; the DB is just a search index. Install **Dataview** and
`LIST FROM #jarvis` to browse.


## Capability map (JARVIS gap analysis)

| Capability | Buildable? | Status |
|---|---|---|
| Long-term memory (Obsidian) | ✅ | **DONE** |
| Vision (screen + webcam understanding) | ✅ | **DONE** |
| App + media control (no Spotify key) | ✅ | **DONE** |
| Files / system info | ✅ | **DONE** |
| Self-correction / retry on failure | ✅ | **DONE** |
| Voice loop (STT + TTS) | ✅ | **DONE** |
| **Wake-word always-listening ("hey jarvis")** | ✅ | **DONE** |
| **Emotion / mood sensing** | ✅ | **DONE** (sampled, on-demand + periodic) |
| **Ambient proactive dialogue** | ✅ | **DONE** (speaks unprompted) |
| Deep OS control (volume/brightness/clipboard/keys/windows/power/wifi) | ✅ | **DONE** |

| Browser control + scraping | ✅ | **DONE** |
| Coding ability (write/run/debug) | ✅ | **DONE** |
| Proactive ambient alerts | ✅ | **DONE** |
| Runtime skill creation | ✅ | **DONE** |
| Ethical-security scan (approval-gated) | ✅ | **DONE** |
| Multi-step planning (tool loop) | ✅ | **DONE** (LLM-driven multi-tool turns) |
| **Multi-turn conversation memory** | ✅ | **DONE** (REPL + voice, persisted) |
| **Continuous conversation (no re-wake)** | ✅ | **DONE** |
| **JARVIS persona + streaming TTS** | ✅ | **DONE** |
| **Reminders / timers** | ✅ | **DONE** (spoken when due) |
| **RAG over local files** | ✅ | **DONE** |
| **Weather / time / math / units / translate** | ✅ | **DONE** |
| **Notes / todos / clipboard history** | ✅ | **DONE** |
| **Playwright browser automation** | ✅ | **DONE** |
| **OCR / file find / organize / email draft** | ✅ | **DONE** |
| Calendar / email *send* / smart-home IoT | 🔶 | not built (needs accounts/hardware) |
| Suits / holograms / flying | ❌ fiction | N/A |



**Vision note:** `deepseek-v4.1-flash-free` accepts images (verified). No
embeddings endpoint exists, so memory embeds locally (zero downloads, ~0 MB).
`jev-1.13-free` is a judge model on a special endpoint — not used for chat.


## Provider

- Base URL: `https://100milionseek.top/v1` (OpenAI-compatible)
- Auth: `Authorization: Bearer <JARVIS_LLM_API_KEY>`
- Confirmed models: `deepseek-v4.1-flash-free`, `jev-1.13-free`
  (there is no "claude sonnet 5.5" / "gpt astra 6" on this provider).

## Notes

- Tesseract must be installed separately; `pytesseract` is only the binding.
  If it isn't on PATH, set `TESSERACT_CMD` or add the install dir to PATH.
- Webcam/screen tests are skippable; a FAIL there doesn't block voice/LLM work.
- Secrets live in `.env` only. Never commit it.
