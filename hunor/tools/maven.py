import os
import subprocess


class Maven:

    def __init__(self, maven_home, jdk, no_compile=False):
        self.maven_home = maven_home
        self.jdk = jdk
        self._check_maven()
        self.no_compile = no_compile

    def _check_maven(self):
        if not self.maven_home:
            if 'M2_HOME' in os.environ and os.environ['M2_HOME']:
                self.maven_home = os.environ['M2_HOME']
            elif 'MAVEN_HOME' in os.environ and os.environ['MAVEN_HOME']:
                self.maven_home = os.environ["MAVEN_HOME"]
            else:
                print('ERROR: MAVEN_HOME not found.')
                raise SystemExit()

        try:
            self._run(None, None, 10, '-version')
        except OSError:
            print('maven not found.')
            raise SystemExit()

    def _run(self, project_dir, target, timeout, *args):

        command = [os.path.join(self.maven_home, os.sep.join(['bin', 'mvn']))]

        if target:
            command.append(target)

        command = command + list(args)

        env = os.environ.copy()
        env['JAVA_HOME'] = self.jdk.java_home

        return subprocess.check_output(command, cwd=project_dir, env=env,
                                       timeout=timeout)

    def compile(self, project_dir, timeout=(20 * 60)):
        try:
            project_dir = os.path.abspath(project_dir)
            if not self.no_compile:
                self._run(project_dir, 'compile', timeout)
                print('SUCCESS: {0} compiled!'.format(project_dir))

            if os.path.exists(os.path.join(project_dir, 'target')):
                return os.path.join(project_dir, 'target', 'classes')
            elif os.path.exists(os.path.join(project_dir, 'build')):
                return os.path.join(project_dir, 'build', 'classes')
            else:
                print("ERROR: Maven classes directory not found.")
                raise SystemExit
        except subprocess.CalledProcessError as e:
            print(e.output.decode('unicode_escape'))
            raise SystemError
        except subprocess.TimeoutExpired:
            print('# ERROR: Maven compile timed out.')
            raise SystemError

    def compile_project(self, project_dir):
        return self.compile(project_dir)

    def test(self, project_dir, timeout=(10 * 60)):
        try:
            project_dir = os.path.abspath(project_dir)
            output = self._run(project_dir, 'test', timeout)
            return _extract_results_ok(output.decode('unicode_escape'))
        except subprocess.CalledProcessError as e:
            return _extract_results(e.output.decode('unicode_escape'))
        except subprocess.TimeoutExpired:
            print("# ERROR: Run JUnit tests timed out.")


def _extract_results_ok(output):
    print(output)


def _extract_results(output):
    print(output)
