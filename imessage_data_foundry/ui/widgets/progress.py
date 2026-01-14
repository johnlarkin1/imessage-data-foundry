"""Progress widget for generation display."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, ProgressBar, Static

from imessage_data_foundry.conversations.generator import GenerationProgress


class GenerationProgressWidget(Static):
    """Widget showing generation progress with phase and stats."""

    DEFAULT_CSS = """
    GenerationProgressWidget {
        height: auto;
        padding: 1;
    }
    GenerationProgressWidget #phase-label {
        text-style: bold;
    }
    GenerationProgressWidget #stats-label {
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._progress = GenerationProgress(
            total_messages=0,
            generated_messages=0,
            current_batch=0,
            total_batches=0,
            phase="initializing",
        )

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Initializing...", id="phase-label")
            yield ProgressBar(total=100, show_eta=False, id="progress-bar")
            yield Label("", id="stats-label")

    def update_progress(self, progress: GenerationProgress) -> None:
        self._progress = progress

        phase_map = {
            "generating": "Generating messages",
            "assigning_timestamps": "Assigning timestamps",
            "writing_database": "Writing to database",
        }
        phase_text = phase_map.get(progress.phase, progress.phase)

        phase_label = self.query_one("#phase-label", Label)
        phase_label.update(f"{phase_text}...")

        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.update(progress=progress.percent_complete)

        stats_label = self.query_one("#stats-label", Label)
        stats_label.update(
            f"Batch {progress.current_batch}/{progress.total_batches} | "
            f"{progress.generated_messages}/{progress.total_messages} messages"
        )

    def set_complete(self, message: str = "Complete!") -> None:
        phase_label = self.query_one("#phase-label", Label)
        phase_label.update(f"[green]{message}[/green]")

        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_bar.update(progress=100)

    def set_error(self, message: str) -> None:
        phase_label = self.query_one("#phase-label", Label)
        phase_label.update(f"[red]{message}[/red]")
