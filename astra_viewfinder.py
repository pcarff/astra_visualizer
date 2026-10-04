#!/usr/bin/env python3
"""
ASTRA Steampunk Optical Viewfinder HUD (Qt6 / PyQt6)
Autonomous Systems & Telemetry Robotics Assistant — Real-Time Visual Telemetry & Camera Reticle.

Displays live/captured frames from the Logitech C925e optical sensor with
Victorian brass housing, corner rivets, amber telemetry crosshairs, and one-click capture.
"""

import sys
import os
import json
import glob
import subprocess
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QPixmap, QImage,
    QRadialGradient, QLinearGradient, QBrush, QAction
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame
)

# Import shared theme if available
THEME_DIR = "/home/pcarff/Workspaces/SteampunkQt6Demo"
if THEME_DIR not in sys.path:
    sys.path.insert(0, THEME_DIR)

try:
    from steampunk_theme import (
        COLOR_BG_DARK, COLOR_BG_PANEL, COLOR_BORDER_BRASS,
        COLOR_BRASS, COLOR_BRASS_LIGHT, COLOR_GOLD, COLOR_COPPER,
        COLOR_NIXIE_AMBER, COLOR_NIXIE_AMBER_BRIGHT, COLOR_TEXT_PRIMARY,
        COLOR_TEXT_MUTED, get_steampunk_font
    )
except ImportError:
    COLOR_BG_DARK = "#0f0c0a"
    COLOR_BG_PANEL = "#1a1410"
    COLOR_BORDER_BRASS = "#8a6625"
    COLOR_BRASS = "#b58900"
    COLOR_BRASS_LIGHT = "#e0a800"
    COLOR_GOLD = "#d4af37"
    COLOR_COPPER = "#b87333"
    COLOR_NIXIE_AMBER = "#ff8c00"
    COLOR_NIXIE_AMBER_BRIGHT = "#ffa726"
    COLOR_TEXT_PRIMARY = "#fff0be"
    COLOR_TEXT_MUTED = "#997b54"

    def get_steampunk_font(size=11, bold=False, family="mono"):
        font = QFont("Courier 10 Pitch", size)
        font.setBold(bold)
        return font

SIGNALS_DIR = "/dev/shm/signals"
PIC_DIR = "/workspaces_nvme/astra_pic"


