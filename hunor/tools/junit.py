import os
import re
import copy
import subprocess
import shutil
import time

from bs4 import BeautifulSoup

from hunor.utils import generate_classpath


PATH = os.path.dirname(os.path.abspath(__file__))

JUNIT = os.sep.join([PATH, 'bin', 'junit-4.12.jar'])
HAMCREST = os.sep.join([PATH, 'bin', 'hamcrest-core-1.3.jar'])
EVOSUITE = os.sep.join([PATH, 'bin', 'evosuite-standalone-runtime-1.0.6.jar'])
JMOCKIT = os.sep.join([PATH, 'bin', 'jmockit-1.40-marcio.1.jar'])


class JUnit:

    def __init__(self, jdk, sut_class, classpath, source_dir):
        self.jdk = jdk
        self.sut_class = sut_class
        self.classpath = classpath
        self.source_dir = source_dir

    def _run_test(self, test_suite, test_classes_dir, test_class,
                  mutant_classpath='', timeout=(60 * 3)):

        classpath = generate_classpath([
            JMOCKIT, JUNIT, HAMCREST, EVOSUITE,
            test_classes_dir,
            mutant_classpath,
            self.classpath,
        ])

        coverage_source_dirs = self.source_dir

        if os.path.exists(os.path.join(mutant_classpath,
                          self.sut_class.replace('.', os.sep) + '.java')):
            coverage_source_dirs = mutant_classpath

        command = [
            self.jdk.java,
            '-classpath', classpath,
            '-Dcoverage-classes=' + self.sut_class,
            '-Dcoverage-output=html',
            '-Dcoverage-metrics=line',
            '-Dcoverage-srcDirs=' + coverage_source_dirs,
            'org.junit.runner.JUnitCore', test_class
        ]

        start = time.time()
        try:
            output = subprocess.check_output(command, shell=False,
                                             cwd=test_suite,
                                             stderr=subprocess.DEVNULL,
                                             timeout=timeout)
            return (_extract_results_ok(output.decode('unicode_escape')),
                    time.time() - start)
        except subprocess.CalledProcessError as e:
            return (_extract_results(e.output.decode('unicode_escape')),
                    time.time() - start)
        except subprocess.TimeoutExpired:
            elapsed_time = time.time() - start
            print("# ERROR: Run JUnit tests timed out. {0} seconds".format(
                elapsed_time
            ))
            return (0, 0, set()), elapsed_time

    def _run_test_suite(self, test_suite, mutant_classpath, mutation_line=0,
                        original_path=None, timeout=(60 * 3)):
        total = 0
        fail = 0
        fail_tests = set()
        coverage = 0
        coverage_tests = set()
        elapsed_time = 0

        for test_class in test_suite.classes:
            (t, f, f_s), e_t = self._run_test(test_suite.source_dir,
                                              test_suite.classes_dir,
                                              test_class,
                                              mutant_classpath=mutant_classpath,
                                              timeout=timeout)

            total += t
            fail += f
            elapsed_time += e_t
            fail_tests = fail_tests.union(f_s)
            coverage_src = test_suite.source_dir

            if original_path is not None:
                coverage_src = os.path.join(original_path, test_suite.id)

            c, c_t = self._count_line_coverage(coverage_src, mutation_line)
            coverage += c
            coverage_tests = coverage_tests.union(c_t)
            coverage_report_dir = os.path.join(test_suite.source_dir,
                                               'coverage-report')
            coverage_report_dst_dir = os.path.join(
                    mutant_classpath, test_suite.id, 'coverage-report')

            if os.path.exists(coverage_report_dst_dir):
                shutil.rmtree(coverage_report_dst_dir)

            if os.path.exists(coverage_report_dir):
                shutil.copytree(coverage_report_dir, coverage_report_dst_dir)

        return total, fail, fail_tests, coverage, coverage_tests, elapsed_time

    def run_test_suites(self, test_suites, mutant_classpath, mutation_line=0,
                        original_path=None):
        suites = copy.deepcopy(test_suites)
        for t in suites:
            if suites[t].is_valid:
                test_suite = suites[t]

                if test_suites[t].elapsed_time:
                    (total, fail, fail_tests, coverage, coverage_tests,
                     elapsed_time) = self._run_test_suite(
                        test_suite, mutant_classpath, mutation_line,
                        original_path, timeout=test_suites[t].elapsed_time * 3)
                else:
                    (total, fail, fail_tests, coverage, coverage_tests,
                     elapsed_time) = self._run_test_suite(
                        test_suite, mutant_classpath, mutation_line,
                        original_path)

                test_suite.fail = (fail != 0)
                test_suite.coverage = coverage
                test_suite.tests_total = total
                test_suite.fail_tests_total = fail
                test_suite.fail_tests = self._prefix(test_suite, fail_tests)
                test_suite.coverage_tests = self._prefix(test_suite,
                                                         coverage_tests)
                test_suite.elapsed_time = elapsed_time
                if test_suite.tests_total == 0:
                    test_suite.is_valid = False
                    if (test_suites[t].elapsed_time is not None
                            and test_suite.elapsed_time > test_suites[t].elapsed_time):
                        test_suite.fail = True
                        test_suite.maybe_in_loop = True

        return suites

    @staticmethod
    def _prefix(test_suite, ids):
        result = set()
        for i in ids:
            result.add('{0}_{1}'.format(test_suite.prefix, i))
        return result

    def _count_line_coverage(self, output_dir, mutation_line):

        report_html_path = os.path.join(
            output_dir, 'coverage-report',
            self.sut_class.replace('.', os.sep) + '.html')

        tests = set()

        if os.path.exists(report_html_path):
            with open(report_html_path) as html:
                soup = BeautifulSoup(html, 'html.parser')
                for tr in soup.find_all('tr'):
                    td_line = tr.find_all('td', class_='line')
                    td_count = tr.find_all('td', class_='callpoints-count')
                    if td_line and td_count:
                        if mutation_line == int(td_line[0].string):
                            for li in tr.find_all('li'):
                                method_name = _extract_li_id(li.string)
                                if method_name is not None:
                                    tests.add(method_name)
                html.close()

        return len(tests), tests


