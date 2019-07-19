import os
import copy

from hunor.args import arg_parser_gen, to_options_gen
from hunor.mutation.generate import _recover_state
from hunor.mutation.generate import _initialize_db
from hunor.mutation.generate import _persist_targets
from hunor.mutation.generate import _save_state
from hunor.mutation.generate import _create_mutants_dir
from hunor.utils import sort_files
from hunor.utils import get_java_files
from hunor.main import Hunor

from hunor.tools.hunor_plugin import HunorPlugin


def main():
    options = to_options_gen(arg_parser_gen())

    _create_mutants_dir(options)
    tool = HunorPlugin(options)
    state = _recover_state(options)
    db = _initialize_db(options)
    targets = state[0]
    analysed_files = state[1]

    files = get_java_files(options.java_src)

    for i, file in enumerate(sort_files(files)):
        print('PROCESSING {0} {1}/{2}'.format(file, i + 1, len(files)))
        if file not in analysed_files['files']:
            t = tool.generate(file, len(targets))
            print('\ttargets found: {0}'.format(len(t)))
            targets += t
            for target in t:
                print('-' * (23 + len(target['directory'])))
                print('| RUNNING HUNOR FOR: {0} |'.format(target['directory']))
                print('-' * (23 + len(target['directory'])))
                target['mutants'] = _run_hunor(options, target)

            _persist_targets(db, t)
            _save_state(options, state, t, file)


def _run_hunor(options, target):
    mutants, _ = Hunor(_create_hunor_options(options, target),
                       using_target=True).run()
    return mutants


def _create_hunor_options(options, target):
    o = copy.copy(options)
    o.mutants = os.path.join(o.mutants, str(target['directory']))
    o.output = o.mutants
    o.sut_class = target['class']
    o.no_compile = True

    return o


if __name__ == '__main__':
    main()
