import os
import shutil
import json

from argparse import ArgumentParser

from hunor.utils import config


DEFAULT = {
    'maven_timeout': 3600,
    'output': 'hunor-output',
    'coverage_threshold': 1.0,
    'suites_number': 1
}


class Options:

    def __init__(self, maven_home, java_home, config_file, mutants,
                 mutation_tool, sut_class=None, source=None,
                 output=DEFAULT['output'], is_evosuite_disabled=False,
                 is_randoop_disabled=False, is_minimal_testsuite_disabled=False,
                 maven_timeout=DEFAULT['maven_timeout'],
                 coverage_threshold=DEFAULT['coverage_threshold'],
                 no_compile=False, suites_evosuite=DEFAULT['suites_number'],
                 suites_randoop=DEFAULT['suites_number'],
                 is_enable_reduce=False, is_enable_new_mutations=False):

        if maven_home:
            self.maven_home = os.path.abspath(maven_home)
        else:
            self.maven_home = None

        if java_home:
            self.java_home = os.path.abspath(java_home)
        else:
            self.java_home = None

        self.maven_timeout = maven_timeout
        self.is_randoop_disabled = is_randoop_disabled
        self.is_evosuite_disabled = is_evosuite_disabled
        self.config_file = os.path.abspath(config_file)
        self.source = _set_source_dir(source, self.config_file)
        self.output = _set_output_dir(output)
        self.mutants = os.path.abspath(mutants)
        self.coverage_threshold = coverage_threshold
        self.sut_class = sut_class
        self.mutation_tool = mutation_tool
        self.no_compile = no_compile
        self.suites_evosuite = suites_evosuite
        self.suites_randoop = suites_randoop
        self.java_src = _set_java_src(self.config_file)
        self.is_minimal_testsuite_disabled = is_minimal_testsuite_disabled
        self.is_enable_reduce = is_enable_reduce
        self.is_enable_new_mutations = is_enable_new_mutations

    def __str__(self):
        return json.dumps({
                'maven_home': self.maven_home,
                'java_home': self.java_home,
                'maven_timeout': self.maven_timeout,
                'is_randoop_disabled': self.is_randoop_disabled,
                'is_evosuite_disabled': self.is_evosuite_disabled,
                'config_file': self.config_file,
                'source': self.source,
                'output': self.output,
                'mutants': self.mutants,
                'coverage_threshold': self.coverage_threshold,
                'sut_class': self.sut_class,
                'mutation_tool': self.mutation_tool,
                'no_compile': self.no_compile,
                'suites_evosuite': self.suites_evosuite,
                'suites_randoop': self.suites_randoop,
                'is_minimal_testsuite_disabled':
                    self.is_minimal_testsuite_disabled,
                'is_enable_reduce': self.is_enable_reduce,
                'is_enable_new_mutations': self.is_enable_new_mutations
        }, indent=2)


def _set_source_dir(source, config_file):
    if source:
        return os.path.abspath(source)

    return os.path.join(
        os.path.dirname(config_file),
        os.sep.join(config(config_file)['source'])
    )


def _set_java_src(config_file):
    return os.path.join(
        os.path.dirname(config_file),
        os.sep.join(config(config_file)['source']),
        os.sep.join(config(config_file)['java_src'])
    )


def _set_output_dir(output):
    if os.path.exists(output):
        shutil.rmtree(output)
    os.makedirs(output, exist_ok=True)

    return os.path.abspath(output)


def _to_options(parser):
    o = parser.parse_args()

    return Options(
        maven_home=o.maven_home,
        java_home=o.java_home,
        is_randoop_disabled=o.is_randoop_disabled,
        is_evosuite_disabled=o.is_evosuite_disabled,
        config_file=o.config_file,
        source=o.source,
        mutants=o.mutants,
        mutation_tool=o.mutation_tool,
        output=o.output,
        maven_timeout=o.maven_timeout,
        coverage_threshold=float(o.coverage_threshold),
        no_compile=o.no_compile,
        suites_evosuite=int(o.suites_evosuite),
        suites_randoop=int(o.suites_randoop),
        is_minimal_testsuite_disabled=o.is_minimal_testsuite_disabled,
        is_enable_reduce=o.is_enable_reduce,
        is_enable_new_mutations=o.is_enable_new_mutations

    )


def to_options(parser):
    args = parser.parse_args()
    options = _to_options(parser)

    options.sut_class = args.sut_class

    return options


def to_options_gen(parser):
    return _to_options(parser)


def arg_parser():
    parser = _default_arg_parser()

    parser.add_argument('--class',
                        action='store',
                        dest='sut_class',
                        required=True)

    return parser


def arg_parser_gen():
    return _default_arg_parser()


def _default_arg_parser():
    parser = ArgumentParser()

    parser.add_argument('-m', '--maven-home',
                        action='store',
                        dest='maven_home')

    parser.add_argument('-j', '--java-home',
                        action='store',
                        dest='java_home')

    parser.add_argument('--maven-timeout',
                        action='store',
                        dest='maven_timeout',
                        default=DEFAULT['maven_timeout'])

    parser.add_argument('--disable-randoop',
                        action='store_true',
                        dest='is_randoop_disabled')

    parser.add_argument('--disable-evosuite',
                        action='store_true',
                        dest='is_evosuite_disabled')

    parser.add_argument('-c', '--config_file',
                        action='store',
                        dest='config_file',
                        required=True)

    parser.add_argument('-s', '--source',
                        action='store',
                        dest='source')

    parser.add_argument('-o', '--output',
                        action='store',
                        dest='output',
                        default=DEFAULT['output'])

    parser.add_argument('--mutants',
                        action='store',
                        dest='mutants',
                        required=True)

    parser.add_argument('--coverage-threshold',
                        action='store',
                        dest='coverage_threshold',
                        default=DEFAULT['coverage_threshold'])

    parser.add_argument('--mutation-tool',
                        action='store',
                        dest='mutation_tool',
                        choices=['major', 'mujava', 'pit'],
                        required=True)

    parser.add_argument('--no-compile',
                        action='store_true',
                        dest='no_compile')

    parser.add_argument('--suites-evosuite',
                        action='store',
                        dest='suites_evosuite',
                        default=DEFAULT['suites_number'])

    parser.add_argument('--suites-randoop',
                        action='store',
                        dest='suites_randoop',
                        default=DEFAULT['suites_number'])

    parser.add_argument('--disable-minimal-testsuite',
                        action='store_true',
                        dest='is_minimal_testsuite_disabled')

    parser.add_argument('--enable-reduce',
                        action='store_true',
                        dest='is_enable_reduce')

    parser.add_argument('--enable-new-mutations',
                        action='store_true',
                        dest='is_enable_new_mutations')

    return parser