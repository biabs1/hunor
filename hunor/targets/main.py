import os
import json

import javalang
import javalang.tree as tree

from javalang.tree import Node
from javalang.parser import JavaSyntaxError

from hunor.utils import get_java_files


PROJECT_DIR = os.path.join('../../example/relational/src/main/java')

RELATIONAL_OPERATORS = ['>', '==', '<', '>=', '<=', '!=']
ARITHMETIC_OPERATORS = ['+', '-', '*', '/', '%']
LOGICAL_OPERATORS = ['&&', '||']
BINARY_LOGICAL_OPERATORS = ['|', '^', '&']
ALL_OPERATORS = (RELATIONAL_OPERATORS + ARITHMETIC_OPERATORS + LOGICAL_OPERATORS
                 + BINARY_LOGICAL_OPERATORS)
ALLOWED_PARAM_TYPES = [
    'byte', 'Byte',
    'short', 'Short',
    'int', 'Integer',
    'long', 'Long',
    'float', 'Float',
    'double', 'Double',
    'char', 'Char',
    'String'
]


def main():
    source_dir = PROJECT_DIR
    files = get_java_files(source_dir)
    targets = []

    for file in files:
        targets += get_targets(source_dir, file, len(targets))

    write_config_json(targets)


def get_targets(source_dir, file, count=0):
    targets = []

    if os.path.exists(os.path.join(source_dir, file)):
        with open(os.path.join(source_dir, file), 'r') as f:
            try:
                ast = javalang.parse.parse(f.read())
            except JavaSyntaxError:
                return targets
            finally:
                f.close()

        for _, clazz in ast.filter(tree.ClassDeclaration):
            package_name = ast.package.name if ast.package else None

            if package_name:
                class_name = '.'.join([package_name, clazz.name])
            else:
                class_name = clazz.name

            for _, method in clazz.filter(tree.MethodDeclaration):

                has_allowed_parameters = True

                for parameter in method.parameters:
                    if isinstance(parameter.type, tree.BasicType):
                        if parameter.type.name not in ALLOWED_PARAM_TYPES:
                            has_allowed_parameters = False
                    elif isinstance(parameter.type, tree.ReferenceType):
                        t = parameter.type.sub_type
                        while t:
                            if (t.sub_type is None
                                    and t.name not in ALLOWED_PARAM_TYPES):
                                has_allowed_parameters = False
                            t = t.sub_type

                if has_allowed_parameters:
                    method_name = method.name
                    method_params = ','.join([p.type.name for p in
                                             method.parameters])
                    method_type = method.return_type

                    if method_type is None:
                        method_type = 'void'
                    else:
                        method_type = method_type.name

                    method_prototype = '{0}({1})'.format(method_name,
                                                         method_params)

                    for path, node in method.filter(tree.BinaryOperation):
                        operandr = None
                        operandl = None

                        if isinstance(node.operandl, tree.MemberReference):
                            if node.operandl.qualifier:
                                operandl = '.'.join([node.operandl.qualifier,
                                                     node.operandl.member])
                            else:
                                operandl = node.operandl.member
                        elif (isinstance(node.operandl, tree.Literal)
                              and not str(node.operandl.value).startswith('"')):
                            operandl = node.operandl.value
                        elif (isinstance(node.operandl, tree.This)
                              and len(node.operandl.selectors) == 1
                              and isinstance(node.operandl.selectors[0],
                                             tree.MemberReference)):
                            operandl = '.'.join([
                                'this',
                                str(node.operandl.selectors[0].member)])
                        elif isinstance(node.operandl, tree.MethodInvocation):
                            operandl = _method_invocation_to_str(node.operandl)

                        if isinstance(node.operandr, tree.MemberReference):
                            if node.operandr.qualifier:
                                operandr = '.'.join([node.operandr.qualifier,
                                                     node.operandr.member])
                            else:
                                operandr = node.operandr.member
                        elif (isinstance(node.operandr, tree.Literal)
                              and not str(node.operandr.value).startswith('"')):
                            operandr = node.operandr.value
                        elif (isinstance(node.operandr, tree.This)
                              and len(node.operandr.selectors) == 1
                              and isinstance(node.operandr.selectors[0],
                                             tree.MemberReference)):
                            operandr = '.'.join([
                                'this',
                                str(node.operandr.selectors[0].member)])
                        elif isinstance(node.operandr, tree.MethodInvocation):
                            operandr = _method_invocation_to_str(node.operandr)

                        if (node.operator in ALL_OPERATORS and
                                operandl is not None and operandr is not None):

                            context = [str(p) for p in path
                                       if not isinstance(p, list)] + [str(node)]

                            context_full = _path_to_context_full(path)
                            method_ast = _method_ast_with_id(method)

                            statement = '{0} {1} {2}'.format(
                                operandl, node.operator, operandr)

                            operator_kind = None

                            if node.operator in ARITHMETIC_OPERATORS:
                                operator_kind = 'ArithmeticOperator'
                            elif node.operator in RELATIONAL_OPERATORS:
                                operator_kind = 'RelationalOperator'
                            elif node.operator in LOGICAL_OPERATORS:
                                operator_kind = 'LogicalOperator'
                            elif node.operator in BINARY_LOGICAL_OPERATORS:
                                operator_kind = 'BinaryLogicalOperator'

                            statement_nodes = '{0} {1} {2}'.format(
                                str(node.operandl), operator_kind,
                                str(node.operandr)
                            )

                            operand_nodes = '{0} {1} {2}'.format(
                                str(node.operandl), node.operator,
                                str(node.operandr)
                            )

                            targets.append({
                                'id': count,
                                'ignore': False,
                                'class': class_name,
                                'method': method_prototype,
                                'type_method': '{0}_{1}'.format(
                                    method_type, method_prototype),
                                'line': node.operandl.position[0],
                                'column': node.operandl.position[1],
                                'statement': statement.strip(),
                                'statement_nodes': statement_nodes,
                                'context': context,
                                'context_full': context_full,
                                'method_ast': method_ast,
                                'operand_nodes': operand_nodes,
                                'operator_kind': operator_kind,
                                'operator': node.operator
                            })
                            count += 1

    targets = clean_ambiguous(targets)
    return targets


