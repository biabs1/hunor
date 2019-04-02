import os

from hunor.tools.suite_generator import SuiteGenerator
from hunor.utils import get_class_files, get_java_files
from hunor.tools.bin import EVOSUITE, EVOSUITE_RUNTIME
from hunor.tools.suite_generator import Suite


class EvosuiteRegression(SuiteGenerator):

    def _get_tool_name(self):
        return "evosuite_r"

    def _exec_tool(self):
        params = [
            '-jar', EVOSUITE,
            '-projectCP', self.classpath,
            '-class', self.sut_class,
            '-DOUTPUT_DIR=' + self.suite_dir
        ]

        params += self.parameters

        return self._exec(*tuple(params))

    def _test_classes(self):
        classes = []

        for class_file in sorted(get_class_files(self.suite_classes_dir)):
            filename, _ = os.path.splitext(class_file)
            if not filename.endswith('_scaffolding'):
                classes.append(filename.replace(os.sep, '.'))

        return classes

    def _get_suite_dir(self):
        return os.path.join(self.suite_dir, 'evosuite-tests')

    @staticmethod
    def _extra_classpath():
        return [EVOSUITE_RUNTIME]

    def _get_java_files(self):
        ordered_files = []

        for file in sorted(get_java_files(self.suite_dir)):
            if '_scaffolding' in file:
                ordered_files.insert(0, file)
            else:
                ordered_files.append(file)

        return ordered_files

    def _exec_differential(self, mutants_classpath):
        params = [
            '-jar', EVOSUITE,
            '-regressionSuite',
            '-projectCP', self.classpath,
            '-Dregressioncp=' + mutants_classpath,
            '-class', self.sut_class,
            '-DOUTPUT_DIR=' + self.suite_dir
        ]

        params += self.parameters

        return self._exec(*tuple(params))

    def generate(self, mutant_classpath=None, make_dir=True):
        if make_dir:
            self._make_src_dir()
        self._exec_differential(mutant_classpath)
        self._compile()

        return Suite(name=self.suite_name, source_dir=self.suite_dir,
                     classes_dir=self.suite_classes_dir,
                     test_classes=self._test_classes())
