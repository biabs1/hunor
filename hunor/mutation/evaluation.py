import os
import copy
import logging

from coloredlogs import ColoredFormatter
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
from hunor.tools.tce import TCE

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
    style = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(style)
    colored = ColoredFormatter(style)
    ch = logging.StreamHandler()
    fh = logging.FileHandler(os.path.join('hunor-evaluation.log'))
    ch.setFormatter(colored)
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
        logger.info('EVALUATING {0} {1}/{2}'.format(file, i + 1, len(files)))
        if file not in analysed_files['files']:
            t = tool.generate(file, len(targets))
            t_r = tool_reduced.generate(file, len(targets))

            logger.info('\ttargets found: {0}, in reduced: {1}'
                        .format(len(t), len(t_r)))
            targets += t
            count = 1
            for target in t_r:
                log = '| RUNNING FOR: {0} {1}/{2} |'.format(
                    target['directory'], count, len(t_r))
                count += 1
                mutants_dir = os.path.join(options.mutants + '_reduced',
                                           target['directory'])
                logger.info('-' * len(log))
                logger.info(log)
                logger.info('-' * len(log))

                mutation_tool = MuJava(mutants_dir)
                mutants = mutation_tool.read_log()
                tce = TCE(options, build, target)

                suites = []
                count_assertions = 0
                has_error = False
                for mutant in mutants:
                    if not has_error:
                        mutant = mutants[mutant]
                        evosuite = Evosuite(
                            java=java,
                            classpath=os.path.join(build.classes_dir),
                            tests_src=os.path.join(mutants_dir, 'suites'),
                            sut_class=target['class'],
                            params=['-Dsearch_budget=60']
                        )

                        suite = evosuite.generate_differential(mutant.path)

                        logger.debug('Test suite created to %s mutation with'
                                     ' %i assertions.', mutant.mutation,
                                     suite.tests_with_assertion)

                        r = junit.exec_suite_with_mutant(
                            suite, target['class'], mutant)

                        if not JUnit.check_pass(r):
                            count_assertions += suite.tests_with_assertion
                            suites.append(suite)
                        else:
                            logger.info('The suite not kill the mutant, %s '
                                        'EvosuiteR fail. :(', mutant.mutation)
                            has_error = True

                if not has_error:
                    result = True

                    logger.debug('Testing all %i suites in original program',
                                 len(suites))
                    for suite in suites:
                        result = (result and JUnit.check_pass(
                            junit.exec_suite(suite, target['class']))
                                  and suite.tests_with_assertion > 0)

                    if result:
                        logger.debug('All tests created and not failing in '
                                     'original program.')
                    else:
                        logger.warning(
                            'Any suite is empty or failing in original '
                            'program.')

                    mutants_full_dir = os.path.join(options.mutants,
                                                    target['directory'])

                    all_mutants = MuJava(mutants_full_dir).read_log()
                    equivalent_mutants = set()
                    total_mutants = len(all_mutants)

                    if (result and mutants
                            and len(suites) == len(mutants)):

                        killed_mutants = set()
                        not_killed_mutants = set()

                        for mutant in all_mutants:
                            mutant = all_mutants[mutant]
                            if not os.path.exists(mutant.path):
                                total_mutants -= 1
                                continue

                            result = junit.exec_suites_with_mutant(
                                suites, target['class'], mutant)

                            if not JUnit.check_pass(result):
                                logger.debug(
                                    'Mutation %s (%s) was killed by %i tests.',
                                    mutant.mutation, mutant.id,
                                    result.fail_tests)
                                killed_mutants.add(mutant.mutation)
                            else:
                                logger.debug(
                                    'Mutation %s (%s) was not killed.',
                                    mutant.mutation, mutant.id)

                                if tce.run(mutant):
                                    equivalent_mutants.add(mutant.mutation)
                                    logger.debug('\tBut it is equivalent.')
                                not_killed_mutants.add(mutant.mutation)

                        not_equivalent_mutants = (total_mutants
                                                  - len(equivalent_mutants))

                        percent = (len(killed_mutants) / not_equivalent_mutants)
                        logger.info(
                            '%i mutants of %i were killed by tests. (%.2f)',
                            len(killed_mutants), not_equivalent_mutants,
                            percent),

                        headers = [
                            'id',
                            'target',
                            'mutants_in_minimal',
                            'test_suites',
                            'assertions',
                            'mutants',
                            'killed_mutants',
                            'not_equivalent_mutants',
                            '%',
                            'differential_success',
                            'minimal',
                            'survive',
                            'killed',
                            'equivalent',
                            'class',
                            'method',
                            'line',
                            'column',
                            'statement',
                            'operator'
                        ]

                        write_to_csv(headers, [
                            str(target['id']),
                            target['target_repr'],
                            str(len(mutants)),
                            str(len(suites)),
                            str(count_assertions),
                            str(total_mutants),
                            str(len(killed_mutants)),
                            str(not_equivalent_mutants),
                            str(percent),
                            str(len(suites) == len(mutants)),
                            ','.join([mutants[m].mutation for m in mutants]),
                            ','.join(not_killed_mutants.difference(
                                equivalent_mutants)),
                            ','.join(killed_mutants),
                            ','.join(equivalent_mutants),
                            target['class'],
                            target['method'],
                            str(target['line']),
                            str(target['column']),
                            target['statement'],
                            target['operator']
                        ], output_dir=options.mutants)

                    if mutants and len(suites) < len(mutants):
                        headers = ['id', 'class', 'method', 'line', 'column',
                                   'statement', 'operator']
                        write_to_csv(headers, [str(target['id']), target['class'],
                                               target['method'], str(target['line']),
                                               str(target['column']),
                                               target['statement'],
                                               target['operator']],
                                     output_dir=options.mutants,
                                     filename='not_tested.csv')

                _save_state(options, state, t_r, file)


def write_to_csv(headers, result, output_dir='.', filename='evaluation.csv',
                 exclude_if_exists=False):
    file = os.path.join(output_dir, filename)

    if exclude_if_exists:
        if os.path.exists(file):
            os.remove(file)

    if not os.path.exists(file):
        with open(file, 'w') as f:
            f.write(';'.join(headers) + '\n')

    with open(file, 'a') as f:
        f.write(';'.join(result) + '\n')


if __name__ == '__main__':
    main()