class ViewfinderWidget(QWidget):
    """Steampunk optical viewfinder with brass bezel, rivets, and targeting reticle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap: QPixmap | None = None
        self.status_text = "OPTICAL SENSOR: STANDBY"
        self.reticle_visible = True
        self.setMinimumSize(640, 380)

    def set_image(self, img_path: str, status: str = ""):
        if os.path.exists(img_path):
            self.pixmap = QPixmap(img_path)
            if status:
                self.status_text = status
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bezel_margin = 12

        # 1. Outer Dark Walnut / Cast Iron Housing
        painter.fillRect(0, 0, w, h, QColor(COLOR_BG_DARK))

        # 2. Weathered Brass Bezel Frame
        bezel_rect = QRectF(bezel_margin, bezel_margin, w - 2 * bezel_margin, h - 2 * bezel_margin)
        pen_brass = QPen(QColor(COLOR_BORDER_BRASS), 3)
        painter.setPen(pen_brass)
        painter.setBrush(QColor(16, 12, 10))
        painter.drawRoundedRect(bezel_rect, 6, 6)

        # 3. Corner Brass Rivets
        rivet_radius = 4.5
        rivet_coords = [
            (bezel_margin + 12, bezel_margin + 12),
            (w - bezel_margin - 12, bezel_margin + 12),
            (bezel_margin + 12, h - bezel_margin - 12),
            (w - bezel_margin - 12, h - bezel_margin - 12),
            (w / 2, bezel_margin + 6),
            (w / 2, h - bezel_margin - 6),
        ]
        for rx, ry in rivet_coords:
            grad = QRadialGradient(rx - 1, ry - 1, rivet_radius)
            grad.setColorAt(0.0, QColor(COLOR_BRASS_LIGHT))
            grad.setColorAt(0.6, QColor(COLOR_BRASS))
            grad.setColorAt(1.0, QColor(60, 40, 18))
            painter.setPen(QColor(40, 25, 10))
            painter.setBrush(grad)
            painter.drawEllipse(QPointF(rx, ry), rivet_radius, rivet_radius)
            # Screw slot
            painter.setPen(QPen(QColor(30, 20, 10), 1.2))
            painter.drawLine(int(rx - 2.5), int(ry), int(rx + 2.5), int(ry))

        # 4. Viewport Area (inside bezel)
        vp_pad = 14
        vp_rect = QRectF(
            bezel_margin + vp_pad,
            bezel_margin + vp_pad,
            w - 2 * (bezel_margin + vp_pad),
            h - 2 * (bezel_margin + vp_pad)
        )

        # Draw Image scaled to fit viewport
        if self.pixmap and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(
                int(vp_rect.width()), int(vp_rect.height()),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            img_x = vp_rect.x() + (vp_rect.width() - scaled.width()) / 2
            img_y = vp_rect.y() + (vp_rect.height() - scaled.height()) / 2
            painter.drawPixmap(int(img_x), int(img_y), scaled)
        else:
            # Standby viewfinder screen
            painter.fillRect(vp_rect, QColor(10, 8, 7))
            painter.setPen(QColor(COLOR_TEXT_MUTED))
            font = get_steampunk_font(12, bold=True, family="serif")
            painter.setFont(font)
            painter.drawText(vp_rect, Qt.AlignmentFlag.AlignCenter, "[ NO OPTICAL TELEMETRY // SENSOR STANDBY ]")

        # 5. Steampunk Targeting Reticle & Optical Overlay
        if self.reticle_visible:
            cx = vp_rect.center().x()
            cy = vp_rect.center().y()

            pen_reticle = QPen(QColor(255, 167, 38, 140), 1.2)  # Amber glow
            painter.setPen(pen_reticle)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            # Center concentric circles
            painter.drawEllipse(QPointF(cx, cy), 32, 32)
            painter.drawEllipse(QPointF(cx, cy), 64, 64)

            # Center crosshair hairs with gap
            painter.drawLine(int(cx - 90), int(cy), int(cx - 40), int(cy))
            painter.drawLine(int(cx + 40), int(cy), int(cx + 90), int(cy))
            painter.drawLine(int(cx), int(cy - 90), int(cx), int(cy - 40))
            painter.drawLine(int(cx), int(cy + 40), int(cx), int(cy + 90))

            # Corner alignment brackets
            bracket_len = 18
            bx1, by1 = vp_rect.left() + 8, vp_rect.top() + 8
            bx2, by2 = vp_rect.right() - 8, vp_rect.bottom() - 8

            pen_bracket = QPen(QColor(COLOR_BRASS), 2)
            painter.setPen(pen_bracket)
            # Top-left
            painter.drawLine(int(bx1), int(by1), int(bx1 + bracket_len), int(by1))
            painter.drawLine(int(bx1), int(by1), int(bx1), int(by1 + bracket_len))
            # Top-right
            painter.drawLine(int(bx2), int(by1), int(bx2 - bracket_len), int(by1))
            painter.drawLine(int(bx2), int(by1), int(bx2), int(by1 + bracket_len))
            # Bottom-left
            painter.drawLine(int(bx1), int(by2), int(bx1 + bracket_len), int(by2))
            painter.drawLine(int(bx1), int(by2), int(bx1), int(by2 - bracket_len))
            # Bottom-right
            painter.drawLine(int(bx2), int(by2), int(bx2 - bracket_len), int(by2))
            painter.drawLine(int(bx2), int(by2), int(bx2), int(by2 - bracket_len))

        # 6. Lens Vignette & Amber Glow Border
        pen_inner = QPen(QColor(COLOR_BORDER_BRASS), 1.5)
        painter.setPen(pen_inner)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(vp_rect)


class SteampunkViewfinderHUD(QMainWindow):
    """Master HUD Window for ASTRA's Optical Eye Viewfinder."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("A.S.T.R.A. — Optical Telemetry & Viewfinder")
        self.resize(780, 620)
        self.setStyleSheet(f"background-color: {COLOR_BG_DARK}; color: {COLOR_TEXT_PRIMARY};")

        self.last_snap_file = ""
        self.last_timestamp = ""

        # Central Layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Brass Title Nameplate
        title_plate = QFrame()
        title_plate.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3d2b18, stop:0.5 #261a0e, stop:1 #1a120a);
                border: 2px solid {COLOR_BORDER_BRASS};
                border-radius: 4px;
                padding: 6px;
            }}
        """)
        title_layout = QHBoxLayout(title_plate)
        title_layout.setContentsMargins(12, 4, 12, 4)

        title_label = QLabel("A.S.T.R.A. OPTICAL TELEMETRY VIEWPORT")
        title_label.setFont(get_steampunk_font(13, bold=True, family="serif"))
        title_label.setStyleSheet(f"color: {COLOR_GOLD}; letter-spacing: 1px;")

        sensor_badge = QLabel("SENSOR: LOGITECH C925e [1080p MJPEG]")
        sensor_badge.setFont(get_steampunk_font(9, bold=True, family="mono"))
        sensor_badge.setStyleSheet(f"color: {COLOR_NIXIE_AMBER}; background: #120e0a; border: 1px solid #4a3215; padding: 3px 8px; border-radius: 3px;")

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(sensor_badge)
        layout.addWidget(title_plate)

        # 2. Optical Viewfinder Display
        self.viewfinder = ViewfinderWidget()
        layout.addWidget(self.viewfinder, stretch=1)

        # 3. Telemetry Readout Console
        self.telemetry_box = QFrame()
        self.telemetry_box.setStyleSheet(f"""
            QFrame {{
                background-color: {COLOR_BG_PANEL};
                border: 1.5px solid {COLOR_BORDER_BRASS};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        tel_layout = QVBoxLayout(self.telemetry_box)
        tel_layout.setContentsMargins(10, 8, 10, 8)
        tel_layout.setSpacing(4)

        self.telemetry_line1 = QLabel("FEED STATUS: IDLE // AWAITING OPTICAL TARGET")
        self.telemetry_line1.setFont(get_steampunk_font(10, bold=True, family="mono"))
        self.telemetry_line1.setStyleSheet(f"color: {COLOR_NIXIE_AMBER_BRIGHT};")

        self.telemetry_line2 = QLabel("LAST SNAPSHOT: NONE  |  PATH: /workspaces_nvme/astra_pic")
        self.telemetry_line2.setFont(get_steampunk_font(9, bold=False, family="mono"))
        self.telemetry_line2.setStyleSheet(f"color: {COLOR_TEXT_MUTED};")

        tel_layout.addWidget(self.telemetry_line1)
        tel_layout.addWidget(self.telemetry_line2)
        layout.addWidget(self.telemetry_box)

        # 4. Action Controls Bar
        btn_bar = QHBoxLayout()
        btn_bar.setSpacing(12)

        self.snap_btn = QPushButton("📷 SNAP && INSPECT NOW")
        self.snap_btn.setFont(get_steampunk_font(11, bold=True, family="serif"))
        self.snap_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.snap_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #8a6625, stop:0.5 #5c4217, stop:1 #3d2b0e);
                color: {COLOR_TEXT_PRIMARY};
                border: 2px solid {COLOR_BRASS};
                border-radius: 4px;
                padding: 8px 18px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #b58900, stop:0.5 #8a6625, stop:1 #5c4217);
                border: 2px solid {COLOR_BRASS_LIGHT};
                color: #ffffff;
            }}
            QPushButton:pressed {{
                background-color: #2a1c0a;
                border: 2px solid {COLOR_COPPER};
            }}
        """)
        self.snap_btn.clicked.connect(self.manual_snap)

        self.open_dir_btn = QPushButton("📂 OPEN GALLERY")
        self.open_dir_btn.setFont(get_steampunk_font(10, bold=False, family="mono"))
        self.open_dir_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #211912;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER_BRASS};
                border-radius: 4px;
                padding: 8px 14px;
            }}
            QPushButton:hover {{
                background-color: #362719;
                border-color: {COLOR_BRASS};
            }}
        """)
        self.open_dir_btn.clicked.connect(self.open_gallery)

        self.reticle_btn = QPushButton("🎯 TOGGLE RETICLE")
        self.reticle_btn.setFont(get_steampunk_font(10, bold=False, family="mono"))
        self.reticle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #211912;
                color: {COLOR_TEXT_PRIMARY};
                border: 1px solid {COLOR_BORDER_BRASS};
                border-radius: 4px;
                padding: 8px 14px;
            }}
            QPushButton:hover {{
                background-color: #362719;
                border-color: {COLOR_BRASS};
            }}
        """)
        self.reticle_btn.clicked.connect(self.toggle_reticle)

        btn_bar.addWidget(self.snap_btn)
        btn_bar.addWidget(self.open_dir_btn)
        btn_bar.addWidget(self.reticle_btn)
        btn_bar.addStretch()

        layout.addLayout(btn_bar)

        # 5. Timer to poll signal bus for incoming snaps
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.check_signals)
        self.poll_timer.start(250)

        # Load initial candidate image if available
        self.load_latest_image()

    def load_latest_image(self):
        """Load the most recent snapshot from the pictures directory."""
        if os.path.exists(PIC_DIR):
            files = [os.path.join(PIC_DIR, f) for f in os.listdir(PIC_DIR)
                     if f.lower().endswith((".jpg", ".jpeg", ".png"))]
            if files:
                newest = max(files, key=os.path.getmtime)
                self.display_snapshot(newest, status="ARCHIVED TELEMETRY LOADED")

    def display_snapshot(self, img_path: str, status: str = "OPTICAL TELEMETRY ACTIVE", query: str = ""):
        self.last_snap_file = img_path
        self.viewfinder.set_image(img_path, status=status)
        fname = os.path.basename(img_path)
        sz = os.path.getsize(img_path) // 1024 if os.path.exists(img_path) else 0

        self.telemetry_line1.setText(f"FEED STATUS: {status}  |  TARGET: {fname} ({sz} KB)")
        if query:
            self.telemetry_line2.setText(f"INSPECTION QUERY: \"{query}\"")
        else:
            self.telemetry_line2.setText(f"CAPTURED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  |  LOCATION: {img_path}")

    def manual_snap(self):
        """User clicked manual snap button."""
        self.snap_btn.setEnabled(False)
        self.telemetry_line1.setText("FEED STATUS: HARDWARE EXPOSING & GRABBING MJPEG FRAME...")
        QApplication.processEvents()

        try:
            from backtalk.camera import snap_webcam_frame
            snap_file = snap_webcam_frame(output_dir=PIC_DIR, query="Manual snapshot from Steampunk Viewfinder")
            if snap_file:
                self.display_snapshot(snap_file, status="MANUAL FRAME CAPTURED", query="Manual Viewfinder Inspection")
            else:
                self.telemetry_line1.setText("FEED STATUS: ⚠️ CAPTURE FAILED — CHECK CAMERA DEVICE")
        except Exception as e:
            self.telemetry_line1.setText(f"FEED STATUS: ❌ ERROR: {e}")
        finally:
            self.snap_btn.setEnabled(True)

    def open_gallery(self):
        """Open the photos folder in system file manager."""
        if os.path.exists(PIC_DIR):
            subprocess.Popen(["xdg-open", PIC_DIR], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def toggle_reticle(self):
        self.viewfinder.reticle_visible = not self.viewfinder.reticle_visible
        self.viewfinder.update()

    def check_signals(self):
        """Check the signal bus file .camera_snap for new captures triggered by voice."""
        sig_file = os.path.join(SIGNALS_DIR, ".camera_snap")
        if os.path.exists(sig_file):
            try:
                with open(sig_file, "r") as f:
                    data = json.load(f)
                img = data.get("image_path")
                ts = data.get("timestamp")
                query = data.get("query", "")
                if img and ts != self.last_timestamp and os.path.exists(img):
                    self.last_timestamp = ts
                    self.display_snapshot(img, status="INCOMING VOICE TELEMETRY", query=query)
                    self.show()
                    self.raise_()
            except Exception:
                pass


def main():
    app = QApplication(sys.argv)
    hud = SteampunkViewfinderHUD()
    hud.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
