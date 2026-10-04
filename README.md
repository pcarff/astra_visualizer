# A.S.T.R.A. Steampunk Telemetry & Voice Console

A Victorian industrial / Steampunk operational console for **A.S.T.R.A.** (**A**utonomous **S**ystems & **T**elemetry **R**obotics **A**ssistant), featuring an authentic 8-digit Nixie vacuum tube telemetry bank, a live 2× Steampunk Chronometer, an interactive command terminal, and a corner push-to-talk voice indicator lamp.

---

## Visual Architecture & Console Layout ($800 \times 660\text{px}$)

```
+-------------------------------------------------------------+
|               [ A.S.T.R.A. + full name ]                     |  <- Y: 16..75
|  +-------------------------------------------------------+  |
|  | [0]  [3]  [8]  [5]  [8]  [7]  [3]  [1]                |  |  <- Y: 88..208
|  |     (Rustic Weathered Brass/Cast Iron Backplate)      |  |
|  +-------------------------------------------------------+  |
|                                                             |
|                         (   12   )                          |
|                       ( 9   •    3 )                        |  <- Y: 235..543
|                         (   6    )                          |  (308px Chronometer)
|                                                             |
|  +--------------------------------------------+    +-----+  |
|  | ▶ Type a message to ASTRA and press Enter...|    | (*) |  |  <- Y: 570..612
|  +--------------------------------------------+    +-----+  |
|          [Enter] Send | [Right-Alt] PTT | [Esc] Exit        |  <- Y: 628
+-------------------------------------------------------------+
```

---

## Core Components

### 1. Slender Nixie Tube Bank (`NixieBank` & `NixieTube`)
- **Dimensions**: $660 \times 120\text{px}$, centered horizontally at $X = 70, Y = 88$.
- **Authentic Aspect Ratio**: Digits are sized to **$42 \times 76\text{px}$** (aspect ratio $0.553$), eliminating squatness and replicating authentic IN-14 / ZM1020 vertical vacuum tube envelopes.
- **Optics & Atmosphere**:
  - Warm radial ambient glow (`#ff8c00`) projected behind the illuminated filament mesh.
  - Fine vertical specular reflection glint along the left curved glass wall.
