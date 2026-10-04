import ast
import json
import os
import re
import sys
import math
import random
import pygame
import pygame.scrap
from datetime import datetime

# -----------------------------------------------------------------------------
# Steampunk Palette & Configuration
# -----------------------------------------------------------------------------
BLACK = (15, 12, 10)
BRASS = (181, 137, 0)
BRASS_DARK = (101, 67, 33)
BRASS_LIGHT = (255, 215, 0)
COPPER = (184, 115, 51)
NIXIE_GLOW = (255, 140, 0)
VOICE_ACTIVE = (0, 255, 127)
CYAN_GLOW = (0, 210, 255)
AMBER_GLOW = (255, 160, 20)
TEXT_COLOR = (255, 240, 190)
MUTED_BRASS = (140, 110, 70)

WIDTH, HEIGHT = 808, 784
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NIXIE_DIR = os.path.join(BASE_DIR, "nixie_images", "drawable-hdpi")
if not os.path.exists(NIXIE_DIR):
    NIXIE_DIR = os.path.expanduser("~/.local/share/steampunk_assets/nixie_tubes")
if not os.path.exists(NIXIE_DIR):
    NIXIE_DIR = "/home/pcarff/Downloads/nixie_images/drawable-hdpi"

SIGNALS_DIRS = ["/dev/shm/signals", "/tmp/signals"]


# -----------------------------------------------------------------------------
# Signal Bus State & Typed Input Writer
# -----------------------------------------------------------------------------
def get_voice_state() -> str:
    """Read real-time voice state from backtalk signal bus."""
    for s_dir in SIGNALS_DIRS:
        state_file = os.path.join(s_dir, ".voice_state")
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    return f.read().strip().lower()
            except Exception:
                pass
    return "idle"


def send_typed_message(text: str):
    """Deliver typed message to backtalk through signal bus queue file."""
    for s_dir in SIGNALS_DIRS:
        try:
            os.makedirs(s_dir, exist_ok=True)
            sig_file = os.path.join(s_dir, ".typed_input")
            with open(sig_file, "w", encoding="utf-8") as f:
                f.write(text.strip() + "\n")
            # Immediate responsive visual feedback
            state_file = os.path.join(s_dir, ".voice_state")
            with open(state_file, "w") as sf:
                sf.write("thinking")
            return True
        except Exception:
            pass
    return False


# -----------------------------------------------------------------------------
# System Clipboard Access (Tkinter / Pygame Scrap / CLI)
# -----------------------------------------------------------------------------
_tk_root = None


def get_clipboard_text() -> str:
    """Retrieve plain text from system clipboard using the best available backend."""
    global _tk_root
    # 1. Tkinter (fastest & most reliable on Linux X11, ~0.3ms)
    try:
        if _tk_root is None:
            import tkinter as tk
            _tk_root = tk.Tk()
            _tk_root.withdraw()
        text = _tk_root.clipboard_get()
        if text:
            return text
    except Exception:
        _tk_root = None

    # 2. Pygame scrap
    try:
        if pygame.scrap.get_init():
            for mime in ("text/plain;charset=utf-8", "UTF8_STRING", "TEXT"):
                raw = pygame.scrap.get(mime)
                if raw:
                    return raw.decode("utf-8", errors="replace").rstrip("\x00")
    except Exception:
        pass

    # 3. CLI fallbacks (xclip / xsel / wl-paste)
    import subprocess
    import shutil
    for cmd in (
        ["xclip", "-selection", "clipboard", "-o"],
        ["xsel", "-b", "-o"],
        ["wl-paste", "--no-newline"],
    ):
        if shutil.which(cmd[0]):
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=0.3)
                if res.returncode == 0 and res.stdout:
                    return res.stdout
            except Exception:
                pass
    return ""


def set_clipboard_text(text: str):
    """Set system clipboard text."""
    global _tk_root
    try:
        if _tk_root is None:
            import tkinter as tk
            _tk_root = tk.Tk()
            _tk_root.withdraw()
        _tk_root.clipboard_clear()
        _tk_root.clipboard_append(text)
        _tk_root.update()
    except Exception:
        _tk_root = None


# -----------------------------------------------------------------------------
# Nixie Tube Component & Realistic Industrial Backplate Bank
# -----------------------------------------------------------------------------
class NixieTube:
    def __init__(self, index=0, x=0, y=0, size=60, bank=None):
        self.index = index
        self.x = x
        self.y = y
        self.size = size
        self.value = str(random.randint(0, 9))
        self.bank = bank

    def draw(self, surface):
        if self.bank:
            d_idx = int(self.value) if self.value.isdigit() else 0
            d_surf = self.bank.digit_surfaces.get(d_idx)
            if d_surf:
                surface.blit(d_surf, (self.x, self.y))


