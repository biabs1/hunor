import os
import copy
import logging

from collections import namedtuple

from hunor.args import arg_parser_gen, to_options_gen
from hunor.mutation.generate import _recover_state
from hunor.mutation.generate import _create_mutants_dir
from hunor.mutation.generate import _save_state
from hunor.tools.hunor_plugin import HunorPlugin
from hunor.tools.mujava import MuJava
from hunor.tools.evosuite2 import Evosuite
from hunor.tools.java_factory import JavaFactory
from hunor.tools.maven_factory import MavenFactory
from hunor.tools.junit2 import JUnit

from hunor.utils import sort_files
from hunor.utils import get_java_files
from hunor.utils import config


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

SimpleMutant = namedtuple('SimpleMutant', [
    'mid',
    'operator',
    'line_number',
    'method',
    'transformation',
    'dir'
])


def configure_logger():
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    fh = logging.FileHandler(os.path.join('hunor-evaluation.log'))
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    logger.addHandler(ch)
    logger.addHandler(fh)


def main():
    options = to_options_gen(arg_parser_gen())
    configure_logger()
    project_dir = os.path.abspath(os.sep.join(
        config(options.config_file)['source']))

    logger.debug(project_dir)

    java = JavaFactory.get_instance()
    maven = MavenFactory.get_instance()

    build = maven.compile(project_dir, clean=True)

    junit = JUnit(java=java, classpath=build.classes_dir)

    _create_mutants_dir(options)

    options.is_enable_reduce = False
    tool = HunorPlugin(copy.deepcopy(options))

    options.is_enable_reduce = True
    tool_reduced = HunorPlugin(copy.deepcopy(options))

    state = _recover_state(options)
    targets = state[0]
    analysed_files = state[1]

    files = get_java_files(options.java_src)

    for i, file in enumerate(sort_files(files)):
        print('EVALUATING {0} {1}/{2}'.format(file, i + 1, len(files)))
        if file not in analysed_files['files']:
            t = tool.generate(file, len(targets))
            t_r = tool_reduced.generate(file, len(targets))

            print('\ttargets found: {0}, in reduced: {1}'
                  .format(len(t), len(t_r)))
            targets += t
            for target in t_r:
                log = '| RUNNING FOR: {0} |'
                mutants_dir = os.path.join(options.mutants + '_reduced',
                                           target['directory'])
                print('-' * (len(log) + len(target['directory'])))
                print(log.format(target['directory']))
                print('-' * (len(log) + len(target['directory'])))

                mutation_tool = MuJava(mutants_dir)
                mutants = mutation_tool.read_log()

                suites = []
                count_assertions = 0
                for mutant in mutants:
                    mutant = mutants[mutant]
                    evosuite = Evosuite(
                        java=java,
                        classpath=os.path.join(build.classes_dir),
                        tests_src=os.path.join(mutants_dir, 'suites'),
                        sut_class=target['class'],
                        params=['-Dsearch_budget=60']
                    )
                    simple_mutant = SimpleMutant(mutant.id,
                                                 mutant.operator,
                                                 mutant.line_number,
                                                 mutant.method,
                                                 mutant.transformation,
                                                 mutant.path)

                    suite = evosuite.generate_differential(simple_mutant.dir)

                    logger.debug('Test suite created to %s mutation with'
                                 ' %i assertions.', mutant.mutation,
                                 suite.tests_with_assertion)

                    r = junit.exec_suite_with_mutant(suite, target['class'],
                                                     simple_mutant)
                    if not JUnit.check_pass(r):
                        count_assertions += suite.tests_with_assertion
                        suites.append(suite)
                    else:
                        logger.info('The suite not kill the mutant, %s'
                                    'EvosuiteR fail. :(', mutant.mutation)

                # TODO execute junit agains all mutants of full set.

            _save_state(options, state, t_r, file)


if __name__ == '__main__':
    main()