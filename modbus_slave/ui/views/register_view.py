"""Vista personalizada de registros (QTableView) con delegados para edición in-line estilo Excel."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QModelIndex, QRegularExpression, Qt
from PySide6.QtGui import (
    QDoubleValidator,
    QIntValidator,
    QRegularExpressionValidator,
    QValidator,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLineEdit,
    QStyledItemDelegate,
    QTableView,
    QWidget,
)

from modbus_slave.core.datastore import ModbusBlockType
from modbus_slave.core.formatters import DataFormat


class InlineRegisterDelegate(QStyledItemDelegate):
    """Delegado para edición in-line ultra rápida con validación numérica y feedback visual."""

    STYLE_VALID = """
        QLineEdit {
            background-color: #1e1e2e;
            color: #89dceb;
            border: 1px solid #89dceb;
            border-radius: 2px;
            padding: 2px;
            font-family: 'Consolas', monospace;
            font-weight: bold;
        }
    """

    STYLE_INVALID = """
        QLineEdit {
            background-color: #1e1e2e;
            color: #f38ba8;
            border: 1px solid #f38ba8;
            border-radius: 2px;
            padding: 2px;
            font-family: 'Consolas', monospace;
            font-weight: bold;
        }
    """

    def createEditor(self, parent: QWidget, option: Any, index: QModelIndex) -> QWidget:
        col = index.column()
        editor = QLineEdit(parent)
        editor.setStyleSheet(self.STYLE_VALID)

        if col == 2:
            model = index.model()
            block = getattr(model, "block", ModbusBlockType.HOLDING_REGISTERS.value)
            fmt = getattr(model, "format_type", DataFormat.INT16)

            if block in (ModbusBlockType.COILS.value, ModbusBlockType.DISCRETE_INPUTS.value):
                editor.setValidator(QRegularExpressionValidator(QRegularExpression(r"^[01]$"), editor))
            else:
                if fmt == DataFormat.INT16:
                    editor.setValidator(QIntValidator(-32768, 32767, editor))
                elif fmt == DataFormat.UINT16:
                    editor.setValidator(QIntValidator(0, 65535, editor))
                elif fmt == DataFormat.INT32:
                    editor.setValidator(QIntValidator(-2147483648, 2147483647, editor))
                elif fmt == DataFormat.UINT32:
                    editor.setValidator(QRegularExpressionValidator(QRegularExpression(r"^[0-9]{1,10}$"), editor))
                elif fmt == DataFormat.FLOAT32:
                    d_val = QDoubleValidator(editor)
                    d_val.setNotation(QDoubleValidator.Notation.StandardNotation)
                    editor.setValidator(d_val)
                elif fmt == DataFormat.HEX:
                    editor.setValidator(QRegularExpressionValidator(QRegularExpression(r"^(0x)?[0-9a-fA-F]{1,4}$"), editor))
                elif fmt == DataFormat.BIN:
                    editor.setValidator(QRegularExpressionValidator(QRegularExpression(r"^[01 ]{1,19}$"), editor))

            # Conectar feedback visual reactivo según validación
            editor.textChanged.connect(lambda _: self._validate_editor_text(editor))

        return editor

    def _validate_editor_text(self, editor: QLineEdit) -> None:
        validator = editor.validator()
        if not validator:
            editor.setStyleSheet(self.STYLE_VALID)
            return

        text = editor.text()
        state, _, _ = validator.validate(text, 0)
        if state == QValidator.State.Acceptable or (state == QValidator.State.Intermediate and (not text or text == "-")):
            editor.setStyleSheet(self.STYLE_VALID)
        else:
            editor.setStyleSheet(self.STYLE_INVALID)

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        if isinstance(editor, QLineEdit):
            val = str(index.data(Qt.ItemDataRole.EditRole) or "")
            editor.setText(val)
            editor.selectAll()

    def setModelData(self, editor: QWidget, model: Any, index: QModelIndex) -> None:
        if isinstance(editor, QLineEdit):
            validator = editor.validator()
            if validator:
                state, _, _ = validator.validate(editor.text(), 0)
                if state != QValidator.State.Acceptable:
                    return
            model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor: QWidget, option: Any, index: QModelIndex) -> None:
        editor.setGeometry(option.rect)

    def editorEvent(self, event: QEvent, model: Any, option: Any, index: QModelIndex) -> bool:
        """Soporta toggle rápido con la barra espaciadora en Coils y Discrete Inputs."""
        if index.column() == 2 and event.type() == QEvent.Type.KeyPress:
            key_event = event
            if key_event.key() == Qt.Key.Key_Space:
                current = index.data(Qt.ItemDataRole.EditRole)
                new_val = "0" if str(current) == "1" else "1"
                model.setData(index, new_val, Qt.ItemDataRole.EditRole)
                return True
        return super().editorEvent(event, model, option, index)


class RegisterTableView(QTableView):
    """Tabla de visualización y edición in-line de registros Modbus."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setItemDelegate(InlineRegisterDelegate(self))
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setAlternatingRowColors(True)
        self.setShowGrid(True)
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(26)

        # Ajuste de cabeceras
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    def keyPressEvent(self, event: Any) -> None:
        """Navegación tipo Excel: presionar Enter guarda y avanza a la siguiente fila."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            curr = self.currentIndex()
            if curr.isValid() and not self.state() == QAbstractItemView.State.EditingState:
                # Si no está editando, presionar Enter abre el editor
                self.edit(curr)
                return
        super().keyPressEvent(event)
