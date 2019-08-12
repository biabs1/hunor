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
from hunor.utils import write_json
from hunor.utils import read_json

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

    targets_count = {}
    class_count = {}

    if os.path.exists('targets_count.json'):
        targets_count = read_json('targets_count.json')

    if os.path.exists('class_count.json'):
        class_count = read_json('class_count.json')

    for i, file in enumerate(sort_files(files)):
        print('PROCESSING {0} {1}/{2}'.format(file, i + 1, len(files)))
        if file not in analysed_files['files']:
            t = tool.generate(file, len(targets))
            print('\ttargets found: {0}'.format(len(t)))
            targets += t
            for target in t:
                if target['target_repr'] not in targets_count.keys():
                    targets_count[target['target_repr']] = 0

                targets_count[target['target_repr']] += 1

                if target['class'] not in class_count.keys():
                    class_count[target['class']] = 0

                class_count[target['class']] += 1

            write_json(targets_count, 'targets_count')
            write_json(class_count, 'class_count')
            _persist_targets(db, t)
            _save_state(options, state, t, file)


if __name__ == '__main__':
    main()
