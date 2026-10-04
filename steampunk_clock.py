"""
Steampunk Chronometer Clock Widget for Qt6
Authentic brass & copper analog clock responding in real-time to system clock.
Derived from FLUX.1 generation concept with corrected Arabic numerals and luminous hands.
"""

import os
import math
from datetime import datetime

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPixmap,
    QPolygonF, QRadialGradient, QLinearGradient, QPainterPath
)
from PyQt6.QtCore import Qt, QPointF, QTime, QTimer


class SteampunkClock(QWidget):
    """
    Authentic Steampunk Clock / Chronometer Widget for Qt6.
    Features:
    - High-resolution dial face with Arabic numerals 1-12.
    - Weathered brass bezel with corner bolts and cardinal rivets.
    - Luminous amber/orange hour and minute hands responding to system time.
    - Fine copper sweep second hand with counterbalance.
    - Polished brass multi-tiered center cap with specular reflection.
    """

    def __init__(self, size: int = 300, smooth: bool = True, show_seconds: bool = True, parent=None):
        super().__init__(parent)
        self.clock_size = size
        self.smooth = smooth
        self.show_seconds = show_seconds
        self.setFixedSize(size, size)

        # Asset discovery paths
        asset_paths = [
            os.path.expanduser("~/.local/share/steampunk_assets/textures/clock_dial_base_trans.png"),
            "/home/pcarff/Pictures/Flux_Generations/clock_dial_base_trans.png",
            "/home/pcarff/Pictures/Flux_Generations/clock_dial_base.png",
            os.path.join(os.path.dirname(__file__), "textures", "clock_dial_base_trans.png"),
        ]
        
        self.base_pixmap = None
        for p in asset_paths:
            if os.path.exists(p):
                self.base_pixmap = QPixmap(p)
                break

        # Internal animation timer (33ms = 30fps for smooth sweeping second hand)
        interval = 33 if self.smooth else 1000
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(interval)

    def set_smooth(self, smooth: bool):
        self.smooth = smooth
        self.timer.setInterval(33 if smooth else 1000)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self.width(), self.height()
        side = min(w, h)
        scale = side / 1024.0

        # Draw dial base pixmap
        if self.base_pixmap:
            scaled_pix = self.base_pixmap.scaled(
                side, side,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            dx = (w - scaled_pix.width()) / 2.0
            dy = (h - scaled_pix.height()) / 2.0
            painter.drawPixmap(int(dx), int(dy), scaled_pix)
            center_x = dx + 513.0 * scale
            center_y = dy + 511.0 * scale
        else:
            center_x = w / 2.0
            center_y = h / 2.0
            # Fallback procedural background if image asset is missing
            self._draw_fallback_dial(painter, center_x, center_y, side * 0.48)

        # Retrieve system time
        now = QTime.currentTime()
        hours = now.hour() % 12
        minutes = now.minute()
        seconds = now.second()
        msecs = now.msec()

        if self.smooth:
            sec_val = seconds + msecs / 1000.0
            min_val = minutes + sec_val / 60.0
            hour_val = hours + min_val / 60.0
        else:
            sec_val = seconds
            min_val = minutes + seconds / 60.0
            hour_val = hours + minutes / 60.0

        hour_angle = hour_val * 30.0
        min_angle = min_val * 6.0
        sec_angle = sec_val * 6.0

        # Relative hand lengths
        hour_len = 175.0 * scale
        min_len = 245.0 * scale
        sec_len = 270.0 * scale

        # -------------------------------------------------------------
        # Helper: Draw lancet pointer with luminous glowing amber core
        # -------------------------------------------------------------
        def draw_lancet_hand(length, shoulder_w, base_w, tail_len, angle):
            painter.save()
            painter.translate(center_x, center_y)
            painter.rotate(angle)

            # Soft drop shadow
            shadow_path = QPainterPath()
            shadow_path.moveTo(0, -length)
            shadow_path.lineTo(shoulder_w, -length * 0.35)
            shadow_path.lineTo(base_w, 0)
            shadow_path.lineTo(base_w * 0.7, tail_len)
            shadow_path.lineTo(-base_w * 0.7, tail_len)
            shadow_path.lineTo(-base_w, 0)
            shadow_path.lineTo(-shoulder_w, -length * 0.35)
            shadow_path.closeSubpath()

            painter.save()
            painter.translate(3.0 * scale, 4.0 * scale)
            painter.fillPath(shadow_path, QColor(0, 0, 0, 95))
            painter.restore()

            # Outer beveled brass rim
            grad_brass = QLinearGradient(-shoulder_w, 0, shoulder_w, 0)
            grad_brass.setColorAt(0.0, QColor("#8a6625"))
            grad_brass.setColorAt(0.3, QColor("#e0a800"))
            grad_brass.setColorAt(0.7, QColor("#ffd700"))
            grad_brass.setColorAt(1.0, QColor("#664a10"))

            painter.setPen(QPen(QColor("#2d1f0c"), max(1.0, 1.5 * scale)))
            painter.setBrush(QBrush(grad_brass))
            painter.drawPath(shadow_path)

            # Inner luminous lumen core (glow)
            core_path = QPainterPath()
            cw_shoulder = shoulder_w * 0.55
            cw_base = base_w * 0.45
            core_path.moveTo(0, -length * 0.94)
            core_path.lineTo(cw_shoulder, -length * 0.35)
            core_path.lineTo(cw_base, -6 * scale)
            core_path.lineTo(-cw_base, -6 * scale)
            core_path.lineTo(-cw_shoulder, -length * 0.35)
            core_path.closeSubpath()

            grad_glow = QLinearGradient(0, -length, 0, 0)
            grad_glow.setColorAt(0.0, QColor("#fff3cc"))  # Parchment bright tip
            grad_glow.setColorAt(0.2, QColor("#ffaa22"))  # Radiant amber
            grad_glow.setColorAt(0.7, QColor("#ff6600"))  # Deep warm orange
            grad_glow.setColorAt(1.0, QColor("#b33c00"))  # Smoked red-amber

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(grad_glow))
            painter.drawPath(core_path)

            # Center spine highlight
            painter.setPen(QPen(QColor(255, 245, 220, 160), max(0.5, 1.0 * scale)))
            painter.drawLine(QPointF(0, -length * 0.92), QPointF(0, -length * 0.15))

            painter.restore()

        # Draw Hour Hand
        draw_lancet_hand(hour_len, 17.0 * scale, 13.0 * scale, 38.0 * scale, hour_angle)

        # Draw Minute Hand
        draw_lancet_hand(min_len, 13.0 * scale, 10.0 * scale, 48.0 * scale, min_angle)

        # Draw Second Hand (if enabled)
        if self.show_seconds:
            painter.save()
            painter.translate(center_x, center_y)
            painter.rotate(sec_angle)

            # Second hand shadow
            painter.setPen(QPen(QColor(0, 0, 0, 80), max(1.0, 2.0 * scale)))
            painter.drawLine(QPointF(2 * scale, -sec_len + 3 * scale), QPointF(2 * scale, 55 * scale + 3 * scale))

            # Needle body (metallic copper)
            painter.setPen(QPen(QColor("#b87333"), max(1.2, 2.0 * scale)))
            painter.drawLine(QPointF(0, -sec_len * 0.7), QPointF(0, 52 * scale))

            # Glowing ruby/vermillion tip
            painter.setPen(QPen(QColor("#e71d36"), max(1.2, 1.8 * scale)))
            painter.drawLine(QPointF(0, -sec_len), QPointF(0, -sec_len * 0.7))

            # Counterbalance Ring & Tail
            painter.setPen(QPen(QColor("#d4af37"), max(1.0, 1.5 * scale)))
            painter.setBrush(QBrush(QColor("#3d2b1f")))
            painter.drawEllipse(QPointF(0, 36 * scale), 7 * scale, 7 * scale)
            painter.setBrush(QBrush(QColor("#ffd700")))
            painter.drawEllipse(QPointF(0, 36 * scale), 2.5 * scale, 2.5 * scale)
            painter.restore()

        # Draw Multi-Tiered Center Brass Hub / Bevel Cap
        hub_r = 30.0 * scale
        painter.save()
        painter.translate(center_x, center_y)

        # Outer collar
        painter.setPen(QPen(QColor("#1f150c"), max(1.0, 2.0 * scale)))
        hub_grad = QRadialGradient(QPointF(-hub_r * 0.3, -hub_r * 0.3), hub_r)
        hub_grad.setColorAt(0.0, QColor("#fff3cc"))  # Specular highlight
        hub_grad.setColorAt(0.25, QColor("#ffd700")) # Polished gold
        hub_grad.setColorAt(0.65, QColor("#b58900")) # Industrial brass
        hub_grad.setColorAt(0.9, QColor("#664a10"))  # Aged bronze
        hub_grad.setColorAt(1.0, QColor("#221508"))  # Shadow rim

        painter.setBrush(QBrush(hub_grad))
        painter.drawEllipse(QPointF(0, 0), hub_r, hub_r)

        # Inner domed rivet cap
        cap_r = hub_r * 0.52
        cap_grad = QRadialGradient(QPointF(-cap_r * 0.35, -cap_r * 0.35), cap_r)
        cap_grad.setColorAt(0.0, QColor("#ffffff"))
        cap_grad.setColorAt(0.3, QColor("#ffd700"))
        cap_grad.setColorAt(0.8, QColor("#b58900"))
        cap_grad.setColorAt(1.0, QColor("#442f10"))
        painter.setPen(QPen(QColor("#3d2b1f"), max(0.8, 1.0 * scale)))
        painter.setBrush(QBrush(cap_grad))
        painter.drawEllipse(QPointF(0, 0), cap_r, cap_r)

        # Center screw slot
        painter.setPen(QPen(QColor("#221508"), max(1.0, 1.2 * scale)))
        painter.drawLine(QPointF(-cap_r * 0.5, 0), QPointF(cap_r * 0.5, 0))

        painter.restore()

    def _draw_fallback_dial(self, painter, cx, cy, radius):
        """Procedural fallback dial face if image asset is unavailable."""
        painter.setPen(QPen(QColor("#654321"), 3))
        painter.setBrush(QBrush(QColor("#1a120b")))
        painter.drawEllipse(QPointF(cx, cy), radius, radius)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    window = SteampunkClock(size=400, smooth=True)
    window.setWindowTitle("ASTRA Steampunk Chronometer (Qt6)")
    window.show()
    sys.exit(app.exec())