class NixieBank:
    def __init__(self, x=70, y=88, width=660, height=120):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

        # Load Realistic Rustic Backplate
        bp_paths = [
            os.path.join(BASE_DIR, "nixie_backplate.png"),
            os.path.expanduser("~/.local/share/steampunk_assets/textures/nixie_backplate.png"),
            "/tmp/nixie_backplate_master.png",
        ]
        self.backplate = None
        for p in bp_paths:
            if os.path.exists(p):
                raw = pygame.image.load(p).convert_alpha()
                self.backplate = pygame.transform.smoothscale(raw, (self.width, self.height))
                break

        # Sizing: 44x80 socket chamber, 42x76 slender digit (ratio 0.553, eliminating squatness)
        self.inner_w = 44
        self.inner_h = 80
        self.digit_w = 42
        self.digit_h = 76

        digit_names = [
            "zeroam.jpg", "oneam.jpg", "twoam.jpg", "threeam.jpg",
            "fouram.jpg", "fiveam.jpg", "sixam.jpg", "sevenam.jpg",
            "eightam.jpg", "nineam.jpg"
        ]

        # Pre-render luminous slender digits (warm amber glow + slender digit + glass glint)
        self.digit_surfaces = {}
        for i in range(10):
            surf = pygame.Surface((self.inner_w, self.inner_h), pygame.SRCALPHA)

            # 1. Warm radial amber glow behind filament
            gcx, gcy = self.inner_w // 2, self.inner_h // 2
            for r in range(self.inner_h // 2, 0, -3):
                alpha = int(45 * (1.0 - r / (self.inner_h // 2)))
                pygame.draw.ellipse(surf, (255, 140, 0, alpha), (gcx - r, gcy - r, r * 2, r * 2))

            # 2. Slender scaled Nixie digit
            img_path = os.path.join(NIXIE_DIR, digit_names[i])
            if os.path.exists(img_path):
                raw_d = pygame.image.load(img_path).convert_alpha()
                scaled_d = pygame.transform.smoothscale(raw_d, (self.digit_w, self.digit_h))
                surf.blit(scaled_d, (1, 2))

            # 3. Specular glass glint (vertical reflection streak on left edge)
            pygame.draw.line(surf, (255, 255, 255, 45), (3, 6), (3, self.inner_h - 8), 2)
            pygame.draw.line(surf, (255, 255, 255, 80), (4, 10), (4, self.inner_h - 14), 1)

            self.digit_surfaces[i] = surf

        # Create 8 tube units aligned with the backplate's milled brass socket bays
        self.tubes = []
        for i in range(8):
            tx = self.x + 56 + i * 72
            ty = self.y + 20
            self.tubes.append(NixieTube(index=i, x=tx, y=ty, bank=self))

    def draw(self, surface):
        if self.backplate:
            surface.blit(self.backplate, (self.x, self.y))
        for tube in self.tubes:
            d_idx = int(tube.value) if tube.value.isdigit() else 0
            d_surf = self.digit_surfaces.get(d_idx)
            if d_surf:
                surface.blit(d_surf, (tube.x, tube.y))


# -----------------------------------------------------------------------------
# Operational Steampunk Clock Component (FLUX Chronometer)
# -----------------------------------------------------------------------------
class SteampunkClock:
    def __init__(self, cx, cy, size=154):
        self.cx = cx
        self.cy = cy
        self.size = size
        self.radius = size // 2
        self.scale = size / 1024.0

        paths = [
            os.path.join(BASE_DIR, "clock_dial_base_trans.png"),
            "/home/pcarff/Pictures/Flux_Generations/clock_dial_base_trans.png",
            os.path.expanduser("~/.local/share/steampunk_assets/textures/clock_dial_base_trans.png"),
        ]
        self.dial_img = None
        for p in paths:
            if os.path.exists(p):
                raw = pygame.image.load(p).convert_alpha()
                self.dial_img = pygame.transform.smoothscale(raw, (size, size))
                break

    def draw(self, surface):
        if self.dial_img:
            surface.blit(self.dial_img, (self.cx - self.radius, self.cy - self.radius))

        now = datetime.now()
        hours = now.hour % 12
        minutes = now.minute
        seconds = now.second
        usecs = now.microsecond

        sec_val = seconds + usecs / 1_000_000.0
        min_val = minutes + sec_val / 60.0
        hour_val = hours + min_val / 60.0

        hour_angle = math.radians(hour_val * 30.0 - 90.0)
        min_angle = math.radians(min_val * 6.0 - 90.0)
        sec_angle = math.radians(sec_val * 6.0 - 90.0)

        hour_len = 175.0 * self.scale
        min_len = 245.0 * self.scale
        sec_len = 270.0 * self.scale

        # Hour Hand (lancet pointer with glowing amber core)
        self._draw_lancet(surface, hour_angle, hour_len, 4.5, (255, 175, 40), (180, 135, 30))

        # Minute Hand (slender lancet pointer)
        self._draw_lancet(surface, min_angle, min_len, 3.5, (255, 185, 50), (180, 135, 30))

        # Second Hand (fine copper / vermillion needle)
        cos_s = math.cos(sec_angle)
        sin_s = math.sin(sec_angle)
        sx = self.cx + sec_len * cos_s
        sy = self.cy + sec_len * sin_s
        tx = self.cx - 26 * self.scale * cos_s
        ty = self.cy - 26 * self.scale * sin_s

        # Shadow
        pygame.draw.line(surface, (15, 10, 8), (tx + 1, ty + 2), (sx + 1, sy + 2), 2)
        # Needle
        pygame.draw.line(surface, (230, 50, 40), (self.cx, self.cy), (sx, sy), 2)
        pygame.draw.line(surface, (184, 115, 51), (tx, ty), (self.cx, self.cy), 2)
        # Counterbalance
        pygame.draw.circle(surface, (255, 215, 0), (int(tx), int(ty)), max(2, int(3 * self.scale)))

        # Polished Brass Center Hub
        hub_r = max(4, int(28.0 * self.scale))
        pygame.draw.circle(surface, (25, 16, 10), (self.cx + 1, self.cy + 2), hub_r + 1)
        pygame.draw.circle(surface, (181, 137, 0), (self.cx, self.cy), hub_r)
        pygame.draw.circle(surface, (255, 215, 0), (self.cx, self.cy), hub_r - 2)
        pygame.draw.circle(surface, (190, 140, 20), (self.cx, self.cy), hub_r - 4)
        # Specular dot
        pygame.draw.circle(surface, (255, 255, 220), (self.cx - int(hub_r * 0.35), self.cy - int(hub_r * 0.35)), max(1, int(hub_r * 0.25)))

    def _draw_lancet(self, surface, angle, length, width, core_color, border_color):
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        perp_cos = -sin_a
        perp_sin = cos_a

        tip_x = self.cx + length * cos_a
        tip_y = self.cy + length * sin_a
        base_l_x = self.cx + width * perp_cos
        base_l_y = self.cy + width * perp_sin
        base_r_x = self.cx - width * perp_cos
        base_r_y = self.cy - width * perp_sin
        tail_x = self.cx - (length * 0.18) * cos_a
        tail_y = self.cy - (length * 0.18) * sin_a

        poly = [(tip_x, tip_y), (base_r_x, base_r_y), (tail_x, tail_y), (base_l_x, base_l_y)]

        # Drop shadow
        shadow_poly = [(x + 2, y + 2) for x, y in poly]
        pygame.draw.polygon(surface, (12, 8, 6), shadow_poly)

        # Outer border
        pygame.draw.polygon(surface, border_color, poly)

        # Luminous inner core
        inner_poly = [
            (tip_x - 3 * cos_a, tip_y - 3 * sin_a),
            (self.cx - (width * 0.5) * perp_cos, self.cy - (width * 0.5) * perp_sin),
            (tail_x + 3 * cos_a, tail_y + 3 * sin_a),
            (self.cx + (width * 0.5) * perp_cos, self.cy + (width * 0.5) * perp_sin)
        ]
        pygame.draw.polygon(surface, core_color, inner_poly)


# -----------------------------------------------------------------------------
# Operational Analog Telemetry Meter Component
# -----------------------------------------------------------------------------
class AnalogMeter:
    def __init__(self, cx, cy, size=140, face_name="meter_face_dial_trans.png"):
        self.cx = cx
        self.cy = cy
        self.size = size
        self.radius = size // 2
        path = os.path.join(BASE_DIR, face_name)
        if not os.path.exists(path):
            path = os.path.expanduser(f"~/.local/share/steampunk_assets/textures/{face_name}")
        self.face_img = None
        if os.path.exists(path):
            raw = pygame.image.load(path).convert_alpha()
            self.face_img = pygame.transform.smoothscale(raw, (size, size))
        self.angle = 0.0
        self.target_angle = 0.0

    def update(self, is_working, is_speaking):
        if is_working:
            self.target_angle = random.uniform(-38, 38)
        elif is_speaking:
            self.target_angle = math.sin(pygame.time.get_ticks() * 0.008) * 22.0
        else:
            self.target_angle = math.sin(pygame.time.get_ticks() * 0.002) * 8.0 - 15.0
        self.angle += (self.target_angle - self.angle) * 0.15

    def draw(self, surface):
        if self.face_img:
            surface.blit(self.face_img, (self.cx - self.radius, self.cy - self.radius))
        
        rad = math.radians(self.angle - 90)
        r = int(self.size * 0.26)
        tx = self.cx + r * math.cos(rad)
        ty = self.cy + r * math.sin(rad)
        
        # Shadow
        pygame.draw.line(surface, (15, 10, 8), (self.cx + 1, self.cy + 2), (tx + 1, ty + 2), 2)
        # Vermillion Needle
        pygame.draw.line(surface, (220, 45, 30), (self.cx, self.cy), (tx, ty), 2)
        # Brass Pivot Hub
        pygame.draw.circle(surface, (181, 137, 0), (self.cx, self.cy), 6)
        pygame.draw.circle(surface, (255, 215, 0), (self.cx, self.cy), 3)


# -----------------------------------------------------------------------------
# Token Status Plates (Claude / Gemini / AGY / MILO) in the side bays
# -----------------------------------------------------------------------------
TOKEN_CMD = os.path.join(os.path.dirname(BASE_DIR), "milo-tools", "milo-tokens")
TOKEN_REFRESH_S = 60


class TokenPoller:
    """Runs milo-tokens in a background thread every minute; the draw loop
    only ever reads the last parsed result."""

    def __init__(self):
        import threading
        self.status = None
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        import json
        import subprocess
        import time
        while True:
            try:
                res = subprocess.run([TOKEN_CMD, "--json"], capture_output=True, text=True, timeout=45)
                if res.returncode == 0:
                    self.status = json.loads(res.stdout)
            except Exception:
                pass
            time.sleep(TOKEN_REFRESH_S)


def _human(n):
    n = n or 0
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "k")):
        if n >= div:
            return f"{n / div:.1f}{suf}".replace(".0", "")
    return str(int(n))


def token_plate_rows(status):
    """-> {agent: (title, badge, big, detail, bar_pct or None)}"""
    import time
    rows = {}
    if not status:
        return rows
    c = status.get("claude", {})
    five = (c.get("plan") or {}).get("five_hour") or {}
    week = (c.get("plan") or {}).get("seven_day") or {}
    now = time.time()
    # A limit window that has already reset makes the saved % stale.
    five_pct = five.get("pct") if (five.get("resets_at") or 0) > now else None
    week_pct = week.get("pct") if (week.get("resets_at") or 0) > now else None
    five_left = (100.0 - five_pct) if five_pct is not None else None
    week_left = (100.0 - week_pct) if week_pct is not None else None
    rows["claude"] = ("CLAUDE",
                      f"5H {five_pct:.0f}% · {five_left:.0f}% LEFT" if five_pct is not None else "5H --",
                      _human(c.get("today_total")),
                      (f"WK {week_pct:.0f}% · {week_left:.0f}% LEFT · " if week_pct is not None else "") + f"7D {_human(c.get('week_total'))}",
                      five_pct)
    g = status.get("gemini", {})
    rows["gemini"] = ("GEMINI", "CLI", _human(g.get("today_total")),
                      f"7D {_human(g.get('week_total'))}" + ("" if g.get("last_used") else " · IDLE"), None)
    a = status.get("agy", {})
    rows["agy"] = ("AGY", "ANTIGRAVITY", _human(a.get("today_total")),
                   f"7D {_human(a.get('week_total'))}" + ("" if a.get("last_used") else " · IDLE"), None)
    m = status.get("milo", {})
    ctx = m.get("context") or {}
    ctx_pct = 100.0 * ctx["used"] / ctx["max"] if ctx.get("max") else None
    rows["milo"] = ("MILO", f"CTX {ctx_pct:.0f}%" if ctx_pct is not None else "OFFLINE",
                    _human(m.get("today_total")),
                    f"7D {_human(m.get('week_total'))} · {_human(ctx.get('used'))} CTX", ctx_pct)
    return rows


class TokenPlate:
    W, H = 160, 62

    def __init__(self, cx, y, agent, fonts):
        self.rect = pygame.Rect(cx - self.W // 2, y, self.W, self.H)
        self.agent = agent
        self.f_title, self.f_big, self.f_tiny = fonts
        self.bg = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
        pygame.draw.rect(self.bg, (12, 9, 7, 225), self.bg.get_rect(), border_radius=5)

    def draw(self, surface, row):
        r = self.rect
        surface.blit(self.bg, r.topleft)
        pygame.draw.rect(surface, BRASS, r, width=1, border_radius=5)
        for ix, iy in ((r.left + 4, r.top + 4), (r.right - 5, r.top + 4),
                       (r.left + 4, r.bottom - 5), (r.right - 5, r.bottom - 5)):
            pygame.draw.circle(surface, BRASS_DARK, (ix, iy), 2)

        title, badge, big, detail, pct = row or (self.agent.upper(), "", "--", "awaiting telemetry", None)
        surface.blit(self.f_title.render(title, True, BRASS_LIGHT), (r.left + 10, r.top + 4))
        b = self.f_tiny.render(badge, True, MUTED_BRASS if pct is None else TEXT_COLOR)
        surface.blit(b, (r.right - 10 - b.get_width(), r.top + 6))

        # Today's total in Nixie amber with a soft glow
        big_s = self.f_big.render(big, True, NIXIE_GLOW)
        glow = self.f_big.render(big, True, (255, 110, 0))
        glow.set_alpha(70)
        bx = r.left + 10
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            surface.blit(glow, (bx + ox, r.top + 17 + oy))
        surface.blit(big_s, (bx, r.top + 17))
        today = self.f_tiny.render("TODAY", True, MUTED_BRASS)
        surface.blit(today, (bx + big_s.get_width() + 6, r.top + 26))

        surface.blit(self.f_tiny.render(detail, True, (200, 175, 120)), (r.left + 10, r.top + 40))

        # Usage bar: amber, turning red past 80%
        bar = pygame.Rect(r.left + 10, r.bottom - 9, r.width - 20, 4)
        pygame.draw.rect(surface, (40, 30, 20), bar, border_radius=2)
        if pct is not None:
            fill = bar.copy()
            fill.width = max(2, int(bar.width * min(pct, 100) / 100))
            color = (230, 60, 40) if pct >= 80 else AMBER_GLOW
            pygame.draw.rect(surface, color, fill, border_radius=2)


# -----------------------------------------------------------------------------
# Reference Plaque (F1 or click the nameplate): keys, voice commands, tools.
# Rebuilt from backtalk's own config/source on every open, so a new milo-tool
# or voice phrase shows up without touching this file.
# -----------------------------------------------------------------------------
AGENT_ROOT = os.path.dirname(BASE_DIR)
BACKTALK_DIR = os.path.join(AGENT_ROOT, "backtalk")
TOOLS_DIR = os.path.join(AGENT_ROOT, "milo-tools")

VOICE_HELP = {
    "clear": "Wipe the conversation and start fresh",
    "compact": "Summarize the session to free context",
    "deep": "Deep model for this session (slower)",
    "fast": "Back to the fast model",
    "brain": "local (Qwen on Cortex), claude, or agy (antigravity)",
    "usage": "Token and cost report",
    "micopen": "Hands-free: open mic, no key needed",
    "micptt": "Back to push-to-talk",
    "noask": "Auto-approve MILO's actions",
    "ask": "Ask before acting again",
}


def _first_sentence(text):
    text = text.split(" Usage:")[0].strip()
    m = re.search(r"(?<=[.!?])\s", text)
    return text[:m.start()] if m else text


def _ptt_label():
    try:
        with open(os.path.join(BACKTALK_DIR, "backtalk.json")) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
    key = str(cfg.get("ptt_key", "right_alt")).replace("_", " ").title()
    return key, cfg.get("mic_mode", "ptt"), cfg.get("active_brain", "local")


def load_reference():
    ptt, mic_mode, brain = _ptt_label()
    talk = f"Hold to talk, release to send" + (" (hands-free is on)" if mic_mode == "open" else "")
    keys = [
        (f"{ptt} (hold)", talk),
        ("Enter", "Send the typed message"),
        ("Ctrl+V / Shift+Ins", "Paste clipboard into the input line"),
        ("Right-click", "Paste clipboard into the input line"),
        ("Ctrl+C", "Copy the input line to the clipboard"),
        ("Ctrl+U", "Clear the input line"),
        ("Ctrl+W / Ctrl+Bksp", "Delete the previous word"),
        ("Ctrl + / Ctrl -", "Zoom the console window"),
        ("Ctrl+0", "Reset zoom"),
        ("F1 / nameplate", "Open or close this plaque"),
        ("Tab / ← →", "Next / previous plaque section"),
        ("↑ ↓ / wheel", "Scroll the plaque"),
        ("Esc", "Close the plaque, else exit the console"),
        ("Ctrl+C (terminal)", "Hang up the voice line"),
    ]

    voice = []
    try:
        src = open(os.path.join(BACKTALK_DIR, "backtalk", "main.py")).read()
        tree = ast.parse(src)
        verbs = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "CONSOLE_VERBS" for t in node.targets):
                verbs = ast.literal_eval(node.value)
        for verb, phrases in verbs.items():
            if verb == "brain":
                said = "switch brain to <name>"
            else:
                said = phrases[0]
            voice.append((said, VOICE_HELP.get(verb, verb)))
    except Exception as e:
        voice.append(("(unavailable)", f"Could not read backtalk voice commands: {e}"))
    voice.append(("set effort to <level>", "low, medium, high, xhigh or max"))
    voice.append(("goodbye milo", "Hang up the voice line"))

    # A row with desc None is drawn as a sub-heading.
    builtin, shell = [], []
    try:
        src = open(os.path.join(BACKTALK_DIR, "backtalk", "brain.py")).read()
        for m in re.finditer(r"^- ([a-z_]+)\(([^)]*)\): (.+)$", src, re.M):
            builtin.append((m.group(1), _first_sentence(m.group(3))))
    except Exception:
        pass
    try:
        for name in sorted(os.listdir(TOOLS_DIR)):
            path = os.path.join(TOOLS_DIR, name)
            if not (os.path.isfile(path) and os.access(path, os.X_OK)):
                continue
            # Same rule as backtalk's _load_milo_tools: a line starting with
            # "# milo-tool:" within the first 5 lines.
            with open(path, errors="replace") as f:
                head = [next(f, "") for _ in range(5)]
            desc = next((l.split(":", 1)[1].strip() for l in head
                         if l.startswith("# milo-tool:")), "")
            if desc:
                shell.append((name, _first_sentence(desc)))
    except Exception:
        pass
    tools = []
    if builtin:
        tools += [(f"BUILT-IN  \u00b7  {len(builtin)}", None)] + builtin
    if shell:
        tools += [(f"MILO-TOOLS  \u00b7  {len(shell)}  \u00b7  run any with --help", None)] + shell

    return [("KEYS", keys), ("VOICE", voice), ("TOOLS", tools)], brain


def _wrap(font, text, width):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if font.size(trial)[0] <= width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


class ReferencePlaque:
    """Brass plaque that drops down from under the nameplate."""
    RECT = pygame.Rect(56, 126, 696, 500)   # ends above the input tray
    TRIGGER = pygame.Rect(316, 66, 176, 56)  # the M.I.L.O. nameplate

    def __init__(self):
        self.f_head = pygame.font.SysFont("serif", 15, bold=True)
        self.f_tab = pygame.font.SysFont("serif", 12, bold=True)
        self.f_name = pygame.font.SysFont("monospace", 12, bold=True)
        self.f_desc = pygame.font.SysFont("sans", 12)
        self.f_hint = pygame.font.SysFont("monospace", 10, bold=True)
        self.open = False
        self.drop = 0.0          # 0 = retracted, 1 = fully down
        self.section = 0
        self.scroll = 0
        self.sections, self.brain = [], "local"
        self.tab_rects = []
        self.body_h = 0
        self.view_h = 0

    def toggle(self):
        self.open = not self.open
        if self.open:
            self.sections, self.brain = load_reference()
            self.scroll = 0

    def next_section(self, step=1):
        self.section = (self.section + step) % max(1, len(self.sections))
        self.scroll = 0

    def scroll_by(self, dy):
        self.scroll = max(0, min(max(0, self.body_h - self.view_h), self.scroll + dy))

    def click(self, pos):
        """Returns True if the click was consumed."""
        if self.TRIGGER.collidepoint(pos):
            self.toggle()
            return True
        if not self.open:
            return False
        for i, r in enumerate(self.tab_rects):
            if r.collidepoint(pos):
                self.section, self.scroll = i, 0
                return True
        return self.RECT.collidepoint(pos)

    def draw(self, surface):
        target = 1.0 if self.open else 0.0
        self.drop += (target - self.drop) * 0.25
        if abs(self.drop - target) < 0.01:
            self.drop = target
        if self.drop <= 0.0:
            return

        R = self.RECT
        shown = int(R.height * (1 - (1 - self.drop) ** 2))
        plate = pygame.Surface(R.size, pygame.SRCALPHA)
        pygame.draw.rect(plate, (14, 10, 7, 255), plate.get_rect(), border_radius=8)
        pygame.draw.rect(plate, BRASS, plate.get_rect(), width=2, border_radius=8)
        pygame.draw.rect(plate, BRASS_DARK, plate.get_rect().inflate(-8, -8), width=1, border_radius=6)
        for ix, iy in ((9, 9), (R.width - 10, 9), (9, R.height - 10), (R.width - 10, R.height - 10)):
            pygame.draw.circle(plate, BRASS_DARK, (ix, iy), 4)
            pygame.draw.circle(plate, BRASS, (ix - 1, iy - 1), 2)

        head = self.f_head.render("REFERENCE PLAQUE", True, BRASS_LIGHT)
        plate.blit(head, (22, 14))
        brain = self.f_hint.render(f"BRAIN: {self.brain.upper()}", True, AMBER_GLOW)
        plate.blit(brain, (R.width - 22 - brain.get_width(), 18))

        # Section tabs
        self.tab_rects = []
        tx = 22
        for i, (name, rows) in enumerate(self.sections):
            count = sum(1 for _, d in rows if d is not None)
            label = self.f_tab.render(f"{name}  {count}", True,
                                      BLACK if i == self.section else BRASS_LIGHT)
            tr = pygame.Rect(tx, 40, label.get_width() + 22, 22)
            if i == self.section:
                pygame.draw.rect(plate, BRASS, tr, border_radius=4)
            else:
                pygame.draw.rect(plate, BRASS_DARK, tr, width=1, border_radius=4)
            plate.blit(label, (tr.x + 11, tr.y + 4))
            self.tab_rects.append(tr.move(R.x, R.y))
            tx = tr.right + 8
        pygame.draw.line(plate, BRASS_DARK, (18, 68), (R.width - 18, 68))

        # Scrollable rows
        body = pygame.Rect(22, 76, R.width - 44, R.height - 104)
        self.view_h = body.height
        rows = self.sections[self.section][1] if self.sections else []
        name_w = min(300, max([self.f_name.size(n)[0] for n, d in rows if d is not None] or [0]) + 16)
        desc_w = body.width - name_w
        clip = plate.get_clip()
        plate.set_clip(body)
        y = body.y - self.scroll
        stripe = 0
        for name, desc in rows:
            if desc is None:
                y += 4 if y > body.y - self.scroll else 0
                plate.blit(self.f_tab.render(name, True, BRASS_LIGHT), (body.x, y + 2))
                pygame.draw.line(plate, BRASS_DARK, (body.x, y + 19), (body.right, y + 19))
                y += 24
                stripe = 0
                continue
            lines = _wrap(self.f_desc, desc, desc_w)
            if len(lines) > 2:
                lines = lines[:2]
                lines[1] = lines[1].rstrip(".,;: ") + "\u2026"
            row_h = 6 + 16 * max(1, len(lines))
            stripe += 1
            if stripe % 2 == 1:
                pygame.draw.rect(plate, (30, 22, 14, 255),
                                 (body.x - 4, y - 2, body.width + 8, row_h), border_radius=3)
            plate.blit(self.f_name.render(name, True, NIXIE_GLOW), (body.x, y + 1))
            for j, line in enumerate(lines):
                plate.blit(self.f_desc.render(line, True, TEXT_COLOR),
                           (body.x + name_w, y + 1 + 16 * j))
            y += row_h
        self.body_h = y + self.scroll - body.y
        plate.set_clip(clip)

        if self.body_h > self.view_h:
            track = pygame.Rect(R.width - 14, body.y, 4, body.height)
            pygame.draw.rect(plate, (40, 30, 20), track, border_radius=2)
            th = max(20, int(track.height * self.view_h / self.body_h))
            ty = track.y + int((track.height - th) * self.scroll / (self.body_h - self.view_h))
            pygame.draw.rect(plate, BRASS, (track.x, ty, 4, th), border_radius=2)

        hint = self.f_hint.render(
            "[Tab] Section  [↑↓/Wheel] Scroll  [F1/Esc] Close  ·  Phrases work spoken or typed",
            True, MUTED_BRASS)
        plate.blit(hint, ((R.width - hint.get_width()) // 2, R.height - 22))

        surface.blit(plate, (R.x, R.y),
                     pygame.Rect(0, R.height - shown, R.width, shown))


# -----------------------------------------------------------------------------
# Main Visualizer Loop
# -----------------------------------------------------------------------------

def main():
    # Enable smooth hardware bilinear scaling for high-DPI / 4K displays
    os.environ["SDL_RENDER_SCALE_QUALITY"] = "1"
    pygame.init()
    pygame.font.init()
    try:
        pygame.scrap.init()
    except Exception:
        pass

    # Determine default scale factor based on screen height (e.g. 4K 3840x2160)
    display_info = pygame.display.Info()
    env_scale = os.environ.get("MILO_SCALE")
    if env_scale:
        try:
            scale_factor = float(env_scale)
        except ValueError:
            scale_factor = 1.85 if display_info.current_h >= 2000 else 1.0
    else:
        # 4K screens (>=2000px): default 1.85x (~1495x1450)
        # 1440p screens (>=1400px): default 1.4x (~1131x1097)
        # 1080p screens: default 1.0x (808x784)
        if display_info.current_h >= 2000:
            scale_factor = 1.85
        elif display_info.current_h >= 1400:
            scale_factor = 1.4
        else:
            scale_factor = 1.0
    default_scale = scale_factor

    win_w = int(WIDTH * scale_factor)
    win_h = int(HEIGHT * scale_factor)
    screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
    canvas = pygame.Surface((WIDTH, HEIGHT))

    # Load ornate box background
    box_bg_path = os.path.join(BASE_DIR, 'box_background.png')
    if os.path.exists(box_bg_path):
        box_bg = pygame.image.load(box_bg_path).convert()
        box_bg = pygame.transform.smoothscale(box_bg, (WIDTH, HEIGHT))
    else:
        box_bg = pygame.Surface((WIDTH, HEIGHT))
        box_bg.fill(BLACK)

    pygame.display.set_caption("MILO — Steampunk Telemetry & Voice Console")
    clock = pygame.time.Clock()

    # Load Background (Dark Walnut)
    # Load Background (Dark Walnut)
    bg_path = os.path.join(NIXIE_DIR, "dkwalnut.jpg")
    if not os.path.exists(bg_path):
        bg_path = os.path.join(BASE_DIR, "nixie_images", "drawable-hdpi", "dkwalnut.jpg")
    if not os.path.exists(bg_path):
        bg_path = "/home/pcarff/Downloads/nixie_images/drawable-hdpi/dkwalnut.jpg"
    bg_texture = None
    if os.path.exists(bg_path):
        bg_texture = pygame.image.load(bg_path).convert()
        bg_texture = pygame.transform.scale(bg_texture, (WIDTH, HEIGHT))

    # Load Title Plate (MILO Flight Director Brass Plate)
    title_plate_path = os.path.join(BASE_DIR, "milo_plate.png")
    title_plate = None
    if os.path.exists(title_plate_path):
        raw_plate = pygame.image.load(title_plate_path).convert_alpha()
        target_w = 300
        ratio = target_w / raw_plate.get_width()
        target_h = int(raw_plate.get_height() * ratio)
        title_plate = pygame.transform.smoothscale(raw_plate, (target_w, target_h))

    # Load Transparent Lamp Graphics (Hex Jewel Fixture - mounted beside input tray)
    lamp_w, lamp_h = 46, 44
    lamp_on_path = os.path.join(BASE_DIR, "lamp_on_trans.png")
    if not os.path.exists(lamp_on_path):
        lamp_on_path = "/home/pcarff/Downloads/lamp_on_trans.png"
    lamp_off_path = os.path.join(BASE_DIR, "lamp_off_trans.png")
    if not os.path.exists(lamp_off_path):
        lamp_off_path = "/home/pcarff/Downloads/lamp_off_trans.png"

    lamp_on_img = None
    lamp_off_img = None
    if os.path.exists(lamp_on_path):
        raw_on = pygame.image.load(lamp_on_path).convert_alpha()
        lamp_on_img = pygame.transform.smoothscale(raw_on, (lamp_w, lamp_h))
    if os.path.exists(lamp_off_path):
        raw_off = pygame.image.load(lamp_off_path).convert_alpha()
        lamp_off_img = pygame.transform.smoothscale(raw_off, (lamp_w, lamp_h))

    # Layout Coordinates for Option B Handcrafted Cabinet:
    # 1. Operational Steampunk Clock (Fitted inside circular porthole bezel: 234px diameter)
    clock_cx = 404
    clock_cy = 432
    clock_widget = SteampunkClock(cx=clock_cx, cy=clock_cy, size=234)

    # 2. Dual Analog Telemetry Meters flanking the clock
    meter_left = AnalogMeter(cx=204, cy=432, size=140)
    meter_right = AnalogMeter(cx=604, cy=432, size=140)

    # 3. Voice Indicator Lamp (mounted beside input tray)
    lamp_x = 695
    lamp_y = 638
    lamp_center_x = lamp_x + lamp_w // 2
    lamp_center_y = lamp_y + lamp_h // 2

    # 4. Realistic Nixie Tube Bank (Upper bay centered tubes)
    nixie_bank = NixieBank(x=85, y=115, width=640, height=110)
    tubes = nixie_bank.tubes
    nixie_start_x = 404 - (7 * 68 + 44) // 2
    nixie_y = 164

    # Fonts
    font_plate = pygame.font.SysFont("serif", 16, bold=True)
    font_sub = pygame.font.SysFont("serif", 10, bold=True)
    font_title = pygame.font.SysFont("monospace", 26, bold=True)
    font_input = pygame.font.SysFont("monospace", 15)
    font_small = pygame.font.SysFont("monospace", 12)

    # 5. Token status plates in the side bays (above/below each meter)
    plate_fonts = (pygame.font.SysFont("serif", 11, bold=True),
                   pygame.font.SysFont("monospace", 18, bold=True),
                   pygame.font.SysFont("monospace", 10, bold=True))
    token_plates = [
        TokenPlate(152, 294, "claude", plate_fonts),
        TokenPlate(152, 508, "gemini", plate_fonts),
        TokenPlate(658, 294, "agy", plate_fonts),
        TokenPlate(658, 508, "milo", plate_fonts),
    ]
    token_poller = TokenPoller()
    plaque = ReferencePlaque()
    # Window -> canvas mapping (offset x/y, scale x/y), updated every frame.
    view = (0, 0, 1.0, 1.0)

    def to_canvas(pos):
        ox, oy, sx, sy = view
        return (int((pos[0] - ox) / sx), int((pos[1] - oy) / sy))

    # Pre-render Nameplate
    t_surf_sh = font_plate.render("M.I.L.O.", True, (180, 150, 80))
    t_surf = font_plate.render("M.I.L.O.", True, (40, 26, 12))
    s_surf_sh = font_sub.render("FLIGHT DIRECTOR", True, (180, 150, 80))
    s_surf = font_sub.render("FLIGHT DIRECTOR", True, (50, 32, 16))

    # State Variables
    input_text = ""
    last_sent_text = ""
    pulse_phase = 0.0
    cursor_timer = 0
    running = True

    while running:
        cursor_timer = (cursor_timer + 1) % 60
        cursor_visible = cursor_timer < 30

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEWHEEL:
                if plaque.open:
                    plaque.scroll_by(-event.y * 32)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    plaque.click(to_canvas(event.pos))
                elif event.button == 3:  # Right-click pastes clipboard text into input box
                    clip = get_clipboard_text()
                    if clip:
                        clean = " ".join(clip.split())
                        if clean:
                            remaining = 1000 - len(input_text)
                            if remaining > 0:
                                input_text += clean[:remaining]
            elif event.type == pygame.KEYDOWN:
                ctrl_pressed = bool(event.mod & pygame.KMOD_CTRL)
                shift_pressed = bool(event.mod & pygame.KMOD_SHIFT)

                # Reference plaque: F1 toggles; while open it owns
                # Tab/arrows/paging/Esc, everything else still types.
                if event.key == pygame.K_F1:
                    plaque.toggle()
                elif plaque.open and event.key == pygame.K_ESCAPE:
                    plaque.toggle()
                elif plaque.open and event.key in (pygame.K_TAB, pygame.K_RIGHT):
                    plaque.next_section(-1 if (shift_pressed and event.key == pygame.K_TAB) else 1)
                elif plaque.open and event.key == pygame.K_LEFT:
                    plaque.next_section(-1)
                elif plaque.open and event.key in (pygame.K_UP, pygame.K_DOWN):
                    plaque.scroll_by(-32 if event.key == pygame.K_UP else 32)
                elif plaque.open and event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                    plaque.scroll_by(-300 if event.key == pygame.K_PAGEUP else 300)
                # Paste from clipboard (Ctrl+V or Shift+Insert)
                elif (ctrl_pressed and event.key == pygame.K_v) or (shift_pressed and event.key == pygame.K_INSERT):
                    clip = get_clipboard_text()
                    if clip:
                        clean = " ".join(clip.split())
                        if clean:
                            remaining = 1000 - len(input_text)
                            if remaining > 0:
                                input_text += clean[:remaining]
                # Copy current input text to clipboard (Ctrl+C)
                elif ctrl_pressed and event.key == pygame.K_c:
                    if input_text:
                        set_clipboard_text(input_text)
                # Clear entire input line (Ctrl+U)
                elif ctrl_pressed and event.key == pygame.K_u:
                    input_text = ""
                # Delete previous word (Ctrl+Backspace or Ctrl+W)
                elif ctrl_pressed and event.key in (pygame.K_BACKSPACE, pygame.K_w):
                    parts = input_text.rstrip().rsplit(" ", 1)
                    input_text = parts[0] if len(parts) > 1 else ""
                elif event.key == pygame.K_ESCAPE:
                    running = False
                elif ctrl_pressed and event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    scale_factor = round(min(3.0, scale_factor + 0.1), 2)
                    new_w = int(WIDTH * scale_factor)
                    new_h = int(HEIGHT * scale_factor)
                    screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
                elif ctrl_pressed and event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                    scale_factor = round(max(0.6, scale_factor - 0.1), 2)
                    new_w = int(WIDTH * scale_factor)
                    new_h = int(HEIGHT * scale_factor)
                    screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
                elif ctrl_pressed and event.key in (pygame.K_0, pygame.K_KP_0):
                    scale_factor = default_scale
                    new_w = int(WIDTH * scale_factor)
                    new_h = int(HEIGHT * scale_factor)
                    screen = pygame.display.set_mode((new_w, new_h), pygame.RESIZABLE)
                elif event.key == pygame.K_RETURN:
                    msg = input_text.strip()
                    if msg:
                        send_typed_message(msg)
                        last_sent_text = msg
                        input_text = ""
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    if not ctrl_pressed and len(input_text) < 1000 and event.unicode and event.unicode.isprintable():
                        input_text += event.unicode

        # Query real-time voice state from backtalk signal bus
        voice_state = get_voice_state()
        is_user_talking = (voice_state == "listening")
        is_working = (voice_state == "thinking")
        is_thinking = (voice_state == "thinking")
        is_speaking = (voice_state == "speaking")

        # ---------------------------------------------------------------------
        # Nixie Tube Behavior:
        # - When MILO is working (thinking): numbers flicker rapidly
        # - In all other states (idle, listening, or MILO speaking): numbers stay FROZEN
        # ---------------------------------------------------------------------
        if is_working:
            for tube in tubes:
                if random.random() < 0.28:  # Rapid telemetry calculation flicker
                    tube.value = str(random.randint(0, 9))
        # When waiting for user or when MILO is speaking: DO NOTHING -> NUMBERS STAY FROZEN

        pulse_phase += 0.08
        glow_pulse = (math.sin(pulse_phase) + 1.0) * 0.5

        # --- Draw Background Cabinet onto Virtual Canvas ---
        canvas.blit(box_bg, (0, 0))

        # --- Draw Engraved Nameplate Text ---
        canvas.blit(t_surf_sh, (404 - t_surf.get_width() // 2 + 1, 75 + 1))
        canvas.blit(t_surf, (404 - t_surf.get_width() // 2, 75))
        canvas.blit(s_surf_sh, (404 - s_surf.get_width() // 2 + 1, 95 + 1))
        canvas.blit(s_surf, (404 - s_surf.get_width() // 2, 95))

        # --- Draw Realistic Nixie Tubes (Centered in Upper Bay at Y=164) ---
        for i, tube in enumerate(tubes):
            tx = nixie_start_x + i * 68
            ty = nixie_y
            d_idx = int(tube.value) if tube.value.isdigit() else 0
            d_surf = nixie_bank.digit_surfaces.get(d_idx)
            if d_surf:
                canvas.blit(d_surf, (tx, ty))

        # --- Update & Draw Dual Analog Telemetry Meters ---
        meter_left.update(is_working, is_speaking)
        meter_right.update(is_working, is_speaking)
        meter_left.draw(canvas)
        meter_right.draw(canvas)

        # --- Token Status Plates ---
        plate_rows = token_plate_rows(token_poller.status)
        for plate in token_plates:
            plate.draw(canvas, plate_rows.get(plate.agent))

        # --- Draw Centered Steampunk Clock (Porthole Bezel: 234px) ---
        clock_widget.draw(canvas)

        # --- Reference Plaque (drops over the upper bays, above the tray) ---
        plaque.draw(canvas)

        # ---------------------------------------------------------------------
        # Steampunk Text Input Box (Recessed Lower Tray)
        # ---------------------------------------------------------------------
        input_box_rect = pygame.Rect(130, 638, 548, 44)

        # Outer Brass Frame
        pygame.draw.rect(canvas, (15, 12, 10), input_box_rect, border_radius=6)
        border_color = BRASS_LIGHT if (pygame.time.get_ticks() % 1200 < 600 and len(input_text) > 0) else BRASS
        pygame.draw.rect(canvas, border_color, input_box_rect, width=2, border_radius=6)

        # Corner Rivets for Input Frame
        for ix, iy in [
            (input_box_rect.left + 5, input_box_rect.top + 5),
            (input_box_rect.right - 5, input_box_rect.top + 5),
            (input_box_rect.left + 5, input_box_rect.bottom - 5),
            (input_box_rect.right - 5, input_box_rect.bottom - 5),
        ]:
            pygame.draw.circle(canvas, BRASS_DARK, (ix, iy), 2)

        # Prompt symbol
        prompt_surf = font_input.render("▶", True, BRASS_LIGHT)
        canvas.blit(prompt_surf, (input_box_rect.left + 12, input_box_rect.top + 12))

        # Render Input Text or Placeholder
        text_x = input_box_rect.left + 32
        text_y = input_box_rect.top + 13
        if input_text:
            rendered_input = font_input.render(input_text, True, TEXT_COLOR)
            # Clip if too long for box
            max_w = input_box_rect.width - 45
            if rendered_input.get_width() > max_w:
                sub_surf = rendered_input.subsurface((rendered_input.get_width() - max_w, 0, max_w, rendered_input.get_height()))
                canvas.blit(sub_surf, (text_x, text_y))
                cursor_x = text_x + max_w + 2
            else:
                canvas.blit(rendered_input, (text_x, text_y))
                cursor_x = text_x + rendered_input.get_width() + 2

            if cursor_visible:
                pygame.draw.line(canvas, BRASS_LIGHT, (cursor_x, text_y + 1), (cursor_x, text_y + 17), 2)
        else:
            placeholder = font_input.render("Type a message to MILO and press Enter...", True, MUTED_BRASS)
            canvas.blit(placeholder, (text_x, text_y))
            if cursor_visible:
                pygame.draw.line(canvas, BRASS_LIGHT, (text_x, text_y + 1), (text_x, text_y + 17), 2)

        # --- Draw Voice Indicator Lamp (Beside Lower Tray) ---
        if is_user_talking:
            glow_radius = int(26 + glow_pulse * 6)
            glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            alpha = int(55 + glow_pulse * 40)
            glow_color = (255, 170, 30, alpha)
            pygame.draw.circle(glow_surf, glow_color, (glow_radius, glow_radius), glow_radius)
            canvas.blit(glow_surf, (lamp_center_x - glow_radius, lamp_center_y - glow_radius))

        if is_user_talking and lamp_on_img:
            canvas.blit(lamp_on_img, (lamp_x, lamp_y))
        elif lamp_off_img:
            canvas.blit(lamp_off_img, (lamp_x, lamp_y))

        # --- Footer Line (Recent Message or Shortcut Hints) ---
        footer_y = 748
        if last_sent_text:
            display_msg = last_sent_text if len(last_sent_text) <= 38 else last_sent_text[:35] + "..."
            last_surf = font_small.render(f"Sent: \"{display_msg}\" | [Right-Alt] Talk | [F1] Reference | [Esc] Exit", True, (160, 130, 85))
            canvas.blit(last_surf, ((WIDTH - last_surf.get_width()) // 2, footer_y))
        else:
            hint = font_small.render("[Enter] Send | [Ctrl+V] Paste | [Right-Alt] Talk | [F1] Reference | [Ctrl +/-] Zoom | [Esc] Exit", True, (140, 115, 80))
            canvas.blit(hint, ((WIDTH - hint.get_width()) // 2, footer_y))

        # --- Smoothscale Virtual Canvas to Fill Window Completely ---
        cur_w, cur_h = screen.get_size()
        if cur_w == WIDTH and cur_h == HEIGHT:
            view = (0, 0, 1.0, 1.0)
            screen.blit(canvas, (0, 0))
        else:
            aspect_diff = abs((cur_w / cur_h) - (WIDTH / HEIGHT))
            if aspect_diff < 0.05:
                # Aspect ratio is close to native -> stretch to 100% fill window with zero black bars
                view = (0, 0, cur_w / WIDTH, cur_h / HEIGHT)
                scaled = pygame.transform.smoothscale(canvas, (cur_w, cur_h))
                screen.blit(scaled, (0, 0))
            else:
                # Window was dragged to non-standard aspect ratio -> letterbox cleanly
                fit_scale = min(cur_w / WIDTH, cur_h / HEIGHT)
                sw = int(WIDTH * fit_scale)
                sh = int(HEIGHT * fit_scale)
                scaled = pygame.transform.smoothscale(canvas, (sw, sh))
                view = ((cur_w - sw) // 2, (cur_h - sh) // 2, fit_scale, fit_scale)
                screen.fill(BLACK)
                screen.blit(scaled, ((cur_w - sw) // 2, (cur_h - sh) // 2))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
