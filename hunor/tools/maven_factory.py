import os
import re
import logging
import subprocess

from collections import namedtuple

from hunor.args import arg_parser_gen, to_options_gen
from hunor.tools.java_factory import JavaFactory


logger = logging.getLogger()


TIMEOUT = 10 * 60


MavenResults = namedtuple('MavenResults', ['source_files', 'classes_dir'])


class Maven:

    def __init__(self, java, maven_home=None, skip_compile=False):
        self.maven_home = maven_home
        self.java = java
        self.skip_compile = skip_compile

        self._set_home()
        self._check()

    @property
    def mvn(self):
        return os.path.join(self.maven_home, 'bin', 'mvn')

    def _check(self):
        try:
            self._version()
        except FileNotFoundError:
            raise MavenNotFoundException()

    def _set_home(self):
        if not self.maven_home:
            if 'M2_HOME' in os.environ and os.environ['M2_HOME']:
                self.maven_home = os.environ['M2_HOME']
            elif 'MAVEN_HOME' in os.environ and os.environ['MAVEN_HOME']:
                self.maven_home = os.environ['MAVEN_HOME']
            elif 'MVN_HOME' in os.environ and os.environ['MVN_HOME']:
                self.maven_home = os.environ['MVN_HOME']
            else:
                logger.critical('MAVEN_HOME undefined.')
                raise MavenNotFoundException()

    def _version(self):
        return self.simple_exec('-version')

    def simple_exec(self, *args):
        return self._exec_mvn(None, self.java.get_env(), TIMEOUT, *args)

    def exec(self, cwd, timeout, *args):
        return self._exec_mvn(cwd, self.java.get_env(), timeout, *args)

    def _exec_mvn(self, cwd, env, timeout, *args):
        try:
            command = [self.mvn] + list(args)

            return subprocess.check_output(command, cwd=cwd, env=env,
                                           timeout=timeout,
                                           stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            logger.error('MAVEN: call process error with arguments {0}.'
                         .format(args), exc_info=True)
            logger.error(e.output.decode('unicode_escape'))
            raise e
        except subprocess.TimeoutExpired as e:
            logger.error('MAVEN: timeout with arguments {0}.'.format(args),
                         exc_info=True)
            raise e
        except FileNotFoundError as e:
            logger.error('MAVEN: not found.', exc_info=True)
            raise e

    def clean(self, project_dir, timeout):
        logger.info("Cleaning up project with maven...")
        return self._exec_mvn(project_dir, self.java.get_env(), timeout,
                              'clean').decode('unicode_escape')

    def compile(self, project_dir, timeout=TIMEOUT, clean=False):
        if clean:
            self.clean(project_dir, TIMEOUT)

        logger.info("Compiling the project with maven...")
        return self.extract_results(
            self._exec_mvn(project_dir, self.java.get_env(), timeout,
                           'compile').decode('unicode_escape'))

    def test(self, project_dir, timeout=TIMEOUT, clean=False):
        if clean:
            self.clean(project_dir, TIMEOUT)

        logger.info("Testing the project with maven...")
        return self._exec_mvn(project_dir, self.java.get_env(), timeout,
                              'test')

    @staticmethod
    def extract_results(output):
        output = re.findall('Compiling [0-9]* source files? to .*\n', output)
        if output:
            output = output[0].replace('\n', '').split()
            return MavenResults(int(output[1]), output[-1])
        raise BuildFailure()


class BuildFailure(Exception):
    pass


class MavenNotFoundException(SystemExit, Exception):
    pass


class MavenFactory:

    maven = None

    @classmethod
    def get_instance(cls):
        if not cls.maven:
            options = to_options_gen(arg_parser_gen())
            cls.maven = Maven(java=JavaFactory.get_instance(),
                              maven_home=options.maven_home)
        return cls.maven