def clean_ambiguous(targets):
    clean = []
    if len(targets) > 0:
        initial_id = targets[0]['id']

        for a in targets:
            ambiguous = False
            for b in targets:
                if (a['id'] != b['id']
                   and a['class'] == b['class']
                   and a['type_method'] == b['type_method']
                   and a['line'] == b['line']
                   and a['statement'] == b['statement']):
                    ambiguous = True
                    break
            if not ambiguous:
                clean.append(a)

        count = initial_id
        for c in clean:
            c['id'] = count
            count += 1

    return clean


def write_config_json(targets, output_dir=''):
    with open(os.path.join(output_dir, 'targets.json'), 'w') as f:
        config = {'targets': targets}

        f.write(json.dumps(config, indent=2))
        f.close()


def _path_to_context_full(path):
    ast = []
    for p in path:
        ast.append({id(p): str(p)} if not isinstance(p, list)
                   else _path_to_context_full(p))
    return ast


if __name__ == '__main__':
    main()


def _get_attrs(node):
    attrs = {}
    if isinstance(node, Node):
        names = node.attrs
        for name in names:
            attrs[name] = str(node.__getattribute__(name))
    return attrs


def _method_ast_with_id(node):
    d = []

    for child in node.children[-1]:
        d.append({
            'id': id(child),
            'name': str(child),
            'attrs': _get_attrs(child),
            'children': _ast_with_id(child)
        })

    return d


def _method_ast(node):
    d = []

    for child in node.children[-1]:
        d.append({
            'name': str(child),
            'attrs': _get_attrs(child),
            'children': _ast(child)
        })

    return d


def _ast_with_id(node):
    d = []

    if isinstance(node, Node):
        for child in node.children:
            if isinstance(child, Node):
                d.append({
                    'id': id(child),
                    'name': str(child),
                    'attrs': _get_attrs(child),
                    'children': _ast_with_id(child)
                })
            elif isinstance(child, (list, tuple)):
                for c in child:
                    d.append({
                        'id': id(c),
                        'name': str(c),
                        'attrs': _get_attrs(c),
                        'children': _ast_with_id(c)
                    })
    return d


def _ast(node):
    d = []

    if isinstance(node, Node):
        for child in node.children:
            if isinstance(child, Node):
                d.append({
                    'name': str(child),
                    'attrs': _get_attrs(child),
                    'children': _ast(child)
                })
            elif isinstance(child, (list, tuple)):
                for c in child:
                    d.append({
                        'name': str(c),
                        'attrs': _get_attrs(c),
                        'children': _ast(c)
                    })
    return d


def _method_invocation_to_str(method_invocation):
    call = ''
    if method_invocation.qualifier:
        call = method_invocation.qualifier + '.'
    call += method_invocation.member + '( '

    arguments = []

    for argument in method_invocation.arguments:
        arg = ''
        if isinstance(argument, tree.MemberReference):
            if argument.qualifier:
                arg = '.'.join([argument.qualifier,
                                argument.member])
            else:
                arg = argument.member
        elif isinstance(argument, tree.Literal):
            arg = argument.value

        arguments.append(arg)

    call += ', '.join(arguments) + ' )'

    return call
