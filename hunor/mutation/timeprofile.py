import os
import copy
import logging
import subprocess

from coloredlogs import ColoredFormatter
from collections import namedtuple

from hunor.args import arg_parser_gen, to_options_gen
from hunor.mutation.generate import _create_mutants_dir
from hunor.tools.hunor_plugin import HunorPlugin
from hunor.tools.java_factory import JavaFactory
from hunor.tools.maven_factory import MavenFactory

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

    conf = config(options.config_file)
    project_dir = os.path.abspath(os.sep.join(conf['source']))

    logger.debug(project_dir)

    _create_mutants_dir(options)

    options.is_enable_reduce = False
    tool = HunorPlugin(copy.deepcopy(options))

    options.is_enable_reduce = True
    tool_reduced = HunorPlugin(copy.deepcopy(options))

    files = get_java_files(options.java_src)

    include = []

    if 'include' in conf:
        include = conf['include']

    for i, file in enumerate(sort_files(files)):
        if file in include:
            try:
                tool.gen(file, analyze=True)
            except subprocess.TimeoutExpired:
                logger.error("Timeout expired while process file {0} to "
                             "generate full set of mutants.".format(file))

            try:
                tool_reduced.gen(file, analyze=True)
            except subprocess.TimeoutExpired:
                logger.error("Timeout expired while process file {0} to "
                             "generate reduced set of mutants.".format(file))



if __name__ == '__main__':
    main()
