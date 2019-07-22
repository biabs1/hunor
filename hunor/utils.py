import os
import re
import json


def get_java_files(path):
    return get_files(path, ext='.java')


def get_class_files(path):
    return get_files(path, ext='.class')


def get_files(path, root='', ext=None):
    files = []

    for node in os.listdir(path):
        node_path = os.path.join(path, node)
        if os.path.isdir(node_path):
            files += get_files(node_path, os.path.join(root, node), ext)
        elif ext is None or os.path.splitext(node_path)[1] == ext:
            files.append(os.path.join(root, node))

    return files


def class_to_dir(class_file, only_package=False):
    if only_package:
        return os.sep.join(class_file.split('.')[0:-1])
    return class_file.replace('.', os.sep)


def generate_classpath(paths):
    return os.pathsep.join(paths)


def qualified_class_to_file(qualified_class, ext='.java'):
    return qualified_class.replace('.', os.sep) + ext


def config(path):
    with open(path, 'r') as c:
        return json.loads(c.read())


def write_json(obj, name, output_dir=''):
    with open(os.path.join(output_dir, name + '.json'), 'w') as f:
        f.write(json.dumps(obj, indent=2))
        f.close()


def read_json(path):
    return config(path)


def list_to_set(l):
    s = set()
    for e in l:
        s.add(e)
    return s


def list_equal(a, b):
    return set_equal(list_to_set(a), list_to_set(b))


def set_equal(a, b):
    return a.issubset(b) and b.issubset(a)


def sort_files(files):
    return sorted(files, key=lambda x: (
        int(0 if re.sub(r'[^0-9]+', '', x) == ''
            else re.sub(r'[^0-9]+', '', x)), x))
