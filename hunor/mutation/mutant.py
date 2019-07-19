import os

from hunor.utils import list_equal
from difflib import ndiff


class Result:

    def __init__(self):
        self.test_suites = {}


class Mutant:

    def __init__(self, mid, operator, original_symbol, replacement_symbol,
                 method, line_number, transformation, path, mutation=None):
        self.id = mid
        self.operator = operator
        self.original_symbol = original_symbol
        self.replacement_symbol = replacement_symbol
        self.method = method
        self.line_number = line_number
        self.transformation = transformation
        self.maybe_equivalent = False
        self.has_brother = False
        self.brothers = list()
        self.subsumes = list()
        self.subsumed_by = list()
        self.path = path
        self.result = Result()
        self.is_invalid = False
        self.label = mid
        self.statement_operator = None
        self.mutation = self.gen_label() if not mutation else mutation
        self.mutation_label = self.mutation

    def __str__(self):
        return '{0}#{1}'.format(self.operator, self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    def get_fail_tests(self):
        fail_tests = set()

        for test_suite in self.result.test_suites:
            fail_tests = fail_tests.union(
                self.result.test_suites[test_suite].fail_coverage_tests)

        return fail_tests

    def get_coverage_count(self):
        coverage_count = 0

        for test_suite in self.result.test_suites:
            coverage_count += self.result.test_suites[test_suite].coverage

        return coverage_count

    def is_brother(self, mutant, ignore_tests=None):
        fail_tests_a = self.get_fail_tests()
        fail_tests_b = mutant.get_fail_tests()

        if ignore_tests is not None:
            fail_tests_a = fail_tests_a.difference(ignore_tests)
            fail_tests_b = fail_tests_b.difference(ignore_tests)

        return (not self.is_invalid and not self.maybe_equivalent
                and (fail_tests_a.issubset(fail_tests_b)
                     and fail_tests_b.issubset(fail_tests_a)))

    def subsume(self, mutant, ignore_tests=None):
        fail_tests_a = self.get_fail_tests()
        fail_tests_b = mutant.get_fail_tests()

        if ignore_tests is not None:
            fail_tests_a = fail_tests_a.difference(ignore_tests)
            fail_tests_b = fail_tests_b.difference(ignore_tests)

        return (not self.is_invalid and not self.maybe_equivalent
                and fail_tests_a.issubset(fail_tests_b)
                and not self.is_brother(mutant))

    def is_subsumed_by(self, mutant, ignore_tests=None):
        fail_tests_a = self.get_fail_tests()
        fail_tests_b = mutant.get_fail_tests()

        if ignore_tests is not None:
            fail_tests_a = fail_tests_a.difference(ignore_tests)
            fail_tests_b = fail_tests_b.difference(ignore_tests)

        return (not self.is_invalid and not self.maybe_equivalent
                and fail_tests_b.issubset(fail_tests_a)
                and not self.is_brother(mutant))

    def subsuming_equal(self, mutant):
        return (list_equal(self.brothers, mutant.brothers)
                and list_equal(self.subsumes, mutant.subsumes)
                and list_equal(self.subsumed_by, mutant.subsumed_by))

    def to_dict(self):

        subsumes = []
        subsumed_by = []
        id_subsumes = []
        id_subsumed_by = []
        test_suites = {}

        brothers = [str(m.id) for m in self.brothers]

        for m in self.subsumes:
            if m.label != self.label and m.label not in subsumes:
                subsumes.append(m.label)

            if (m.id != self.id
                    and m.id not in id_subsumes
                    and m.id not in brothers):
                id_subsumes.append(m.id)

        for m in self.subsumed_by:
            if m.label != self.label and m.label not in subsumed_by:
                subsumed_by.append(m.label)

            if (m.id != self.id
                    and m.id not in id_subsumed_by
                    and m.id not in brothers):
                id_subsumed_by.append(m.id)

        for t in self.result.test_suites:
            test_suites[t] = self.result.test_suites[t].to_dict()

        return {
            'id': str(self.id),
            'operator': self.operator,
            'original_symbol': self.original_symbol,
            'replacement_symbol': self.replacement_symbol,
            'method': self.method,
            'line_number': self.line_number,
            'transformation': self.transformation.strip() if self.transformation
            else None,
            'maybe_equivalent': self.maybe_equivalent,
            'has_brother': self.has_brother,
            'brothers': brothers,
            'subsumes': subsumes,
            'subsumed_by': subsumed_by,
            'subsumes_id': id_subsumes,
            'subsumed_by_id': id_subsumed_by,
            'path': self.path.split(os.sep)[-2:],
            'is_invalid': self.is_invalid,
            'label': self.label,
            'test_suites': test_suites,
            'mutation': self.gen_label(),
            'is_redundant': self.is_redundant(),
            'belongs_to_minimal': self.belongs_to_minimal(),
            'is_useless': self.is_useless(),
            'mutation_label': self.mutation_label,
            'statement_operator': self.operator
        }

    def set_as_brother(self, brother):
        self.has_brother = True
        if brother not in self.brothers:
            self.brothers.append(brother)

        brother.has_brother = True
        if self not in brother.brothers:
            brother.brothers.append(self)

        all_brothers = set()
        all_brothers_mutation = set()

        for b in self.brothers:
            all_brothers.add(b.id)
            all_brothers_mutation.add(b.mutation)

        for b in brother.brothers:
            all_brothers.add(b.id)
            all_brothers_mutation.add(b.mutation)

        label = _create_label(all_brothers)

        self.label = label
        brother.label = label

        mutation_label = _create_label(all_brothers_mutation)

        self.mutation_label = mutation_label
        brother.mutation_label = mutation_label

    def is_redundant(self):
        return len(self.subsumed_by) > 0 or self.has_brother

    def belongs_to_minimal(self):
        return len(self.subsumed_by) == 0 and not self.maybe_equivalent

    def is_useless(self):
        return len(self.subsumed_by) > 0 or self.maybe_equivalent

    def statement(self):
        return self.transformation.split(' => ')[0].strip()

    def diff(self):
        diff = []
        transformation = self.transformation.split(' => ')
        original = transformation[0].strip().replace(' ', '')
        mutation = transformation[1].strip().replace(' ', '')
        for d in ndiff(original, mutation):
            if d[0] != ' ':
                diff.append([d[0], d[-1]])
        return diff

    def gen_label(self):
        transformation = self.transformation.split(' => ')

        ori_lhs, ori_rhs, ori_op = None, None, None
        mut_lhs, mut_rhs, mut_op = None, None, None

        if len(transformation) > 0:
            ori_lhs, ori_rhs, ori_op = _split_expression(transformation[0])

        if len(transformation) > 1:
            mut_lhs, mut_rhs, mut_op = _split_expression(transformation[1])

        self.statement_operator = ori_op
        label = self.id

        if self.operator == 'ROR':
            if mut_op is not None:
                label = '{0} {1}'.format('ROR', mut_op)
            else:
                label = '{0} {1}'.format('ROR', mut_lhs)
        elif self.operator == 'AORB':
            label = '{0} {1}'.format('AORB', mut_op)
        elif self.operator == 'COI':
            label = '{0} {1}'.format('COI', '!()')
        elif self.operator == 'CDL':
            label = '{0} {1}'.format(
                'CDL', _check_hand_side(mut_lhs, ori_lhs, ori_rhs))
        elif self.operator == 'VDL':
            label = '{0} {1}'.format(
                'VDL', _check_hand_side(mut_lhs, ori_lhs, ori_rhs))
        elif self.operator == 'ODL':
            label = '{0} {1}'.format(
                'ODL', _check_hand_side(mut_lhs, ori_lhs, ori_rhs))

        return label


def _check_hand_side(to_check, lhs, rhs):
    side = None

    if to_check == lhs:
        side = 'lhs'
    elif to_check == rhs:
        side = 'rhs'

    return side


def _split_expression(expression):

    two_char = ['==', '>=', '<=', '!=', '&&', '||']
    one_char = ['>', '<', '&', '|', '^', '+', '-', '*', '/', '%']

    exp_operator = None
    rhs = None

    for operator in two_char:
        if (operator in expression
                and not expression.startswith(operator)
                and not expression.endswith(operator)):
            exp_operator = operator

    if exp_operator is None:
        for operator in one_char:
            if (operator in expression
                    and not expression.startswith(operator)
                    and not expression.endswith(operator)):
                exp_operator = operator

    if exp_operator is not None:
        lhs = expression.split(exp_operator)[0].strip()
        rhs = expression.split(exp_operator)[1].strip()
    else:
        lhs = expression.strip()

    return lhs, rhs, exp_operator


def _create_label(brothers):
    return ', '.join(sorted(list(brothers)))