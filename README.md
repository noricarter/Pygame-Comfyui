# Pygame ↔ ComfyUI Runner — **Modular Edition**

A small, friendly Pygame front‑end for running **ComfyUI** API workflows, with a folder‑based picker, a token‑driven inputs form (supports **multiline + paste**), automatic seed management, and a universal artifact collector (images, text, audio, video).

> Current state: **folder-based workflows**, **token-aware inputs form**, **seed policy**, **images/text/audio preview**, **video saved to disk**, **tunnel/host ready**.


---

## ✨ Features

- **Workflows folder (F1 pick)** — Drop API‑format JSONs into `workflows/` and select them with a keyboard picker.
- **Token‑driven Inputs Form (F2)** — The app scans your graph for any `%%TOKEN%%` and builds a form automatically.
  - Multiline fields (use `%%NAME:ml%%` or common prompt names) with wrapping + **Ctrl+V paste**.
  - Typed values: `:int`, `:float` are coerced to numbers when the token occupies a field exactly.
- **Seed policy that makes sense** — If the graph has `%%SEED%%`, the app uses your value or auto‑generates one; otherwise it broadcasts a random seed to all `seed`/`noise_seed` inputs.
- **Artifact harvester** — Collects saved files (images/audio/video/text), **UI text outputs**, and deterministic fallbacks under `output/` for plugins that don’t register history files.
- **Non‑blocking game loop** — Workflow runs on a worker thread; UI stays smooth.
- **Tunnel/host ready** — Set `COMFY_BASE_URL` to an ngrok or reverse‑proxied URL; optional Basic Auth supported.
- **Portable across graphs** — No hardcoded node IDs. Tokens + Save nodes keep it resilient as you rearrange nodes.


---

## 🧱 Project Layout

```
pg_comfy_modular/
├─ main.py                  # tiny: app glue, modes & drawing
├─ requirements.txt
├─ workflows/               # put your API-format JSONs here (recursively scanned)
├─ core/
│  ├─ comfy_client.py       # HTTP client; collects artifacts (history + UI + output/ fallback)
│  ├─ workflow_io.py        # scan/load workflows
│  ├─ tokens.py             # find/apply %%TOKENS%% with optional types (ml/int/float)
│  ├─ seed.py               # random_u32, seed policy
│  └─ artifacts.py          # split artifacts by kind for UI
├─ ui/
│  ├─ renderer.py           # draw panels, wrap text, load/scale images
│  ├─ picker.py             # F1 Workflow Picker
│  ├─ form.py               # F2 Inputs Form (multiline + paste)
│  └─ hud.py                # status/seed/paths + overlay text
└─ app/
   ├─ state.py              # dataclasses for app state
   └─ runner.py             # background thread that calls Comfy
```


---

## 🚀 Installation

```bash
# 1) Get deps
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt

# 2) (Linux only) Clipboard backend for paste in the Inputs Form:
sudo apt install xclip    # or: sudo apt install xsel
# Wayland: sudo apt install wl-clipboard

# 3) Run
python main.py
```

**ComfyUI** must be running and reachable (default `http://127.0.0.1:8188`).  
Set a tunnel/hosted URL via environment:

```bash
export COMFY_BASE_URL="https://<your-ngrok-id>.ngrok.io"
# or behind a reverse proxy: https://imgbox.yourdomain.com
```

> If you add Basic Auth at the proxy, see `core/comfy_client.py` for passing `auth=("user","pass")`.


---

## 🎛 Preparing Workflows (what the app expects)

1) **Export in API format**  
   In ComfyUI, use **Workflow → Save (API Format)**. Save the JSON in `pg_comfy_modular/workflows/`.

