
import pygame, pyperclip
from core.tokens import find_specs

class InputsForm:
    """
    Token-driven form with multiline support.
    Controls:
      - F2: close
      - ↑/↓: select field
      - Enter: edit field / save edit
      - Esc: cancel edit / close form
      - Ctrl+V while editing: paste
      - Enter while editing: inserts newline if multiline; else ends edit
      - Ctrl+Enter: end edit (multiline)
      - PgUp/PgDn/Home/End: navigate fields
    """
    def __init__(self, font=None, font_bold=None, font_mono=None, rows=12):
        self.font = font or pygame.font.SysFont(None, 24)
        self.font_bold = font_bold or pygame.font.SysFont(None, 24, bold=True)
        self.font_mono = font_mono or pygame.font.SysFont("monospace", 20)
        self.rows = rows
        self.open = False
        self.fields = []          # [{name, kind}]
        self.values = {}          # name -> str
        self.index = 0
        self.scroll = 0
        self.editing = False
        self.caret = 0            # caret position inside current text
        self.view_offset = 0      # horizontal scroll for single-line
        self.multiline = False    # current field mode

    def _is_multiline_kind(self, kind: str, name: str):
        if kind and kind.lower() == "ml":
            return True
        # heuristic: prompt-like names default to multiline
        return name.lower() in ("prompt", "prompt_1", "prompt_2", "negative_prompt", "neg_prompt", "system", "memory", "notes")

    def open_form(self, graph: dict):
        specs = find_specs(graph)
        self.fields = [{"name": s["name"], "kind": s["kind"]} for s in specs]
        # keep existing values when possible
        self.values = {f["name"]: self.values.get(f["name"], "") for f in self.fields}
        self.index = 0; self.scroll = 0; self.editing = False; self.caret = 0; self.view_offset = 0
        self.multiline = self._is_multiline_kind(self.fields[0]["kind"] if self.fields else "str", self.fields[0]["name"] if self.fields else "")
        self.open = True
        return f"inputs: {len(self.fields)} token(s)"

    def close(self):
        self.open = False
        self.editing = False

    def _current_name_kind(self):
        if not self.fields: return None, "str"
        name = self.fields[self.index]["name"]
        kind = self.fields[self.index]["kind"]
        return name, kind

    def handle_key(self, event, mods):
        if not self.open:
            return False, None

        if self.editing:
            name, kind = self._current_name_kind()
            if name is None: return True, None
            txt = self.values.get(name, "")
            # paste
            if (mods & pygame.KMOD_CTRL) and event.key == pygame.K_v:
                try:
                    clip = pyperclip.paste()
                    if clip:
                        before = txt[:self.caret]; after = txt[self.caret:]
                        txt = before + clip + after
                        self.caret += len(clip)
                        self.values[name] = txt
                        return True, None
                except Exception:
                    pass
            # end edit (ctrl+enter)
            if (mods & pygame.KMOD_CTRL) and event.key == pygame.K_RETURN:
                self.editing = False; return True, None

            if event.key == pygame.K_ESCAPE:
                self.editing = False; return True, None

            if event.key == pygame.K_RETURN:
                if self.multiline:
                    before = txt[:self.caret]; after = txt[self.caret:]
                    txt = before + "\n" + after
                    self.caret += 1
                    self.values[name] = txt
                else:
                    self.editing = False
                return True, None

            if event.key == pygame.K_BACKSPACE:
                if self.caret > 0:
                    self.values[name] = txt[:self.caret-1] + txt[self.caret:]
                    self.caret -= 1
                return True, None

            if event.key == pygame.K_DELETE:
                if self.caret < len(txt):
                    self.values[name] = txt[:self.caret] + txt[self.caret+1:]
                return True, None

            if event.key == pygame.K_LEFT:
                if self.caret > 0: self.caret -= 1
                return True, None
            if event.key == pygame.K_RIGHT:
                if self.caret < len(txt): self.caret += 1
                return True, None
            if event.key == pygame.K_HOME:
                # move to start of line for multiline, else start
                if self.multiline:
                    line_start = txt.rfind("\n", 0, self.caret) + 1
                    self.caret = line_start
                else:
                    self.caret = 0
                return True, None
            if event.key == pygame.K_END:
                if self.multiline:
                    line_end = txt.find("\n", self.caret)
                    if line_end == -1: line_end = len(txt)
                    self.caret = line_end
                else:
                    self.caret = len(txt)
                return True, None

            # typing
            ch = event.unicode
            if ch and ch.isprintable():
                before = txt[:self.caret]; after = txt[self.caret:]
                txt = before + ch + after
                self.caret += len(ch)
                self.values[name] = txt
                return True, None

            return True, None

        # not editing -> navigation or open/close
        if event.key == pygame.K_F2 or event.key == pygame.K_ESCAPE:
            self.close(); return True, "inputs closed"
        elif event.key == pygame.K_RETURN:
            self.editing = True
            name, kind = self._current_name_kind()
            self.multiline = self._is_multiline_kind(kind, name or "")
            if name is not None:
                self.caret = len(self.values.get(name, ""))
            return True, None
        elif event.key == pygame.K_UP:
            self.index = max(0, self.index - 1); return True, None
        elif event.key == pygame.K_DOWN:
            self.index = min(max(0, len(self.fields)-1), self.index + 1); return True, None
        elif event.key == pygame.K_PAGEUP:
            self.index = max(0, self.index - self.rows); return True, None
        elif event.key == pygame.K_PAGEDOWN:
            self.index = min(max(0, len(self.fields)-1), self.index + self.rows); return True, None
        elif event.key == pygame.K_HOME:
            self.index = 0; return True, None
        elif event.key == pygame.K_END:
            self.index = max(0, len(self.fields)-1); return True, None

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

        title = "Workflow Inputs (F2=close  ↑/↓ select  Enter=edit/save  Ctrl+V=paste)"
        screen.blit(self.font_bold.render(title, True, (240,240,255)), (panel_x + 14, panel_y + 12))

        list_x = panel_x + 14
        list_y = panel_y + 50
        row_h  = self.font.get_height() + 8

        # Scroll management
        if self.index < self.scroll: self.scroll = self.index
        if self.index >= self.scroll + self.rows: self.scroll = self.index - self.rows + 1
        end = min(len(self.fields), self.scroll + self.rows)

        for i in range(self.scroll, end):
            name = self.fields[i]["name"]
            kind = self.fields[i]["kind"]
            val  = self.values.get(name, "")
            y    = list_y + (i - self.scroll) * row_h
            is_sel = (i == self.index)

            # Label
            label = f"{name} ({kind})"
            screen.blit(self.font.render(label, True, (220,230,245)), (list_x, y))

            # Box
            box_x = list_x + 300
            box_w = panel_w - (box_x - panel_x) - 30
            # Single-line preview (first line only)
            preview = val.split("\n", 1)[0]
            pygame.draw.rect(screen, (35,38,48), (box_x, y-2, box_w, row_h), border_radius=6)
            if is_sel:
                pygame.draw.rect(screen, (80,130,200), (box_x, y-2, box_w, row_h), width=2, border_radius=6)
            screen.blit(self.font.render(preview[:120] + ("…" if len(preview) > 120 else ""), True, (240,240,255)), (box_x + 8, y))

        # If editing, draw an expanded multiline editor panel below list
        if self.editing and self.fields:
            name = self.fields[self.index]["name"]
            kind = self.fields[self.index]["kind"]
            val  = self.values.get(name, "")
            ml   = self._is_multiline_kind(kind, name)
            edit_h = int(panel_h * 0.38)
            edit_y = panel_y + panel_h - edit_h - 12
            R.draw_panel(screen, (panel_x+12, edit_y, panel_w-24, edit_h), bg=(28,32,44))

            cap = f"Editing: {name}  ({'multiline' if ml else 'single-line'})   Enter={'newline' if ml else 'save'}   Ctrl+Enter=save   Ctrl+V=paste"
            screen.blit(self.font_bold.render(cap, True, (230,235,255)), (panel_x + 20, edit_y + 8))

            # text area
            area_x = panel_x + 20
            area_y = edit_y + 36
            area_w = panel_w - 40
            area_h = edit_h - 50
            pygame.draw.rect(screen, (20,22,30), (area_x, area_y, area_w, area_h), border_radius=6)
            pygame.draw.rect(screen, (70,90,120), (area_x, area_y, area_w, area_h), width=2, border_radius=6)

            # render lines with soft wrap
            lines = []
            space_w = self.font_mono.size(" ")[0]
            current = ""
            for ch in val.replace("\t", "    "):
                trial = current + ch
                if self.font_mono.size(trial)[0] <= area_w - 16 or ch == "\n":
                    current = trial
                else:
                    lines.append(current)
                    current = ch
                if ch == "\n":
                    lines.append(current[:-1])
                    current = ""
            lines.append(current)

            # draw lines
            y = area_y + 8
            for i, line in enumerate(lines):
                screen.blit(self.font_mono.render(line, True, (235,235,245)), (area_x + 8, y))
                y += self.font_mono.get_height() + 4

            # simple caret at end (approx)
            if True:
                caret_txt = val[:self.caret]
                caret_line = caret_txt.split("\n")[-1]
                caret_x = area_x + 8 + self.font_mono.size(caret_line)[0]
                caret_y = area_y + 8 + (len(caret_txt.split("\n")) - 1) * (self.font_mono.get_height() + 4)
                pygame.draw.line(screen, (200,220,255), (caret_x, caret_y), (caret_x, caret_y + self.font_mono.get_height()), 2)
