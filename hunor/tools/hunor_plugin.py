import os
import shutil

from hunor.tools.maven_factory import MavenFactory
from hunor.utils import read_json

TIMEOUT = 5 * 60
GROUP_ID = 'br.ufal.ic.easy.hunor.plugin'
ARTIFACT_ID = 'hunor-maven-plugin'


class HunorPlugin:

    def __init__(self, project_dir, mutants_dir):
        self.project_dir = project_dir
        self.mutants_dir = mutants_dir

    @staticmethod
    def _plugin_ref(goal):
        return '{0}:{1}:{2}'.format(GROUP_ID, ARTIFACT_ID, goal)

    @staticmethod
    def _includes(file):
        return '-Dhunor.includes=**{0}{1}'.format(os.sep, file)

    def generate(self, class_file, count=0):
        self._clean_result_dir()
        maven = MavenFactory.get_instance()
        maven.exec(self.project_dir, TIMEOUT,
                   self._plugin_ref('mujava-generate'),
                   self._includes(class_file))

        class_name = class_file.split('.')[0].replace(os.sep, '.')

        return self.subsuming(class_name, count)

    def subsuming(self, class_name, count=0):
        maven = MavenFactory.get_instance()
        maven.exec(self.project_dir, TIMEOUT, self._plugin_ref('subsuming'),
                   '-Dhunor.output={0}'.format(os.path.abspath(self.mutants_dir)),
                   '-Dhunor.skipTests=true')

        return self.read_targets_json(class_name, count)

    def read_targets_json(self, class_name, count=0):
        targets = []
        t = read_json(os.path.join(self.mutants_dir, 'plugin_targets.json'))

        for target in t:
            mutant = None

            for m in t[target]:
                if m['tid'] == int(target):
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
                            ''.join(mutant['transformation'].split('=>')[1])
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


