import os
import subprocess


class JDK:

    def __init__(self, java_home):
        self.java_home = java_home
        self.java = None
        self.javac = None
        self.check_javac()
        self.tools = os.path.join(java_home, 'lib', 'tools.jar')
        self.jre_home = os.path.join(java_home, 'jre')
        self.rt = os.path.join(self.jre_home, 'lib', 'rt.jar')

    def check_javac(self):
        if not self.java_home:
            if 'JAVA_HOME' in os.environ and os.environ['JAVA_HOME']:
                self.java_home = os.environ['JAVA_HOME']
            else:
                print('ERROR: JAVA_HOME not found.')
                raise SystemExit()

        try:
            self.javac = os.path.join(self.java_home, os.sep.join(
                ['bin', 'javac']))
            self.java = os.path.join(self.java_home, os.sep.join(
                ['jre', 'bin', 'java']))
            self.run_javac(None, 10, None, '-version')

        except OSError:
            print('ERROR: javac not found.')
            raise SystemExit()

    def run_javac(self, java_file, timeout, cwd, *args):
        try:
            command = [self.javac] + list(args)

            if java_file:
                command.append(java_file)

            subprocess.check_call(command, stdout=subprocess.DEVNULL,
                                  timeout=timeout, cwd=cwd,
                                  stderr=subprocess.DEVNULL)
            return True
        except subprocess.CalledProcessError:
            print("Cannot compile {0} with arguments {1}".format(
                java_file, args))
            return False
        except subprocess.TimeoutExpired:
            print("javac timeout compiling {0}".format(java_file))
            return False


class Java:

    def __init__(self, java_home=None):
        self.java_home = java_home

    @property
    def java(self):
        return os.path.join(self.java_home, 'jre', 'bin', 'java')

    def _version_java(self):
        return self.run('-version')

    def run(self, *args):
        return self.exec_java(None, self.get_env(), None, *args)

    def exec_java(self, cwd, env, timeout, *args):
        return Java._exec(self.java, cwd, env, timeout, *args)

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
