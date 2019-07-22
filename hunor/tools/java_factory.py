import os
import subprocess
import logging

from hunor.args import arg_parser_gen, to_options_gen


logger = logging.getLogger()


TIMEOUT = 10


class Java:

    def __init__(self, java_home=None):
        self.java_home = java_home
        self._set_home()
        self._check()

    def _set_home(self):
        if not self.java_home:
            if os.getenv('JAVA_HOME'):
                self.java_home = os.getenv('JAVA_HOME')
            else:
                logger.critical('JAVA_HOME undefined')
                raise JavaNotFoundException()

    def _check(self):
        try:
            self._version_java()
            self._version_javac()
        except FileNotFoundError:
            logger.critical('{0} is not a valid JDK.'.format(self.java_home))
            raise JavaNotFoundException()

    @property
    def java(self):
        return os.path.join(self.java_home, 'jre', 'bin', 'java')

    @property
    def javac(self):
        return os.path.join(self.java_home, 'bin', 'javac')

    @property
    def tools(self):
        return os.path.join(self.java_home, 'lib', 'tools.jar')

    @property
    def rt(self):
        return os.path.join(self.java_home, 'jre', 'lib', 'rt.jar')

    def _version_java(self):
        return self.run('-version')

    def run(self, *args):
        return self.exec_java(None, self.get_env(), TIMEOUT, *args)

    def exec_java(self, cwd, env, timeout, *args):
        return Java._exec(self.java, cwd, env, timeout, *args)

    def _version_javac(self):
        return self.run_javac(None, '-version')

    def run_javac(self, java_file, *args):
        return self.exec_javac(java_file, None, self.get_env(), TIMEOUT, *args)

    def exec_javac(self, java_file, cwd, env, timeout, *args):
        if java_file:
            args = (java_file,) + args

        return Java._exec(self.javac, cwd, env, timeout, *args)

    @staticmethod
    def _exec(program, cwd, env, timeout, *args):
        try:
            command = [program] + list(args)

            return subprocess.check_output(command, cwd=cwd, env=env,
                                           timeout=timeout,
                                           stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise e
        except subprocess.TimeoutExpired as e:
            raise e
        except FileNotFoundError as e:
            raise e

    def get_env(self, variables=None):
        env = os.environ.copy()
        env['JAVA_HOME'] = self.java_home
        env['PATH'] = os.pathsep.join(
            [env['PATH'], os.path.join(self.java_home, 'bin')])

        if variables:
            env.update(variables)

        return env

    def exec_java_all(self, java_files, cwd, env, timeout, *args):
        for java_file in java_files:
            self.exec_javac(java_file, cwd, env, timeout, *args)


class JavaNotFoundException(SystemExit, Exception):
    pass


class JavaFactory:

    java = None

    @classmethod
    def get_instance(cls):
        if not cls.java:
            options = to_options_gen(arg_parser_gen())
            cls.java = Java(java_home=options.java_home)
        return cls.java
