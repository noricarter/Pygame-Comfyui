
import pygame, os
from ui.renderer import wrap_text

def draw_hud(screen, font, status, current_graph_path, form_tokens, last_seed, saved_video_paths, overlay_text_lines):
    y = 16
    ui_lines = []
    ui_lines.append("F1: pick workflow    F2: inputs form    F5: run    R: refresh (in picker)")
    ui_lines.append(f"Status: {status}")
    if current_graph_path:
        ui_lines.append(f"Workflow: {current_graph_path}")
    if form_tokens:
        ui_lines.append(f"Inputs: {', '.join(form_tokens)}")
    if last_seed is not None:
        ui_lines.append(f"Last seed: {last_seed}")
    if saved_video_paths:
        ui_lines.append("Saved video(s):")
        for p in saved_video_paths[:3]:
            ui_lines.append(f"  {p}")

    for line in ui_lines:
        screen.blit(font.render(line, True, (230,230,235)), (16, y))
        y += font.get_height() + 6

    if overlay_text_lines:
        y += 8
        for line in overlay_text_lines[:15]:
            screen.blit(font.render(line, True, (220,220,230)), (16, y))
            y += font.get_height() + 2
