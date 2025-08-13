
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class AppState:
    status: str = "idle"
    last_seed: Optional[int] = None
    current_graph: Optional[dict] = None
    current_graph_path: Optional[str] = None
    saved_video_paths: List[str] = field(default_factory=list)
    overlay_text_lines: List[str] = field(default_factory=list)
    current_image_surface: Any = None  # pygame.Surface at runtime
    current_audio_tempfile: Optional[str] = None
    busy: bool = False

@dataclass
class PickerState:
    open: bool = False

@dataclass
class FormState:
    open: bool = False
    tokens: List[str] = field(default_factory=list)
    values: Dict[str, str] = field(default_factory=dict)
