"""Diálogo para configurar la simulación automática de un registro."""

from __future__ import annotations

from typing import Optional
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from modbus_slave.core.formatters import DataFormat, Endianness
from modbus_slave.core.simulation import SimulationRule, WaveformType


class SimulationDialog(QDialog):
    """Configuración de generador de señal para un registro."""

    def __init__(
        self,
        block: str,
        address: int,
        format_type: DataFormat,
        endianness: Endianness,
        existing_rule: Optional[SimulationRule] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.block = block
        self.address = address
        self.format_type = format_type
        self.endianness = endianness
        self.setWindowTitle(f"Simulación de Señal - Dirección {address}")
        self.setFixedWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.chk_enabled = QCheckBox("Habilitar simulación en este registro")
        self.chk_enabled.setChecked(existing_rule is not None)
        self.chk_enabled.toggled.connect(self._toggle_fields)
        layout.addWidget(self.chk_enabled)

        # Forma de onda
        self.cmb_waveform = QComboBox()
        self.cmb_waveform.addItem("Rampa (Incremento continuo)", WaveformType.RAMP.value)
        self.cmb_waveform.addItem("Onda Senoidal", WaveformType.SINE.value)
        self.cmb_waveform.addItem("Ruido Aleatorio", WaveformType.RANDOM.value)
        self.cmb_waveform.addItem("Pulso Toggle (0 / 1)", WaveformType.TOGGLE.value)
        self.cmb_waveform.currentIndexChanged.connect(self._on_waveform_changed)
        form.addRow("Tipo de Señal:", self.cmb_waveform)

        # Parámetros numéricos
        self.spn_min = QDoubleSpinBox()
        self.spn_min.setRange(-1e6, 1e6)
        self.spn_min.setValue(existing_rule.min_val if existing_rule else 0.0)
        form.addRow("Valor Mínimo:", self.spn_min)

        self.spn_max = QDoubleSpinBox()
        self.spn_max.setRange(-1e6, 1e6)
        self.spn_max.setValue(existing_rule.max_val if existing_rule else 100.0)
        form.addRow("Valor Máximo:", self.spn_max)

        self.spn_step = QDoubleSpinBox()
        self.spn_step.setRange(0.01, 1000.0)
        self.spn_step.setValue(existing_rule.step if existing_rule else 1.0)
        form.addRow("Paso (Step Rampa):", self.spn_step)

        self.spn_amp = QDoubleSpinBox()
        self.spn_amp.setRange(0.01, 1e6)
        self.spn_amp.setValue(existing_rule.amplitude if existing_rule else 50.0)
        form.addRow("Amplitud Seno:", self.spn_amp)

        self.spn_freq = QDoubleSpinBox()
        self.spn_freq.setRange(0.01, 10.0)
        self.spn_freq.setValue(existing_rule.frequency if existing_rule else 0.2)
        form.addRow("Frecuencia (Hz):", self.spn_freq)

        self.spn_offset = QDoubleSpinBox()
        self.spn_offset.setRange(-1e6, 1e6)
        self.spn_offset.setValue(existing_rule.offset if existing_rule else 50.0)
        form.addRow("Offset Seno:", self.spn_offset)

        layout.addLayout(form)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._toggle_fields(self.chk_enabled.isChecked())
        if existing_rule:
            for i in range(self.cmb_waveform.count()):
                if self.cmb_waveform.itemData(i) == existing_rule.waveform.value:
                    self.cmb_waveform.setCurrentIndex(i)
                    break

    def _toggle_fields(self, enabled: bool) -> None:
        self.cmb_waveform.setEnabled(enabled)
        self.spn_min.setEnabled(enabled)
        self.spn_max.setEnabled(enabled)
        self.spn_step.setEnabled(enabled)
        self.spn_amp.setEnabled(enabled)
        self.spn_freq.setEnabled(enabled)
        self.spn_offset.setEnabled(enabled)

    def _on_waveform_changed(self) -> None:
        pass

    def get_rule(self) -> Optional[SimulationRule]:
        if not self.chk_enabled.isChecked():
            return None

        wf = WaveformType(self.cmb_waveform.currentData())
        return SimulationRule(
            block=self.block,
            address=self.address,
            format_type=self.format_type,
            endianness=self.endianness,
            waveform=wf,
            min_val=self.spn_min.value(),
            max_val=self.spn_max.value(),
            step=self.spn_step.value(),
            amplitude=self.spn_amp.value(),
            frequency=self.spn_freq.value(),
            offset=self.spn_offset.value(),
        )
