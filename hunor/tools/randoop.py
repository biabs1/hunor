import os
import subprocess
import json
import random

from hunor.utils import generate_classpath
from hunor.utils import get_java_files


PATH = os.path.dirname(os.path.abspath(__file__))

RANDOOP = os.sep.join([PATH, 'bin', 'randoop-all-4.0.3.jar'])
JUNIT = os.sep.join([PATH, 'bin', 'junit-4.12.jar'])
HAMCREST = os.sep.join([PATH, 'bin', 'hamcrest-core-1.3.jar'])
TOOL = 'randoop'


class Randoop:

    def __init__(self, jdk, classpath, config, tests_dir, sut_class,
                 project_dir=None, test_suite_name=TOOL):
        self.jdk = jdk
        self.tool_tests_dir = os.path.join(tests_dir, test_suite_name)
        self.tests_dir = tests_dir
        self.sut_class = sut_class
        self.classpath = classpath
        self.tests_src = os.path.join(self.tool_tests_dir, 'tests')
        self.tests_classes = os.path.join(self.tool_tests_dir, 'classes')
        self.parameters = []
        self.project_dir = project_dir
        self.test_suite_name = test_suite_name

        with open(config, 'r') as c:
            self.parameters = json.loads(c.read())[TOOL]['parameters']

    def _exec_tool(self):
        print("TEST SUITE: generating with {0}.".format(TOOL))
        command = [
            self.jdk.java,
            '-classpath', self.classpath + ':' + RANDOOP,
            'randoop.main.Main',
            'gentests',
            "--randomseed=" + str(random.randint(0, 9999)),
            "--testclass=" + self.sut_class,
            '--junit-output-dir=' + self.tests_src
        ]

        command += self.parameters

        try:
            env = os.environ.copy()
            env['PATH'] = (os.path.join(self.jdk.java_home, 'bin') +
                           os.pathsep + env['PATH'])
            return subprocess.check_output(command, shell=False,
                                           env=env,
                                           cwd=self.project_dir,
                                           timeout=5 * 60,
                                           stderr=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            print('# ERROR: {0} generate timed out.'.format(TOOL))
        except subprocess.CalledProcessError as e:
            print('# ERROR: {0} returned non-zero exit status.\n{1}'.format(
                TOOL, e.output.decode('unicode_escape')))

    def _compile(self):
        os.mkdir(self.tests_classes)

        classpath = generate_classpath([self.classpath, self.tests_src, JUNIT,
                                        HAMCREST])

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
        return ['RegressionTest']
