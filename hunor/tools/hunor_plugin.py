import os
import shutil
import logging
import subprocess

from hunor.tools.maven_factory import MavenFactory
from hunor.utils import read_json

TIMEOUT = 10 * 60
GROUP_ID = 'br.ufal.ic.easy.hunor.plugin'
ARTIFACT_ID = 'hunor-maven-plugin'
VERSION = '0.3.9'


logger = logging.getLogger()


class HunorPlugin:

    def __init__(self, options, analyze_timeout=300):
        self.project_dir = options.source
        self.mutants_dir = options.mutants
        self.is_enable_reduce = options.is_enable_reduce
        self.is_enable_new_mutations = options.is_enable_new_mutations
        self.analyze_timeout = analyze_timeout

    @staticmethod
    def _plugin_ref(goal):
        return '{0}:{1}:{2}:{3}'.format(GROUP_ID, ARTIFACT_ID, VERSION, goal)

    @staticmethod
    def _includes(file):
        return '-Dhunor.includes=**{0}{1}'.format(os.sep, file)

    def gen(self, class_file, analyze=False, debug=False):
        self._clean_result_dir()
        maven = MavenFactory.get_instance()

        params = (self.project_dir, TIMEOUT,
                  self._plugin_ref('mujava-generate'),
                  '-Dhunor.enableRules={0}'.format(
                      'true' if self.is_enable_reduce else 'false'),
                  '-Dhunor.enableNewMutations={0}'.format(
                       'true' if self.is_enable_new_mutations else 'false'),
                  self._includes(class_file))

        if debug:
            params += '-X',

        logger.info("Generating mutants with {0}:{1}".format(ARTIFACT_ID,
                                                             VERSION))
        output = maven.exec(*params)

        if analyze:
            return self._extract_time(output), self._analyse(debug=debug)

        return self._extract_time(output),

    def _analyse(self, skip_tests=False, debug=False, split_reduced_dir=False):
        maven = MavenFactory.get_instance()

        timeout = TIMEOUT

        if not skip_tests:
            timeout = 24 * 60 * 60

        params = (self.project_dir, timeout,
                  self._plugin_ref('subsuming'),
                  '-Dhunor.timeout={0}'.format(self.analyze_timeout),
                  '-Dhunor.skipTests={0}'.format(
                      'true' if skip_tests else 'false'))

        if split_reduced_dir:
            params += '-Dhunor.output={0}'.format(self._dest_dir()),

        if debug:
            params += '-X',

        logger.info("Starting mutation testing...")
        output = maven.exec(*params)

        return self._extract_result(output)

    def generate(self, class_file, count=0):
        try:
            self.gen(class_file)
        except subprocess.TimeoutExpired:
            pass

        class_name = class_file.split('.')[0].replace(os.sep, '.')

        return self.subsuming(class_name, count)

    def subsuming(self, class_name, count=0):
        try:
            self._analyse(skip_tests=True, split_reduced_dir=True)
        except subprocess.TimeoutExpired:
            pass

        return self.read_targets_json(class_name, count)

    def read_targets_json(self, class_name, count=0):
        targets = []
        t = read_json(os.path.join(self.mutants_dir, 'plugin_targets.json'))

        for target in t:
            mutant = None

            for m in t[target]:
                if m['tid'] == int(target) and m['directory']:
                    mutant = m
                    break

            if mutant:
                targets.append(
                    {
                        'id': count,
                        'ignore': False,
                        'class': class_name,
                        'method': ''.join(mutant['methodSignature']
                                          .split('_')[1:]),
                        'type_method': mutant['methodSignature'],
                        'line': mutant['lineNumber'],
                        'column': 0,
                        'statement':
                            ''.join(mutant['transformation'].split('=>')[0])
                            .strip(),
                        'statement_nodes': '',
                        'context': [],
                        'context_full': [],
                        'method_ast': [],
                        'operand_nodes': '',
                        'operator_kind': '',
                        'operator': mutant['expOperator'],
                        'directory':
                            os.path.join(
                                os.sep.join(mutant['directory']
                                            .split(os.sep)[:-2]), target),
                        'oid': int(target),
                        'target_class': mutant['targetClass'],
                        'target_repr': mutant['targetRepr'],
                        'children': mutant['children'],
                        'prefix_operator': mutant['prefixExpOperator'],
                        'mutants': []
                    }
                )
            count += 1
        return targets

    def _clean_result_dir(self):
        result_dir = os.path.join(os.path.abspath(self.project_dir), 'result')
        if os.path.exists(result_dir):
            shutil.rmtree(result_dir)

    def _dest_dir(self):
        if self.is_enable_reduce:
            return os.path.abspath(self.mutants_dir + '_reduced')
        return os.path.abspath(self.mutants_dir)

    @staticmethod
    def _extract_time(output):
        output = output.decode('unicode_escape')
        for line in output.split('\n'):
            if line.startswith('[INFO] Total time:'):
                return str(line).replace('[INFO] Total time:', '').strip()

    @staticmethod
    def _extract_result(output):
        time = HunorPlugin._extract_time(output)
        output = output.decode('unicode_escape')
        for line in output.split('\n'):
            if line.startswith('[INFO] total:') and 'score:' in line:
                result = time,
                for data in line.split(','):
                    result += float(str(data.split(':')[1]).strip()),
                return result
