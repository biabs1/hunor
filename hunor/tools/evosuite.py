import os
import subprocess

from hunor.utils import get_class_files, generate_classpath, config
from hunor.utils import get_java_files

PATH = os.path.dirname(os.path.abspath(__file__))

EVOSUITE = os.sep.join([PATH, 'bin', 'evosuite-1.0.6.jar'])
EVOSUITE_RUNTIME = os.sep.join(
    [PATH, 'bin', 'evosuite-standalone-runtime-1.0.6.jar'])
JUNIT = os.sep.join([PATH, 'bin', 'junit-4.12.jar'])
HAMCREST = os.sep.join([PATH, 'bin', 'hamcrest-core-1.3.jar'])
TOOL = 'evosuite'


class Evosuite:

    def __init__(self, jdk, classpath, config_file, tests_dir, sut_class,
                 project_dir=None, test_suite_name=TOOL):
        self.jdk = jdk
        self.tool_tests_dir = os.path.join(tests_dir, test_suite_name)
        self.tests_dir = tests_dir
        self.sut_class = sut_class
        self.classpath = classpath
        self.tests_src = os.path.join(self.tool_tests_dir, 'evosuite-tests')
        self.tests_classes = os.path.join(self.tool_tests_dir, 'classes')
        self.parameters = config(config_file)[TOOL]['parameters']
        self.project_dir = project_dir
        self.test_suite_name = test_suite_name

    def _exec_tool(self):
        print("TEST SUITE: generating with {0}.".format(TOOL))
        command = [
            self.jdk.java,
            '-jar', EVOSUITE,
            '-projectCP', self.classpath,
            '-class', self.sut_class,
            '-DOUTPUT_DIR=' + self.tool_tests_dir
        ]
        command += self.parameters

        try:
            return subprocess.check_output(command, shell=False,
                                           cwd=self.tool_tests_dir,
                                           timeout=10 * 60)
        except subprocess.TimeoutExpired:
            print('# ERROR: {0} generate timed out.'.format(TOOL))
        except subprocess.CalledProcessError as e:
            print('# ERROR: {0} returned non-zero exit status.\n{1}'.format(
                TOOL, e.output.decode('unicode_escape')))

    def _compile(self):
        os.mkdir(self.tests_classes)

        classpath = generate_classpath([self.classpath, self.tests_src, JUNIT,
                                        HAMCREST, EVOSUITE_RUNTIME])

        for java_test_file in sorted(get_java_files(self.tests_src)):
            self.jdk.run_javac(os.path.join(self.tests_src, java_test_file),
                               5 * 60, self.tests_src, '-classpath', classpath,
                               '-d', self.tests_classes)

        return self._test_classes()

    def generate(self):

        if not os.path.exists(self.tests_src):
            os.makedirs(self.tests_src)

        self._exec_tool()
        classes = self._compile()

        return self.tests_src, self.tests_classes, classes

    def _test_classes(self):
        classes = []

        for class_file in sorted(get_class_files(self.tests_classes)):
            filename, _ = os.path.splitext(class_file)
            if not filename.endswith('_scaffolding'):
                classes.append(filename.replace(os.sep, '.'))

        return classes
