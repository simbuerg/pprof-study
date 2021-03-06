"""
Test the actions module.
"""
import unittest

from plumbum import ProcessExecutionError

from benchbuild.environments.domain.declarative import ContainerImage
from benchbuild.project import Project
from benchbuild.source import nosource
from benchbuild.utils import actions as a


class EmptyProject(Project):
    NAME = "test_empty"
    DOMAIN = "debug"
    GROUP = "debug"
    SOURCE = [nosource()]
    CONTAINER = ContainerImage().from_('benchbuild:alpine')

    def build(self):
        pass

    def configure(self):
        pass

    def download(self):
        pass


class FailAlways(a.Step):
    NAME = "FAIL ALWAYS"
    DESCRIPTION = "A Step that guarantees to fail."

    def __call__(self):
        raise ProcessExecutionError([], 1, "", "")


class PassAlways(a.Step):
    NAME = "PASS ALWAYS"
    DESCRIPTION = "A Step that guarantees to succeed."

    def __call__(self):
        return a.StepResult.OK


class ActionsTestCase(unittest.TestCase):

    def test_for_all_pass(self):
        ep = EmptyProject()
        actn = a.RequireAll(actions=[PassAlways(ep)])
        self.assertEqual(actn(), [a.StepResult.OK])

    def test_for_all_fail(self):
        ep = EmptyProject()
        actn = a.RequireAll(actions=[FailAlways(ep)])
        self.assertEqual(actn(), [a.StepResult.ERROR])
