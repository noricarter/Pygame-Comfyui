
import os, pygame
from core.workflow_io import scan_workflows

class WorkflowPicker:
    def __init__(self, workdir: str, rows=18, font=None, font_bold=None):
        self.workdir = workdir
        self.rows = rows
        self.font = font or pygame.font.SysFont(None, 24)
        self.font_bold = font_bold or pygame.font.SysFont(None, 24, bold=True)
        self.open = False
        self.items = []
        self.index = 0
        self.scroll = 0

    def open_picker(self):
        self.items = scan_workflows(self.workdir)
        self.index = 0; self.scroll = 0
        self.open = True
        return f"picker: {len(self.items)} file(s)"

    def close(self):
        self.open = False

    def nudge(self, delta):
        if not self.items: self.index = 0; return
        self.index = max(0, min(len(self.items)-1, self.index + delta))

    def handle_key(self, event):
        if event.key == pygame.K_ESCAPE or event.key == pygame.K_F1:
            self.close(); return True, "picker closed"
        elif event.key == pygame.K_RETURN:
            return True, "select"
        elif event.key == pygame.K_UP:
            self.nudge(-1); return True, None
        elif event.key == pygame.K_DOWN:
            self.nudge(+1); return True, None
        elif event.key == pygame.K_PAGEUP:
            self.nudge(-self.rows); return True, None
        elif event.key == pygame.K_PAGEDOWN:
            self.nudge(+self.rows); return True, None
        elif event.key == pygame.K_HOME:
            self.index = 0; return True, None
        elif event.key == pygame.K_END:
            self.index = max(0, len(self.items)-1); return True, None
        elif event.key == pygame.K_r:
            return True, self.open_picker()
        return False, None

    def draw(self, screen):
        import ui.renderer as R
        SCREEN_W, SCREEN_H = screen.get_size()
        pad = 12
        panel_w = SCREEN_W - 2*pad
        panel_h = int(SCREEN_H * 0.75)
        panel_x = pad
        panel_y = (SCREEN_H - panel_h)//2
        R.draw_panel(screen, (panel_x, panel_y, panel_w, panel_h))

        title = f"Select workflow (↑/↓ PgUp/PgDn Home/End, Enter=select, R=refresh, F1=close)"
        screen.blit(self.font_bold.render(title, True, (240,240,255)), (panel_x + 14, panel_y + 12))

        list_x = panel_x + 14; list_y = panel_y + 46
        row_h  = self.font.get_height() + 6

        if self.index < self.scroll: self.scroll = self.index
        if self.index >= self.scroll + self.rows: self.scroll = self.index - self.rows + 1

        end = min(len(self.items), self.scroll + self.rows)
        for i in range(self.scroll, end):
            rel = self.items[i]; y = list_y + (i - self.scroll) * row_h
            is_sel = (i == self.index)
            if is_sel:
                pygame.draw.rect(screen, (55,100,160), (list_x-6, y-2, panel_w-28, row_h), border_radius=6)
            color = (250,250,250) if is_sel else (220,220,230)
            screen.blit(self.font.render(rel, True, color), (list_x, y))
