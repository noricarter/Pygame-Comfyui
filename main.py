
import os, tempfile, pygame
from io import BytesIO

from app.state import AppState
from app.runner import Runner
from core.workflow_io import ensure_dir, load_workflow_graph, scan_workflows
from core.tokens import find_specs, apply_token_values
from core.seed import random_u32, apply_seed_policy
from core.artifacts import split_artifacts
from ui.renderer import image_from_bytes, wrap_text
from ui.picker import WorkflowPicker
from ui.form import InputsForm
from ui.hud import draw_hud

pygame.init()
try:
    pygame.mixer.init()
except Exception as e:
    print("Audio disabled (mixer init failed):", e)

# Config
SCREEN_W, SCREEN_H = 1280, 720
WORKFLOW_DIR = "workflows"
PICKER_ROWS = 18

# Keys
RUN_KEY           = pygame.K_F5
PICKER_TOGGLE_KEY = pygame.K_F1
INPUTS_FORM_KEY   = pygame.K_F2
REFRESH_KEY       = pygame.K_r

# Setup
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Pygame ↔ ComfyUI (Modular)")
clock = pygame.time.Clock()
font  = pygame.font.SysFont(None, 24)
font_bold = pygame.font.SysFont(None, 24, bold=True)
font_mono = pygame.font.SysFont("monospace", 20)

state = AppState()
runner = Runner()
picker = WorkflowPicker(WORKFLOW_DIR, rows=PICKER_ROWS, font=font, font_bold=font_bold)
form   = InputsForm(font=font, font_bold=font_bold, font_mono=font_mono, rows=12)

ensure_dir(WORKFLOW_DIR)

def reset_visual_state():
    state.current_image_surface = None
    state.overlay_text_lines = []
    if state.current_audio_tempfile and os.path.exists(state.current_audio_tempfile):
        try: os.remove(state.current_audio_tempfile)
        except Exception: pass
    state.current_audio_tempfile = None
    state.saved_video_paths = []

def process_artifacts_into_state(arts: list[dict]):
    imgs, txts, auds, vids, _ = split_artifacts(arts)
    # image (first)
    for a in imgs:
        surf = image_from_bytes(a["bytes"], SCREEN_W, SCREEN_H)
        if surf is not None:
            state.current_image_surface = surf
            break
    # text overlay
    if txts:
        joined = "\n\n".join([f"[{a['filename']}]\n" + a["bytes"].decode("utf-8", "replace") for a in txts])
        excerpt = joined[:800] + ("…" if len(joined) > 800 else "")
        state.overlay_text_lines = wrap_text(excerpt, font, max_width=SCREEN_W - 40)
    # audio (first)
    for a in auds:
        try:
            fd, path = tempfile.mkstemp(suffix=os.path.splitext(a["filename"])[1])
            os.close(fd)
            with open(path, "wb") as f:
                f.write(a["bytes"])
            state.current_audio_tempfile = path
            try:
                snd = pygame.mixer.Sound(state.current_audio_tempfile)
                snd.play()
            except Exception as e:
                print("Audio saved but could not be played by mixer:", e, "->", state.current_audio_tempfile)
        except Exception as e:
            print("Failed handling audio:", e)
        break
    # videos
    for a in vids:
        try:
            fd, path = tempfile.mkstemp(suffix=os.path.splitext(a["filename"])[1])
            os.close(fd)
            with open(path, "wb") as f:
                f.write(a["bytes"])
            state.saved_video_paths.append(path)
        except Exception as e:
            print("Failed saving video:", e)

running = True
reset_visual_state()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False; break

        if event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()

            # Inputs form has priority when open
            if form.open:
                consumed, msg = form.handle_key(event, mods)
                if consumed:
                    if msg: state.status = msg
                    continue

            # Picker when open
            if picker.open:
                consumed, msg = picker.handle_key(event)
                if consumed:
                    if msg == "select":
                        if picker.items:
                            rel = picker.items[picker.index]
                            path = os.path.join(WORKFLOW_DIR, rel)
                            try:
                                state.current_graph = load_workflow_graph(path)
                                state.current_graph_path = rel
                                state.status = f"loaded: {rel}"
                                # update form tokens
                                form.open_form(state.current_graph)
                                form.close()  # don't show by default
                            except Exception as e:
                                state.current_graph = None
                                state.current_graph_path = None
                                state.status = f"load failed: {e}"
                        picker.close()
                    elif msg:
                        state.status = msg
                    continue

            # Commands
            if event.key == PICKER_TOGGLE_KEY:
                state.status = picker.open_picker()

            elif event.key == INPUTS_FORM_KEY:
                if state.current_graph:
                    state.status = form.open_form(state.current_graph)
                else:
                    state.status = "load a workflow first (F1)"

            elif event.key == RUN_KEY and not state.busy:
                if not state.current_graph and not state.current_graph_path:
                    items = scan_workflows(WORKFLOW_DIR)
                    if items:
                        rel = items[0]
                        state.current_graph = load_workflow_graph(os.path.join(WORKFLOW_DIR, rel))
                        state.current_graph_path = rel
                    else:
                        state.status = f"no workflows in '{WORKFLOW_DIR}' (press F1 to pick)"
                        continue

                import copy
                g = copy.deepcopy(state.current_graph or {})
                reset_visual_state()
                state.busy = True

                # 1) apply token values
                apply_token_values(g, form.values)

                # 2) seed policy
                tokens_present = {spec["name"] for spec in (find_specs(g) or [])}
                chosen_seed = apply_seed_policy(g, tokens_present, form.values.get("SEED"))
                state.last_seed = chosen_seed

                state.status = f"running… (seed {state.last_seed})"
                runner.run_async(g, poll_interval=0.5, max_wait=600)

    # Drain results
    try:
        while True:
            arts = runner.q.get_nowait()
            process_artifacts_into_state(arts)
            state.busy = False
            if not arts:
                state.status = "done (no artifacts)"
            else:
                state.status = "done"
    except Exception:
        pass

    # ---- Draw ----
    screen.fill((12, 12, 16))

    if state.current_image_surface:
        rect = state.current_image_surface.get_rect(center=screen.get_rect().center)
        screen.blit(state.current_image_surface, rect)

    draw_hud(
        screen, font,
        status=state.status,
        current_graph_path=state.current_graph_path,
        form_tokens=[f["name"] for f in (find_specs(state.current_graph or {}) or [])],
        last_seed=state.last_seed,
        saved_video_paths=state.saved_video_paths,
        overlay_text_lines=state.overlay_text_lines,
    )

    # overlays
    if picker.open: picker.draw(screen)
    if form.open:   form.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