- **Rustic Industrial Backplate** ([`nixie_backplate.png`](file:///anzym/my-agent/astra_visualizer/nixie_backplate.png)):
  - Outer cast-iron tubular molding secured with 14 polished brass dome rivets.
  - Weathered copper and smoked bronze patina surface.
  - 8 precision-milled brass socket bezels ($54 \times 92\text{px}$) with corner set-screws and deep recessed dark chambers ($44 \times 80\text{px}$).
- **Dynamic Telemetry Behavior**:
  - **Thinking / Working**: Tubes flicker rapidly with random telemetry calculations.
  - **Idle / Listening / Speaking**: Numbers remain frozen in place.

### 2. Operational Steampunk Chronometer (`SteampunkClock`)
- **Dimensions**: $308\text{px}$ diameter (2× scale), centered at $X = 400, Y = 389$.
- **Dial Face** ([`clock_dial_base_trans.png`](file:///anzym/my-agent/astra_visualizer/clock_dial_base_trans.png)):
  - Authentic Victorian brass bezel with rivet lugs, dark chocolate dial plate, and gold Arabic numerals (1–12).
  - Subpixel signed-distance anti-aliased transparency with zero grey fringing.
- **Live Mechanical Movement**:
  - **Hour Hand**: Tapered lancet pointer with luminous amber core and drop shadow.
  - **Minute Hand**: Slender lancet pointer with amber core.
  - **Second Hand**: Vermillion red needle with counterbalanced brass tail, sweeping smoothly to microsecond precision.
  - **Center Hub**: Multi-tier polished brass cap with specular highlight.

### 3. Equipment Placard (`astra_plate.png`)
- High-detail brass placard engraved *"A.S.T.R.A."* over *"Autonomous Systems & Telemetry Robotics Assistant"*.
- Scaled to $300 \times 59\text{px}$ and centered at $Y = 16$.

### 4. Corner Voice Indicator Jewel Lamp
- Scaled to 1/3 size ($56 \times 54\text{px}$) mounted at $X = 718, Y = 564$.
- Hexagonal brass socket housing an authentic faceted amber jewel lens:
  - **Off** ([`lamp_off_trans.png`](file:///anzym/my-agent/astra_visualizer/lamp_off_trans.png)): Dark translucent amber jewel.
  - **On** ([`lamp_on_trans.png`](file:///anzym/my-agent/astra_visualizer/lamp_on_trans.png)): Luminous glowing lens with pulsing radial ambient halo while transmitting.

### 5. Interactive Command Console
- Steampunk bordered input field with brass rivets and gold prompt marker (`▶`).
- Dispatches typed messages directly to ASTRA's voice engine queue via `/dev/shm/signals/.typed_input` or `/tmp/signals/.typed_input`.

---

## Signal Bus Integration (`backtalk`)

The console communicates via POSIX shared memory files:
- **`.voice_state`**: Read-only telemetry indicating state (`idle`, `listening`, `thinking`, `speaking`).
- **`.typed_input`**: Write queue allowing typed instructions to bypass microphone speech recognition.

---

## Running the Visualizer

```bash
# Launch directly via script
/anzym/my-agent/astra_visualizer/run.sh

# Or run in Python virtual environment
cd /anzym/my-agent/astra_visualizer
./venv/bin/python astra_nixie.py
```

### Controls
- **Text Input**: Type message and press `[Enter]` to dispatch to ASTRA.
- **`[Right-Alt]`**: Push-To-Talk voice trigger (the key comes from backtalk's `ptt_key`).
- **`[Ctrl+V]` / `[Shift+Insert]` / right-click**: Paste. **`[Ctrl+C]`** copy line, **`[Ctrl+U]`** clear line, **`[Ctrl+W]` / `[Ctrl+Backspace]`** delete word.
- **`[Ctrl +/-]`, `[Ctrl+0]`**: Zoom / reset zoom.
- **`[F1]`** or click the **A.S.T.R.A. nameplate**: Reference plaque (below).
- **`[Esc]`**: Close the plaque if open, otherwise exit the console.

### Reference Plaque (`ReferencePlaque`)
A brass plaque that drops down from under the nameplate over the Nixie and
meter bays, stopping above the input tray so typing still works. Three
sections, switched with `[Tab]` / `[←][→]` or by clicking the tabs; scroll
with `[↑][↓]`, `[PgUp][PgDn]` or the mouse wheel:

- **KEYS**: every console key binding above, plus "Ctrl+C in the terminal hangs up".
- **VOICE**: the voice-console phrases (spoken *or* typed), e.g. "switch brain to <name>", "go hands free", "set effort to <level>", "goodbye astra".
- **TOOLS**: built-in tools and ASTRA-tools, grouped under sub-headings.

The content is rebuilt on every open from the live sources, so it never needs
hand-editing: `backtalk.json` (PTT key, mic mode, active brain shown top-right),
`CONSOLE_VERBS` in `backtalk/backtalk/main.py` (read with `ast`, not imported),
the `- name(args): desc` tool list in `backtalk/backtalk/brain.py`, and each
`astra-tools/` executable with a `# astra-tool:` line in its first 5 lines (the
same rule backtalk uses). Short explanations for voice verbs live in
`VOICE_HELP` in `astra_nixie.py`; add one there when adding a verb.

---

## 6. Steampunk Optical Viewfinder HUD (`astra_viewfinder.py`)

A dedicated high-resolution visual HUD window for ASTRA's optical eyes:
- **Framework**: PyQt6 adhering to the Victorian Steampunk design system (dark walnut housing, weathered brass border, dome screw rivets).
- **Optics Display**: High-resolution 1080p frame viewport with an amber targeting reticle (concentric rings, crosshairs, and corner alignment brackets).
- **Telemetry Console**: Real-time readouts indicating optical sensor model (Logitech C925e / UVC), resolution, target filename, file size, and query context.
- **Live Signal Bus Sync**: Watches `/dev/shm/signals/.camera_snap`. When ASTRA snaps a photo during voice conversation, the Viewfinder instantly pops to the front and presents the image.
- **Interactive Controls**:
  - `[ 📷 SNAP & INSPECT NOW ]`: Manually trigger a fresh hardware frame capture and diagnosis.
  - `[ 📂 OPEN GALLERY ]`: Opens `/workspaces_nvme/astra_pic` in the file manager.
  - `[ 🎯 TOGGLE RETICLE ]`: Show or hide targeting reticle overlays.

### Running the Viewfinder HUD

```bash
# Launch standalone Viewfinder HUD
python3 /anzym/my-agent/astra_visualizer/astra_viewfinder.py
```