def _extract_results_ok(output):
    result = re.findall(r'OK \([0-9]* tests?\)', output)
    if len(result) > 0:
        result = result[0].replace('(', '')
        r = [int(s) for s in result.split() if s.isdigit()]

        return r[0], 0, set()
    return 0, 0, set()


def _extract_results(output):
    if len(re.findall(r'initializationError', output)) == 0:
        result = re.findall(r'Tests run: [0-9]*,[ ]{2}Failures: [0-9]*', output)
        if len(result) > 0:
            result = result[0]
            result = result.replace(',', ' ')
            r = [int(s) for s in result.split() if s.isdigit()]
            tests_fail = _extract_test_id(output)
            return r[0], r[1], tests_fail
    return 0, 0, set()


def _extract_test_id(output):
    tests_fail = set()
    for test in re.findall(r'\.test[0-9]+\([A-Za-z0-9_]+\.java:[0-9]+\)', output):
        i = re.findall(r'\d+', test)
        file = re.findall(r'\(.+?(?=\.)', test)[0][1:]
        test_case = re.findall(r'\..+?(?=\()', test)[0][1:]

        if len(i) > 0:
            tests_fail.add('{0}#{1}'.format(file, test_case, int(i[-1])))
        else:
            print("*** ERROR: Error in regex of junit output.")

    return tests_fail


def _extract_li_id(li):
    try:
        file = re.findall(r'[A-Za-z0-9_]+#', li)[0][:-1]
        test_case = re.findall(r'#test[0-9]+:', li)[0][1:-1]
        return '{0}#{1}'.format(file, test_case)
    except IndexError:
        return None