2) **Use tokens where you want runtime inputs**  
   - Basic: `%%PROMPT%%`, `%%NEG_PROMPT%%`, `%%STYLE%%`  
   - Multiline: `%%PROMPT_1:ml%%` (or rely on prompt‑name heuristics)  
   - Typed: `%%STEPS:int%%`, `%%CFG:float%%` (exact‑match tokens are coerced to numbers)  
   - Seed (optional): `%%SEED:int%%`  
   You can add as many tokens as you like (e.g., `%%PROMPT_1%%`, `%%PROMPT_2:ml%%`, `%%MEMORY:ml%%`).

3) **Save your outputs**  
   Ensure your graph ends with Save nodes so the app can fetch results:
   - **Save Image** → previewed in the window
   - **Save Text** → shown as a short overlay excerpt
   - **Save Audio** → plays via `pygame.mixer` (WAV/OGG most reliable)
   - **Save Video** → saved to temp; path shown on screen

   For plugins that write directly to disk (e.g., `SaveText|pysssss`), point them **under** `output/` with a deterministic relative path:
   - `root_dir = "output"`, `file = "Pygame/file.txt"`  
   The client includes a fallback that will fetch these via `/view`.


---

## 🖥 Using the App

- **F1** — Open Workflow Picker (↑/↓ PgUp/PgDn Home/End, **Enter** to select, **R** to refresh, **F1/Esc** to close).  
- **F2** — Open Inputs Form (auto‑built from tokens in the selected workflow).  
  - **Enter**: edit / save field  
  - **Ctrl+V**: paste into field  
  - **Esc**: cancel edit / close form  
  - Multiline fields: **Enter** inserts newline, **Ctrl+Enter** saves  
- **F5** — Run workflow  
  - Replaces `%%TOKENS%%` everywhere in string inputs.  
  - Applies **seed policy** (below).  
  - Displays images, overlays text, plays first audio, saves videos (paths shown).

> HUD shows status, active workflow, discovered inputs, last seed, and saved video paths.


---

## 🎲 Seed Policy (how randomness works)

- If the graph **contains `%%SEED%%`** and you leave it blank in the form, the app generates a fresh 32‑bit seed and injects it **at the exact token fields**.
- If the graph **does not contain `%%SEED%%`**, the app **broadcasts** a random seed to **all** `seed` / `noise_seed` inputs it finds.
- You can supply your own seed in the form to make runs deterministic.


---

## 🔊 Outputs Behavior

- **Images**: First image is shown, auto‑scaled to fit.  
- **Text**: All text artifacts are concatenated, excerpted, and shown as an overlay. The client harvests:
  1) files registered in **history** (`{filename, subfolder, type}`),
  2) **UI text** entries from nodes like `ShowText`,
  3) **deterministic disk fallbacks** under `output/` for plugins that don’t register history files.
- **Audio**: First audio file is saved to temp and played (WAV/OGG recommended; MP3 may depend on your SDL build).  
- **Video**: Saved to temp; path printed in the HUD (Pygame has no native video player).


---

## 🐞 Troubleshooting

- **Clipboard paste fails on Linux** → install `xclip` / `xsel` / `wl-clipboard`.  
- **No outputs appear** → confirm your graph uses Save nodes or writes to `output/...`; check that ComfyUI is reachable at `COMFY_BASE_URL` (or `127.0.0.1:8188`).  
- **Audio won’t play** → prefer WAV/OGG; verify `pygame.mixer.get_init()`; headless/WSL may need an audio backend.  
- **Same seed every run** → ensure you’re on this modular version; it auto‑generates seeds as described above.  
- **Token not replaced** → open the Inputs Form (F2) and confirm the token name exists. Typed tokens replace as numbers only when the field equals the token exactly.

## 🧪 Quick Checklist

- [ ] ComfyUI is running (local or tunneled via `COMFY_BASE_URL`)  
- [ ] Workflow JSONs saved in **API format** and placed under `workflows/`  
- [ ] Tokens inserted where runtime inputs are needed (e.g., `%%PROMPT_1:ml%%`, `%%SEED:int%%`)  
- [ ] Save nodes at the end of each branch you care about  
- [ ] (Linux) Clipboard backend installed for paste in the form
---
