import os
import re

from hunor.tools.suite_generator import SuiteGenerator
from hunor.utils import get_class_files, get_java_files
from hunor.tools.bin import EVOSUITE, EVOSUITE_RUNTIME
from hunor.tools.suite_generator import Suite

METHOD_LIST_FILENAME = 'methods_to_test.txt'


class Evosuite(SuiteGenerator):

    def _get_tool_name(self):
        return "evosuite"

    def _exec_tool(self):
        params = [
            '-jar', EVOSUITE,
            '-projectCP', self.classpath,
            '-class', self.sut_class,
            '-Dtimeout', '10000',
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

    def _exec_regression_analyze(self):
        params = [
            '-jar', EVOSUITE,
            '-projectCP', self.classpath,
            '-Dregression_analyze',
            '-class', self.sut_class,
            '-DOUTPUT_DIR=' + self.suite_dir
        ]

        params += self.parameters

        return self._exec(*tuple(params))

    def generate_differential(self, mutant_classpath, make_dir=True):
        if make_dir:
            self._make_src_dir()

        output = self._exec_differential(mutant_classpath)

        tests_with_assertion = self._get_tests_with_assertion(output)

        self._compile()

        return Suite(suite_name=self.suite_name, suite_dir=self.suite_dir,
                     suite_classes_dir=self.suite_classes_dir,
                     test_classes=self._test_classes(),
                     tool_name=self._get_tool_name(),
                     tests_with_assertion=tests_with_assertion)

    def regression_analyze(self, make_dir=True):
        if make_dir:
            self._make_src_dir()

        return self._exec_regression_analyze()

    @staticmethod
    def _get_tests_with_assertion(output_bin):
        if not output_bin:
            return 0
        output = output_bin.decode('unicode_escape')
        return Evosuite._extract_differential_output(output)

    @staticmethod
    def _extract_differential_output(output):
        result = re.findall(r'Tests with assertion: [0-9]*', output)
        if len(result) > 0:
            result = re.findall(r'\d+', result[0])
            return int(result[0])
        return 0
