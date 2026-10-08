"""Script para generar el icono oficial de Modbus Slave Pro (Opción C: Modern Tile 92%).

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
    QFont,
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
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    scale = size / 100.0

    # 1. Contenedor Base Squircle Modern Tile (92% de ocupación óptica)
    margin = 4.0 * scale
    rect_size = 92.0 * scale
    radius = 22.0 * scale

    bg_grad = QLinearGradient(0, 0, size, size)
    bg_grad.setColorAt(0.0, QColor("#1e293b"))
    bg_grad.setColorAt(1.0, QColor("#0f172a"))

    squircle_path = QPainterPath()
    squircle_path.addRoundedRect(QRectF(margin, margin, rect_size, rect_size), radius, radius)

    painter.fillPath(squircle_path, QBrush(bg_grad))
    # Bisel luminoso cian (#38bdf8) de alta visibilidad en barra oscura o clara
    painter.strokePath(squircle_path, QPen(QColor("#38bdf8"), 2.2 * scale))

    # 2. Configuración de Fuente Monospace para Registros
    font = QFont("Consolas")
    font.setPixelSize(int(14.0 * scale))
    font.setBold(True)
    painter.setFont(font)

    # 3. Cuadrante 1: Holding Register "HR" (Superior Izquierda)
    q1_rect = QRectF(18.0 * scale, 18.0 * scale, 28.0 * scale, 28.0 * scale)
    q1_path = QPainterPath()
    q1_path.addRoundedRect(q1_rect, 8.0 * scale, 8.0 * scale)
    painter.fillPath(q1_path, QBrush(QColor(2, 132, 199, 75)))
    painter.strokePath(q1_path, QPen(QColor("#38bdf8"), 2.0 * scale))

    painter.setPen(QColor("#38bdf8"))
    painter.drawText(q1_rect, int(Qt.AlignmentFlag.AlignCenter), "HR")

    # 4. Cuadrante 2: Coil / Bit Activo "LED" (Superior Derecha)
    q2_rect = QRectF(54.0 * scale, 18.0 * scale, 28.0 * scale, 28.0 * scale)
    q2_path = QPainterPath()
    q2_path.addRoundedRect(q2_rect, 8.0 * scale, 8.0 * scale)
    painter.fillPath(q2_path, QBrush(QColor(22, 163, 74, 65)))
    painter.strokePath(q2_path, QPen(QColor("#4ade80"), 2.0 * scale))

    # Indicador Circular Coil On (Halo + Núcleo Esmeralda)
    coil_center = QPointF(68.0 * scale, 32.0 * scale)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(74, 222, 128, 80)))
    painter.drawEllipse(coil_center, 9.0 * scale, 9.0 * scale)
    painter.setBrush(QBrush(QColor("#4ade80")))
    painter.drawEllipse(coil_center, 5.0 * scale, 5.0 * scale)

    # 5. Cuadrante 3: Input Register "IR" (Inferior Izquierda)
    q3_rect = QRectF(18.0 * scale, 54.0 * scale, 28.0 * scale, 28.0 * scale)
    q3_path = QPainterPath()
    q3_path.addRoundedRect(q3_rect, 8.0 * scale, 8.0 * scale)
    painter.fillPath(q3_path, QBrush(QColor(51, 65, 85, 125)))
    painter.strokePath(q3_path, QPen(QColor("#64748b"), 2.0 * scale))

    painter.setPen(QColor("#94a3b8"))
    painter.drawText(q3_rect, int(Qt.AlignmentFlag.AlignCenter), "IR")

    # 6. Cuadrante 4: Discrete / Value "01" (Inferior Derecha)
    q4_rect = QRectF(54.0 * scale, 54.0 * scale, 28.0 * scale, 28.0 * scale)
    q4_path = QPainterPath()
    q4_path.addRoundedRect(q4_rect, 8.0 * scale, 8.0 * scale)
    painter.fillPath(q4_path, QBrush(QColor(2, 132, 199, 75)))
    painter.strokePath(q4_path, QPen(QColor("#38bdf8"), 2.0 * scale))

    painter.setPen(QColor("#38bdf8"))
    painter.drawText(q4_rect, int(Qt.AlignmentFlag.AlignCenter), "01")

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
