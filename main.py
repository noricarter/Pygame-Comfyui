# main.py
import os
import threading
import queue
import tempfile
from io import BytesIO
import json
import pyperclip

import pygame
from comfy_client import ComfyClient
from loader import load_workflow_graph
from params import replace_token, replace_numeric_token, set_seed_on_all_nodes, random_u32


pygame.init()
try:
    pygame.mixer.init()
except Exception as e:
    print("Audio disabled (mixer init failed):", e)

SCREEN_W, SCREEN_H = 1280, 720
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Pygame ↔ ComfyUI")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

# ---- Key bindings
RUN_KEY = pygame.K_F5          # run workflow
TYPE_TOGGLE_KEY = pygame.K_t   # enter/exit typing mode
PASTE_KEY = pygame.K_v         # with CTRL for paste

WORKFLOW_PATH = "my_comfy_workflow.json"  # optional fallback file

client = ComfyClient()

# ---- Runtime state
result_q: queue.Queue[list[dict]] = queue.Queue()
current_graph: dict | None = None
busy = False
status = "idle"

# Visual state
current_image_surface = None
current_text_overlay: list[str] = []
current_audio_tempfile: str | None = None
saved_video_paths: list[str] = []

# Prompt entry
typing_prompt = False
prompt_buffer = ""

last_seed: int | None = None

def reset_visual_state():
    global current_image_surface, current_text_overlay, current_audio_tempfile, saved_video_paths
    current_image_surface = None
    current_text_overlay = []
    if current_audio_tempfile and os.path.exists(current_audio_tempfile):
        try:
            os.remove(current_audio_tempfile)
        except Exception:
            pass
    current_audio_tempfile = None
    saved_video_paths = []

