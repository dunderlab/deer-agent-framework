from typing import List
from deer.schema.io import StepTrace


class TraceStore:
    def __init__(self) -> None:
        self._buffer: List[StepTrace] = []

    def reset(self) -> None:
        """Limpia la traza actual (para una nueva ejecución)."""
        self._buffer.clear()

    def append(self, trace: StepTrace) -> None:
        self._buffer.append(trace)

    def extend(self, traces: list[StepTrace]):
        self._buffer.extend(traces)

    def get_trace(self) -> List[StepTrace]:
        """Devuelve una copia de la traza acumulada."""
        return list(self._buffer)
