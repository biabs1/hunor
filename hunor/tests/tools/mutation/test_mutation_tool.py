from unittest import TestCase
from unittest.mock import MagicMock

import subprocess

from hunor.tools.mutation.mutation_tool import MutationTool


class FakeMutationTool(MutationTool):

    def _exec_tool(self):
        command = ['echo', '"Hello World!"']
        subprocess.check_output(command)


class TestMutationTool(TestCase):

    def test_generate_call_mutation_tool_process(self):
        tool = FakeMutationTool()

        subprocess.check_output = MagicMock(returns="Hello World!")
        tool.generate()

        subprocess.check_output.assert_called_once_with(
            ['echo', '"Hello World!"']
        )
