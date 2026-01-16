from collections.abc import Callable

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from imessage_data_foundry.conversations.generator import GenerationPhase, GenerationProgress


def create_generation_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[cyan]{task.fields[phase]}[/cyan]"),
        TimeElapsedColumn(),
    )


def phase_to_display(phase: GenerationPhase) -> str:
    mapping = {
        GenerationPhase.GENERATING: "Generating messages",
        GenerationPhase.ASSIGNING_TIMESTAMPS: "Assigning timestamps",
        GenerationPhase.WRITING_DATABASE: "Writing to database",
    }
    return mapping.get(phase, phase.value)


def create_progress_callback(
    progress: Progress,
    task_id: TaskID,
) -> Callable[[GenerationProgress], None]:
    def callback(gen_progress: GenerationProgress) -> None:
        progress.update(
            task_id,
            completed=gen_progress.generated_messages,
            total=gen_progress.total_messages,
            phase=phase_to_display(gen_progress.phase),
        )

    return callback


def create_simple_progress() -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    )
