import logging
import typing as tp

from benchbuild.environments.domain import commands, model
from benchbuild.environments.service_layer import unit_of_work
from benchbuild.settings import CFG

from . import ensure

LOG = logging.getLogger(__name__)


def _create_build_container(
    name: str, layers: tp.List[tp.Any], uow: unit_of_work.AbstractUnitOfWork
) -> model.Image:
    container = uow.create_image(name, layers)
    image = container.image
    for layer in image.layers:
        uow.add_layer(container, layer)
    return image


def create_image(
    cmd: commands.CreateImage, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    """
    Create a container image using a registry.
    """
    replace = CFG['container']['replace']
    with uow:
        image = uow.registry.get_image(cmd.name)
        if image and not replace:
            return str(image.name)

        image = _create_build_container(cmd.name, cmd.layers, uow)
        uow.commit()

        return str(image.name)


def create_benchbuild_base(
    cmd: commands.CreateBenchbuildBase, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    """
    Create a benchbuild base image.
    """
    replace = CFG['container']['replace']
    with uow:
        image = uow.registry.get_image(cmd.name)
        if image and not replace:
            return str(image.name)

        image = _create_build_container(cmd.name, cmd.layers, uow)
        uow.commit()

        return str(image.name)


def update_image(
    cmd: commands.UpdateImage, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    """
    Update a benchbuild image.
    """
    with uow:
        ensure.image_exists(cmd.name, uow)

        image = _create_build_container(cmd.name, cmd.layers, uow)
        uow.commit()

        return str(image.name)


def run_project_container(
    cmd: commands.RunProjectContainer, uow: unit_of_work.AbstractUnitOfWork
) -> None:
    """
    Run a project container.
    """
    with uow:
        ensure.image_exists(cmd.image, uow)

        build_dir = uow.registry.env(cmd.image, 'BB_BUILD_DIR')
        if build_dir:
            uow.registry.temporary_mount(cmd.image, cmd.build_dir, build_dir)
        else:
            LOG.warning(
                'The image misses a configured "BB_BUILD_DIR" variable.'
            )
            LOG.warning('No result artifacts will be copied out.')

        container = uow.create_container(cmd.image, cmd.name)
        uow.run_container(container)


def export_image_handler(
    cmd: commands.ExportImage, uow: unit_of_work.AbstractUnitOfWork
) -> None:
    """
    Export a container image.
    """
    with uow:
        ensure.image_exists(cmd.image, uow)
        image = uow.registry.get_image(cmd.image)
        if image:
            uow.export_image(image.name, cmd.out_name)


def import_image_handler(
    cmd: commands.ImportImage, uow: unit_of_work.AbstractUnitOfWork
) -> None:
    """
    Import a container image.
    """
    with uow:
        uow.import_image(cmd.image, cmd.in_path)
