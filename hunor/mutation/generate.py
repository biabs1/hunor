import os
import copy

from hunor.tools.mujava import MuJava
from hunor.tools.java import Java
from hunor.tools.maven import Maven
from hunor.utils import  write_json, read_json, sort_files
from hunor.utils import get_java_files
from hunor.args import arg_parser_gen, to_options_gen
from hunor.main import Hunor
from hunor.db.models import Database
from hunor.db.queries import Queries


def main():
    options = to_options_gen(arg_parser_gen())

    jdk = Java(options.java_home)

    classes_dir = _maven_work(options, jdk)

    _create_mutants_dir(options)

    tool = MuJava(options.mutants, jdk=jdk, classpath=classes_dir)

    state = _recover_state(options)
    db = _initialize_db(options)
    targets = state[0]
    analysed_files = state[1]

    count = 1
    files = get_java_files(options.java_src)

    for i, file in enumerate(sort_files(files)):
        print('PROCESSING {0} {1}/{2}'.format(file, i + 1, len(files)))
        if file not in analysed_files['files']:
            t = tool.generate(classes_dir, options.java_src, file, len(targets))
            print('\ttargets found: {0}'.format(len(t)))
            targets += t
            for target in t:
                target['mutants'] = _run_hunor(options, target)

            _persist_targets(db, t)
            _save_state(options, state, t, file)

            count += 1


def _run_hunor(options, target):
    mutants, _ = Hunor(_create_hunor_options(options, target),
                       using_target=True).run()
    return mutants


def _persist_targets(db, targets):
    for target in targets:
        if len(target['mutants']) > 0:
            db.save_target_and_mutants(target, target['mutants'])


def _recover_state(options):
    targets = _recover_targets(options)
    analysed_files = _recover_files(options)

    return targets, analysed_files


def _save_state(options, state, t, file):
    _save_targets(options, state[0])
    _save_files(options, state[1], t, file)


def _create_mutants_dir(options):
    if not os.path.exists(options.mutants):
        os.makedirs(options.mutants)


def _maven_work(options, jdk, run_tests=False):
    mvn = Maven(jdk=jdk, maven_home=options.maven_home)
    target_dir = mvn.compile_project(options.source)

    if run_tests:
        mvn.test(options.source)

    return target_dir


def _initialize_db(options):
    db = Queries(Database(os.path.join(options.mutants, 'mutation.db')))
    db.create_tables()

    return db


def _recover_targets(options):
    targets_file = os.path.join(options.mutants, 'targets.json')

    if os.path.exists(targets_file):
        targets = read_json(targets_file)
    else:
        targets = []

    return targets


def _recover_files(options):
    save_status_file = os.path.join(options.mutants, 'save_status.json')

    if os.path.exists(save_status_file):
        status = read_json(save_status_file)
    else:
        status = {
            'files': [],
            'targets': 0
        }

    return status


def _save_files(options, files, targets, java_file):
    files['files'].append(java_file)
    files['targets'] += len(targets)
    write_json(files, 'save_status', options.mutants)


def _save_targets(options, targets):
    write_json(targets, 'targets', options.mutants)


def _create_hunor_options(options, target):
    o = copy.copy(options)
    o.mutants = os.path.join(o.mutants, str(target['id']))
    o.output = o.mutants
    o.sut_class = target['class']
    o.no_compile = True

    return o


if __name__ == '__main__':
    main()
