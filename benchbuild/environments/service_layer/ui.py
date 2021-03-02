import typing as tp

import rich
from rich.progress import Task, Progress, BarColumn

from benchbuild.environments.domain import events
from benchbuild.environments.service_layer import unit_of_work


def print_image_created(
    _: unit_of_work.ImageUnitOfWork, event: events.ImageCreated
) -> None:
    __progress__.console.print(f'Building {event.name}')


def print_creating_layer(
    _: unit_of_work.ImageUnitOfWork, event: events.CreatingLayer
) -> None:
    __progress__.console.print(event.layer)


def print_layer_created(
    _: unit_of_work.ImageUnitOfWork, event: events.LayerCreated
) -> None:
    rich.print(f'[bold]{event.name}[/bold] {event.layer}')


def print_image_committed(
    _: unit_of_work.ImageUnitOfWork, event: events.ImageCommitted
) -> None:
    __progress__.console.print(f'Finished {event.name}')


def print_image_destroyed(
    _: unit_of_work.ImageUnitOfWork, event: events.ImageCommitted
) -> None:
    del event


def print_container_created(
    _: unit_of_work.ContainerUnitOfWork, event: events.ContainerCreated
) -> None:
    __progress__.console.print(
        f'Created {event.name} for image: {event.image_id}'
    )


__progress__ = Progress(
    "[progress.description]{task.description}", BarColumn(),
    "[progress.percentage]{task.percentage:>3.0f}%"
)
__progress__ = Progress()
__tasks__: tp.Dict[str, Task] = {}
