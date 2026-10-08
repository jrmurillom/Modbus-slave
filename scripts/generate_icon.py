"""Script para generar el icono oficial de Modbus Slave Pro (Opción 1: Matriz de Registros).

Genera:
- modbus_slave/assets/icon.png (512x512 PNG con canal alfa)
- modbus_slave/assets/icon.ico (Windows ICO multi-resolución: 256, 128, 64, 48, 32, 24, 16 px)
"""

import os
from PIL import Image
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)


def render_icon(size: int = 512) -> QImage:
    """Renderiza el icono vectorial a la resolución especificada."""
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor(0, 0, 0, 0))

    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    scale = size / 100.0

    # 1. Contenedor Base (Squircle)
    margin = 5.0 * scale
    rect_size = 90.0 * scale
    radius = 22.0 * scale

    bg_grad = QLinearGradient(0, 0, size, size)
    bg_grad.setColorAt(0.0, QColor("#1e1e2e"))
    bg_grad.setColorAt(1.0, QColor("#11111b"))

    rim_grad = QLinearGradient(0, 0, size, size)
    rim_grad.setColorAt(0.0, QColor("#45475a"))
    rim_grad.setColorAt(1.0, QColor("#313244"))

    squircle_path = QPainterPath()
    squircle_path.addRoundedRect(QRectF(margin, margin, rect_size, rect_size), radius, radius)

    painter.fillPath(squircle_path, QBrush(bg_grad))
    painter.strokePath(squircle_path, QPen(QBrush(rim_grad), 2.5 * scale))

    # 2. Pistas de circuito salientes (Traces exteriores)
    trace_pen = QPen(QColor("#45475a"), 2.2 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(trace_pen)

    # Superior / Inferior
    for x in [36.0, 50.0, 64.0]:
        painter.drawLine(QPointF(x * scale, 15.0 * scale), QPointF(x * scale, 28.0 * scale))
        painter.drawLine(QPointF(x * scale, 85.0 * scale), QPointF(x * scale, 72.0 * scale))

    # Izquierda / Derecha
    for y in [36.0, 50.0, 64.0]:
        painter.drawLine(QPointF(15.0 * scale, y * scale), QPointF(28.0 * scale, y * scale))
        painter.drawLine(QPointF(85.0 * scale, y * scale), QPointF(72.0 * scale, y * scale))

    # 3. Resplandor exterior suave para el chip central
    glow_color = QColor(137, 220, 235, 40)
    for g_offset in [3.0, 2.0, 1.0]:
        glow_pen = QPen(glow_color, g_offset * scale)
        glow_path = QPainterPath()
        glow_path.addRoundedRect(
            QRectF((28.0 - g_offset * 0.5) * scale, (28.0 - g_offset * 0.5) * scale, (44.0 + g_offset) * scale, (44.0 + g_offset) * scale),
            (8.0 + g_offset * 0.5) * scale,
            (8.0 + g_offset * 0.5) * scale,
        )
        painter.strokePath(glow_path, glow_pen)

    # 4. Chip Cuerpo Central
    chip_path = QPainterPath()
    chip_path.addRoundedRect(QRectF(28.0 * scale, 28.0 * scale, 44.0 * scale, 44.0 * scale), 8.0 * scale, 8.0 * scale)
    painter.fillPath(chip_path, QBrush(QColor("#181825")))
    painter.strokePath(chip_path, QPen(QColor("#89dceb"), 2.0 * scale))

    # 5. Matriz de Registros Modbus 2x2
    # Celda 1 (Holding Register Activo - Superior Izquierda)
    c1_rect = QRectF(33.0 * scale, 33.0 * scale, 15.0 * scale, 15.0 * scale)
    c1_path = QPainterPath()
    c1_path.addRoundedRect(c1_rect, 3.0 * scale, 3.0 * scale)
    painter.fillPath(c1_path, QBrush(QColor(137, 220, 235, 60)))
    painter.strokePath(c1_path, QPen(QColor("#89dceb"), 1.6 * scale))

    bar_pen_cyan = QPen(QColor("#89dceb"), 2.2 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(bar_pen_cyan)
    painter.drawLine(QPointF(36.5 * scale, 40.5 * scale), QPointF(44.5 * scale, 40.5 * scale))

    # Celda 2 (Coil / Bit Activo - Superior Derecha)
    c2_rect = QRectF(52.0 * scale, 33.0 * scale, 15.0 * scale, 15.0 * scale)
    c2_path = QPainterPath()
    c2_path.addRoundedRect(c2_rect, 3.0 * scale, 3.0 * scale)
    painter.fillPath(c2_path, QBrush(QColor(166, 227, 161, 60)))
    painter.strokePath(c2_path, QPen(QColor("#a6e3a1"), 1.6 * scale))

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor("#a6e3a1")))
    painter.drawEllipse(QPointF(59.5 * scale, 40.5 * scale), 2.8 * scale, 2.8 * scale)

    # Celda 3 (Input Register - Inferior Izquierda)
    c3_rect = QRectF(33.0 * scale, 52.0 * scale, 15.0 * scale, 15.0 * scale)
    c3_path = QPainterPath()
    c3_path.addRoundedRect(c3_rect, 3.0 * scale, 3.0 * scale)
    painter.fillPath(c3_path, QBrush(QColor("#1e1e2e")))
    painter.strokePath(c3_path, QPen(QColor("#45475a"), 1.6 * scale))

    bar_pen_slate = QPen(QColor("#45475a"), 2.2 * scale, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    painter.setPen(bar_pen_slate)
    painter.drawLine(QPointF(36.5 * scale, 59.5 * scale), QPointF(44.5 * scale, 59.5 * scale))

    # Celda 4 (Holding Register 2 - Inferior Derecha)
    c4_rect = QRectF(52.0 * scale, 52.0 * scale, 15.0 * scale, 15.0 * scale)
    c4_path = QPainterPath()
    c4_path.addRoundedRect(c4_rect, 3.0 * scale, 3.0 * scale)
    painter.fillPath(c4_path, QBrush(QColor(137, 220, 235, 50)))
    painter.strokePath(c4_path, QPen(QColor("#89dceb"), 1.6 * scale))

    painter.setPen(bar_pen_cyan)
    painter.drawLine(QPointF(55.5 * scale, 59.5 * scale), QPointF(63.5 * scale, 59.5 * scale))

    # 6. LED de Estado Superior Derecho (Verde Esmeralda con Halo)
    led_center = QPointF(80.0 * scale, 20.0 * scale)
    # Halo
    halo_grad = QLinearGradient(led_center.x() - 6 * scale, led_center.y() - 6 * scale, led_center.x() + 6 * scale, led_center.y() + 6 * scale)
    halo_grad.setColorAt(0.0, QColor(166, 227, 161, 100))
    halo_grad.setColorAt(1.0, QColor(166, 227, 161, 0))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(166, 227, 161, 50)))
    painter.drawEllipse(led_center, 6.0 * scale, 6.0 * scale)

    # Núcleo del LED
    painter.setBrush(QBrush(QColor("#a6e3a1")))
    painter.drawEllipse(led_center, 3.5 * scale, 3.5 * scale)

    painter.end()
    return img


def generate_assets(output_dir: str) -> None:
    """Genera icon.png e icon.ico en la carpeta de destino."""
    os.makedirs(output_dir, exist_ok=True)

    png_path = os.path.join(output_dir, "icon.png")
    ico_path = os.path.join(output_dir, "icon.ico")

    # Renderizar master a 512x512
    qimg = render_icon(512)
    qimg.save(png_path, "PNG")
    print(f"[OK] Guardado PNG en: {png_path}")

    # Convertir a ICO multi-resolución usando Pillow
    pil_img = Image.open(png_path)
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    pil_img.save(ico_path, format="ICO", sizes=icon_sizes)
    print(f"[OK] Guardado ICO multi-resolución en: {ico_path}")


if __name__ == "__main__":
    app = QGuiApplication([])
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "modbus_slave", "assets"))
    generate_assets(target_dir)
