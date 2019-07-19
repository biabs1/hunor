import os
import subprocess
import shutil

from hunor.mutation.mutant import Mutant
from hunor.utils import generate_classpath

PATH = os.path.dirname(os.path.abspath(__file__))

MAJOR = os.sep.join([PATH, 'bin', 'major', 'bin', 'javac'])


class Major:

    def __init__(self, mutants_dir, jdk=None, classpath=None):
        self.mutants_dir = mutants_dir
        self.jdk = jdk
        self.classpath = classpath

    def read_log(self):
        mutants_data = {}

        log_file = os.sep.join([self.mutants_dir, 'mutants.log'])

        with open(log_file) as log:
            for line in log.readlines():
                data = line.split(':')
                mutants_data[int(data[0])] = Mutant(
                    mid=int(data[0]),
                    operator=data[1],
                    original_symbol=data[2],
                    replacement_symbol=data[3],
                    method=data[4],
                    line_number=int(data[5]),
                    transformation=data[6],
                    path=self._mutant_dir(data[0])
                )
            log.close()

        return mutants_data

    def _mutant_dir(self, mid):
        return os.path.join(os.path.abspath(self.mutants_dir), str(mid))

    def _exec(self, parameters, cwd=None):
        cwd = self.mutants_dir if cwd is None else cwd

        classpath = generate_classpath(['.', self.classpath, self.jdk.rt])

        command = [MAJOR
                   ]
        command += parameters
        print(classpath)
        try:
            env = {}
            return subprocess.check_output(command, shell=False, cwd=cwd,
                                           env=env, timeout=(5 * 60))
        except subprocess.TimeoutExpired:
            print('# ERROR: Major time out.')
        except subprocess.CalledProcessError as e:
            print('# ERROR: {0} returned non-zero exit status.\n{1}'.format(
                'major', e.output.decode('unicode_escape')))

    def _exec_major(self, java_file, source_dir, classpath, operators='ALL'):
        export_dir = os.path.join(self.mutants_dir, '.tmp')
        dest_dir = os.path.join(export_dir, 'target', 'classes')

        if os.path.exists(export_dir):
            shutil.rmtree(export_dir)
        os.makedirs(dest_dir)

        print(self.jdk.rt)

        parameters = [
            '-XMutator:' + operators,
            '-J-Dmajor.export.context=true',
            '-J-Dmajor.export.mutants=true',
            '-J-Dmajor.export.directory=' + export_dir,
            '-cp', generate_classpath([classpath, self.jdk.rt]),
            '-d', dest_dir,
            java_file
        ]

        self._exec(parameters, cwd=source_dir)

    def generate(self, classes_dir, source_dir, java_file):
        self._exec_major(java_file, source_dir, classes_dir)
        return []