def _wrap_text(text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines, line = [], ""
    for w in words:
        trial = (line + " " + w).strip()
        if font.size(trial)[0] <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def process_artifacts(arts: list[dict]):
    global current_image_surface, current_text_overlay, current_audio_tempfile, saved_video_paths

    # Image (first)
    for a in arts:
        if a["kind"] == "image":
            try:
                img = pygame.image.load(BytesIO(a["bytes"]))
                rect = img.get_rect()
                if rect.w > SCREEN_W or rect.h > SCREEN_H:
                    img = pygame.transform.smoothscale(img, img.get_rect().fit(screen.get_rect()).size)
                current_image_surface = img
                break
            except Exception as e:
                print("Failed to load image:", e)

    # Text overlay
    chunks = []
    for a in arts:
        if a["kind"] == "text":
            try:
                text = a["bytes"].decode("utf-8", errors="replace")
                chunks.append(f"[{a['filename']}]\n{text}")
            except Exception:
                chunks.append(f"[{a['filename']}] <non-utf8 text>")
    if chunks:
        joined = "\n\n".join(chunks)
        excerpt = joined[:500] + ("…" if len(joined) > 500 else "")
        current_text_overlay = _wrap_text(excerpt, font, max_width=SCREEN_W - 40)

    # Audio (first)
    for a in arts:
        if a["kind"] == "audio":
            try:
                fd, path = tempfile.mkstemp(suffix=os.path.splitext(a["filename"])[1])
                os.close(fd)
                with open(path, "wb") as f:
                    f.write(a["bytes"])
                current_audio_tempfile = path
                try:
                    snd = pygame.mixer.Sound(current_audio_tempfile)
                    snd.play()
                except Exception as e:
                    print("Audio saved but could not be played by mixer:", e, "->", current_audio_tempfile)
            except Exception as e:
                print("Failed handling audio:", e)
            break

    # Videos (save & list)
    for a in arts:
        if a["kind"] == "video":
            try:
                fd, path = tempfile.mkstemp(suffix=os.path.splitext(a["filename"])[1])
                os.close(fd)
                with open(path, "wb") as f:
                    f.write(a["bytes"])
                saved_video_paths.append(path)
            except Exception as e:
                print("Failed saving video:", e)

def load_workflow_from_clipboard() -> dict:
    raw = pyperclip.paste()
    if not raw:
        raise ValueError("Clipboard is empty.")
    try:
        graph = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Clipboard content is not valid JSON: {e}") from e
    if not isinstance(graph, dict):
        raise ValueError("Workflow JSON must be a dict (API format).")
    return graph

def run_async_with_graph(graph: dict):
    global busy, status
    try:
        job = client.run_workflow(graph, poll_interval=0.5, max_wait=600)
        result_q.put(job["artifacts"])
        status = "done"
    except Exception as e:
        print("Workflow failed:", e)
        result_q.put([])
        status = f"error: {e}"
    finally:
        busy = False

running = True
reset_visual_state()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()

            # --- PRIORITY: if typing, treat keys as text (SPACE should be a space!)
            if typing_prompt:
                if event.key == pygame.K_RETURN:
                    typing_prompt = False
                    status = f"prompt set ({len(prompt_buffer)} chars)"
                elif event.key == pygame.K_ESCAPE:
                    typing_prompt = False
                    prompt_buffer = ""
                    status = "prompt cleared"
                elif event.key == pygame.K_BACKSPACE:
                    prompt_buffer = prompt_buffer[:-1]
                else:
                    ch = event.unicode
                    if ch and ch.isprintable():
                        prompt_buffer += ch
                continue  # don't fall through to command keys

            # --- Command keys (only when not typing)
            if (mods & pygame.KMOD_CTRL) and event.key == PASTE_KEY:
                try:
                    current_graph = load_workflow_from_clipboard()
                    status = "workflow loaded from clipboard"
                    print("Workflow loaded from clipboard.")
                except Exception as e:
                    status = f"paste failed: {e}"
                    print("Paste failed:", e)

            elif event.key == TYPE_TOGGLE_KEY:
                typing_prompt = True
                prompt_buffer = ""
                status = "typing prompt… (ENTER to finish, ESC to cancel)"

            elif event.key == RUN_KEY and not busy:
                reset_visual_state()
                busy = True
                status = "running…"

                import copy
                if current_graph is not None:
                    graph = copy.deepcopy(current_graph)
                elif os.path.exists(WORKFLOW_PATH):
                    graph = load_workflow_graph(WORKFLOW_PATH)
                else:
                    busy = False
                    status = "no workflow (Ctrl+V to paste or set WORKFLOW_PATH)"
                    continue

                # --- Prompt token (still supported)
                if prompt_buffer:
                    replace_token(graph, "%%PROMPT%%", prompt_buffer)

                # --- Seed handling ---
                seed = random_u32()
                repl = replace_numeric_token(graph, "%%SEED%%", seed)  # use token if present
                if repl == 0:
                    # No token found? force it everywhere sensible.
                    set_seed_on_all_nodes(graph, seed)
                last_seed = seed
                status = f"running… (seed {seed})"

                threading.Thread(target=run_async_with_graph, args=(graph,), daemon=True).start()

    # Drain results
    try:
        while True:
            arts = result_q.get_nowait()
            process_artifacts(arts)
    except queue.Empty:
        pass

    # ---- Draw ----
    screen.fill((12, 12, 16))

    if current_image_surface:
        rect = current_image_surface.get_rect(center=screen.get_rect().center)
        screen.blit(current_image_surface, rect)

    y = 16
    ui = []
    ui.append("Ctrl+V: paste workflow    T: type prompt    F5: run")
    ui.append(f"Status: {status}")
    if saved_video_paths:
        ui.append("Saved video(s):")
        for p in saved_video_paths[:3]:
            ui.append(f"  {p}")
    if prompt_buffer or typing_prompt:
        ui.append(f"Prompt: {prompt_buffer}{'|' if typing_prompt else ''}")
    if last_seed is not None:
        ui.append(f"Last seed: {last_seed}")

    for line in ui:
        surf = font.render(line, True, (230, 230, 235))
        screen.blit(surf, (16, y))
        y += surf.get_height() + 6

    if current_text_overlay:
        y += 8
        for line in current_text_overlay[:15]:
            surf = font.render(line, True, (220, 220, 230))
            screen.blit(surf, (16, y))
            y += surf.get_height() + 2

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
