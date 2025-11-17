from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPixmap, QPainter, QPen, QCursor, QMouseEvent, QImage
from PyQt6.QtCore import Qt, QRect, QPoint

class CropWidget(QWidget):
    def __init__(self, pil_img, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.img = pil_img
        # Convert PIL image to QPixmap
        self.display_pixmap = self.pil_to_pixmap(pil_img)
        self.ratio_x = pil_img.width / self.display_pixmap.width()
        self.ratio_y = pil_img.height / self.display_pixmap.height()
        # Initial crop box (centered, 60% of width and height)
        w = self.display_pixmap.width()
        h = self.display_pixmap.height()
        crop_w, crop_h = int(w * 0.6), int(h * 0.6)
        crop_x, crop_y = (w - crop_w) // 2, (h - crop_h) // 2
        self.crop_rect = QRect(crop_x, crop_y, crop_w, crop_h)
        self.dragging = False
        self.resizing = False
        self.resize_dir = None
        self.offset = QPoint(0, 0)

    def pil_to_pixmap(self, pil_img):
        im = pil_img.convert("RGB")
        data = im.tobytes("raw", "RGB")
        qimg = QImage(data, im.width, im.height, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg).scaled(800, 600, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.display_pixmap)
        # Draw crop rect semi-transparent
        if not self.crop_rect.isNull():
            pen = QPen(Qt.GlobalColor.red)
            pen.setWidth(2)
            painter.setPen(pen)
            painter.setBrush(Qt.GlobalColor.transparent)
            painter.drawRect(self.crop_rect)
            # corners
            for pt in self._corner_points(self.crop_rect):
                painter.setBrush(Qt.GlobalColor.red)
                painter.drawEllipse(pt, 6, 6)
        painter.end()

    def mousePressEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()
        if event.button() == Qt.MouseButton.LeftButton:
            if self._on_corner(pos):
                self.resizing = True
                self.resize_dir = self._on_corner(pos)
            elif self.crop_rect.contains(pos):
                self.dragging = True
                self.offset = pos - self.crop_rect.topLeft()
            else:
                # Start new crop rect
                self.crop_rect = QRect(pos, pos)
                self.dragging = False
                self.resizing = False
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position().toPoint()
        if self.resizing and self.resize_dir:
            self._resize_crop(pos)
        elif self.dragging:
            tl = pos - self.offset
            size = self.crop_rect.size()
            br = QPoint(tl.x() + size.width(), tl.y() + size.height())
            # Ensure the rect stays within bounds
            tl.setX(max(0, min(tl.x(), self.display_pixmap.width() - size.width())))
            tl.setY(max(0, min(tl.y(), self.display_pixmap.height() - size.height())))
            self.crop_rect = QRect(tl, br)
        else:
            # Change cursor
            c = self._on_corner(pos)
            if c:
                self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor if c in ['tl','br'] else Qt.CursorShape.SizeBDiagCursor if c in ['tr','bl'] else Qt.CursorShape.SizeAllCursor))
            elif self.crop_rect.contains(pos):
                self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
            else:
                self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        if not self.dragging and not self.resizing and event.buttons() & Qt.MouseButton.LeftButton:
            # Draw new rect
            self.crop_rect.setBottomRight(pos)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self.dragging = False
        self.resizing = False
        self.resize_dir = None
        self.update()

    def _corner_points(self, rect):
        return [
            rect.topLeft(),         # tl
            rect.topRight(),        # tr
            rect.bottomRight(),     # br
            rect.bottomLeft()       # bl
        ]

    def _on_corner(self, pos):
        # Return 'tl', 'tr', 'br', 'bl' if mouse is on a corner, else None
        pts = self._corner_points(self.crop_rect)
        names = ['tl', 'tr', 'br', 'bl']
        for pt, name in zip(pts, names):
            if (pt - pos).manhattanLength() < 12:
                return name
        return None

    def _resize_crop(self, pos):
        rect = self.crop_rect
        if self.resize_dir == 'tl':
            rect.setTopLeft(pos)
        elif self.resize_dir == 'tr':
            rect.setTopRight(pos)
        elif self.resize_dir == 'br':
            rect.setBottomRight(pos)
        elif self.resize_dir == 'bl':
            rect.setBottomLeft(pos)
        self.crop_rect = rect.normalized()

    def get_crop_box(self):
        x1 = int(self.crop_rect.left() * self.ratio_x)
        y1 = int(self.crop_rect.top() * self.ratio_y)
        x2 = int(self.crop_rect.right() * self.ratio_x)
        y2 = int(self.crop_rect.bottom() * self.ratio_y)
        print(f"[DEBUG] get_crop_box: ({x1}, {y1}, {x2}, {y2})")
        return (x1, y1, x2, y2)
