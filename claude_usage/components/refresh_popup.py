from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Static


class RefreshPopup(ModalScreen):
    def __init__(self, message: str, timeout: float = 1.5) -> None:
        super().__init__()
        self._message = message
        self._timeout = timeout

    def compose(self) -> ComposeResult:
        yield Static(self._message)

    def on_mount(self) -> None:
        self._timer = self.set_timer(self._timeout, self._close)

    def _close(self) -> None:
        self.dismiss()

    def on_click(self) -> None:
        self._timer.stop()
        self.dismiss()
