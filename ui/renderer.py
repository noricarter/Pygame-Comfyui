
import pygame
from io import BytesIO

def draw_panel(surf, rect, bg=(24,28,36), border=(100,110,130), radius=12, border_w=2):
    pygame.draw.rect(surf, bg, rect, border_radius=radius)
    pygame.draw.rect(surf, border, rect, width=border_w, border_radius=radius)

def wrap_text(text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines, line = [], ""
    for w in words:
        trial = (line + " " + w).strip()
        if font.size(trial)[0] <= max_width:
            line = trial
        else:
            if line: lines.append(line)
            line = w
    if line: lines.append(line)
    return lines

def image_from_bytes(data: bytes, max_w: int, max_h: int):
    try:
        img = pygame.image.load(BytesIO(data))
        rect = img.get_rect()
        if rect.w > max_w or rect.h > max_h:
            img = pygame.transform.smoothscale(img, img.get_rect().fit(pygame.Rect(0,0,max_w,max_h)).size)
        return img
    except Exception as e:
        print("image_from_bytes failed:", e)
        return None
