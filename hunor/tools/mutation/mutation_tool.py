from abc import ABC, abstractmethod

import subprocess


class MutationTool(ABC):

    def __init__(self):
        pass

    @abstractmethod
    def _exec_tool(self):
        ''' Call mutation tool subprocess.'''

    def generate(self):
        self._exec_tool()
