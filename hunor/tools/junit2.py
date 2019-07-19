import re
import time
import logging
import subprocess

from collections import namedtuple


from hunor.tools.bin import JUNIT, HAMCREST, JMOCKIT, EVOSUITE_RUNTIME
from hunor.utils import generate_classpath


logger = logging.getLogger()

TIMEOUT = 80

JUnitResult = namedtuple('JUnitResult', ['ok_tests', 'fail_tests',
                                         'fail_test_set', 'run_time',
                                         'coverage', 'timeout'])
Coverage = namedtuple('Coverage', ['call_points', 'test_cases', 'executions',
                                   'class_coverage'])


class JUnit:

    def __init__(self, java, classpath):
        self.java = java
        self.classpath = classpath

    def exec_suites_with_mutant(self, suites, sut_class, mutant):
        result = JUnitResult(0, 0, set(), 0, None, False)
        for suite in suites:
            result = self.update_result(result, self.exec_suite_with_mutant(
                suite, sut_class, mutant))
        return result

    def exec_suite_with_mutant(self, suite, sut_class, mutant):
        result = JUnitResult(0, 0, set(), 0, None, False)
        for test_class in suite.test_classes:
            result = self.update_result(result,
                                        self.exec_with_mutant(
                                            suite.suite_dir,
                                            suite.suite_classes_dir,
                                            sut_class, test_class, mutant))
        return result

    def exec_suite(self, suite, sut_class):
        result = JUnitResult(0, 0, set(), 0, None, False)
        for test_class in suite.test_classes:
            result = self.update_result(result,
                                        self.exec(suite.suite_dir,
                                                  suite.suite_classes_dir,
                                                  sut_class, test_class))
        return result

    @staticmethod
    def update_result(r_1, r_2):
        ok_tests = r_1.ok_tests + r_2.ok_tests
        fail_tests = r_1.fail_tests + r_2.fail_tests
        fail_test_set = r_1.fail_test_set.union(r_2.fail_test_set)
        run_time = r_1.run_time + r_2.run_time
        coverage = JUnit.update_coverage(r_1.coverage, r_2.coverage)
        timeout = r_1.timeout or r_2.timeout

        return JUnitResult(ok_tests, fail_tests, fail_test_set, run_time,
                           coverage, timeout)

    @staticmethod
    def update_coverage(c_1, c_2):
        if c_1 is not None and c_2 is not None:
            call_points = c_1.call_points.union(c_2.call_points)
            test_cases = c_1.test_cases.union(c_2.test_cases)
            executions = c_1.executions + c_2.execitions
            class_coverage = c_1.class_coverage.update(c_2.class_coverage)

            return Coverage(call_points, test_cases, executions,
                            class_coverage)

    @staticmethod
    def check_pass(result):
        return (result.ok_tests > 0 and result.fail_tests == 0
                and not result.timeout)

    def exec(self, suite_dir, suite_classes_dir, sut_class, test_class,
             timeout=TIMEOUT):
        classpath = generate_classpath([
            JMOCKIT, JUNIT, HAMCREST, EVOSUITE_RUNTIME,
            suite_classes_dir,
            self.classpath
        ])

        return self._exec(suite_dir, sut_class, test_class, classpath, '.',
                          timeout)

    def exec_with_mutant(self, suite_dir, suite_classes_dir, sut_class,
                         test_class, mutant, timeout=TIMEOUT):
        classpath = generate_classpath([
            JMOCKIT, JUNIT, HAMCREST, EVOSUITE_RUNTIME,
            suite_classes_dir,
            mutant.dir,
            self.classpath
        ])

        return self._exec(suite_dir, sut_class, test_class, classpath,
                          mutant.dir, timeout)

    def _exec(self, suite_dir, sut_class, test_class, classpath,
              cov_src_dirs='.', timeout=TIMEOUT):

        params = (
            '-classpath', classpath,
            '-Dcoverage-classes=' + sut_class,
            '-Dcoverage-output=html',
            '-Dcoverage-metrics=line',
            '-Dcoverage-srcDirs=' + cov_src_dirs,
            'org.junit.runner.JUnitCore', test_class
        )

        start = time.time()
        try:
            output = self.java.exec_java(suite_dir, self.java.get_env(),
                                         timeout, *params)
            return JUnitResult(
                *JUnit._extract_results_ok(output.decode('unicode_escape')),
                time.time() - start, None, False
            )
        except subprocess.CalledProcessError as e:
            return JUnitResult(
                *JUnit._extract_results(e.output.decode('unicode_escape')),
                time.time() - start, None, False
            )
        except subprocess.TimeoutExpired:
            elapsed_time = time.time() - start
            logger.warning("Run JUnit tests timed out. {0} seconds".format(
                elapsed_time))
            return JUnitResult(0, 0, set(), 0, None, True)

    @staticmethod
    def _extract_results_ok(output):
        result = re.findall(r'OK \([0-9]* tests?\)', output)
        if len(result) > 0:
            result = result[0].replace('(', '')
            r = [int(s) for s in result.split() if s.isdigit()]
            return r[0], 0, set()

        return 0, 0, set()

    @staticmethod
    def _extract_results(output):
        if len(re.findall(r'initializationError', output)) == 0:
            result = re.findall(r'Tests run: [0-9]*,[ ]{2}Failures: [0-9]*',
                                output)
            if len(result) > 0:
                result = result[0].replace(',', ' ')
                r = [int(s) for s in result.split() if s.isdigit()]
                return r[0], r[1], JUnit._extract_test_id(output)

        return 0, 0, set()

    @staticmethod
    def _extract_test_id(output):
        tests_fail = set()
        for test in re.findall(r'\.test[0-9]+\([A-Za-z0-9_]+\.java:[0-9]+\)',
                               output):
            i = re.findall(r'\d+', test)
            file = re.findall(r'\(.+?(?=\.)', test)[0][1:]
            test_case = re.findall(r'\..+?(?=\()', test)[0][1:]

            if len(i) > 0:
                tests_fail.add('{0}#{1}'.format(file, test_case, int(i[-1])))
            else:
                logger.error('Error in regex of junit output.')

        return tests_fail
