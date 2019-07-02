from peewee import *
from playhouse.sqlite_ext import JSONField

from hunor.mutation.mutant import Mutant as HunorMutant
from hunor.tools.testsuite import TestSuiteResult
from hunor.mutation.mutant import Result
from hunor.mutation.subsuming import *
from hunor.utils import write_json


database_proxy = Proxy()


class BaseModel(Model):
    class Meta:
        database = database_proxy


class Database:

    def __init__(self, database_dir):
        self.db = SqliteDatabase(database_dir)
        database_proxy.initialize(self.db)


class Target(BaseModel):
    tid = IntegerField(null=False)
    ignore = BooleanField(null=False, default=False)
    clazz = CharField(null=False)
    method = CharField(null=False)
    type_method = CharField(null=True)
    line = IntegerField(null=False)
    column = IntegerField(null=False)
    statement = CharField(null=True)
    statement_nodes = CharField(null=True)
    context = JSONField()
    context_full = JSONField()
    method_ast = JSONField()
    operand_nodes = CharField(null=True)
    operator_kind = CharField(null=True)
    operator = CharField(null=True)
    coverage = IntegerField(null=False)
    oid = IntegerField(null=True)
    target_class = CharField(null=True)
    target_repr = CharField(null=True)
    children = JSONField()
    directory = CharField(null=True)
    prefix_operator = BooleanField(null=False, default=False)

    def save_dmsg(self, output_dir, format='png'):
        mutants = self.mutants_to_hunor()
        create_dmsg(subsuming(mutants), export_dir=output_dir,
                    format=format, filename=self.tid)

    def get_dmsg(self):
        mutants = self.mutants_to_hunor()
        return dmsg_dot_elements(subsuming(mutants))

    def mutants_to_hunor(self):
        mutants = {}
        for m in self.mutants:
            mutants[m.mid] = to_hunor_mutant(m)
        return mutants

    def get_a_minimal_test_set(self, shuffle=True):
        mutants = {}
        for m in self.mutants:
            mutants[m.id] = to_hunor_mutant(m)
        _, minimal = minimize(mutants, shuffle_tests=shuffle)

        return minimal

    @staticmethod
    def find_all(coverage=0):
        return Target.select().where(Target.coverage >= coverage)

    @staticmethod
    def find_all_by_statement(statement, coverage=0):
        return Target.select().where(
            (Target.statement.contains(statement))
            & (Target.coverage >= coverage)
        )

    @staticmethod
    def find_all_by_statement_nodes(statement_nodes, coverage=0):
        return Target.select().where(
            (Target.statement_nodes.contains(statement_nodes))
            & (Target.coverage >= coverage)
        )

    @staticmethod
    def find_all_by_operator(operator, coverage=0):
        return Target.select().where(
            (Target.operator == operator)
            & (Target.coverage >= coverage)
        )

    @staticmethod
    def find_all_by_operator_kind(operator_kind, coverage=0):
        return Target.select().where(
            (Target.operator_kind == operator_kind)
            & (Target.coverage >= coverage)
        )

    @staticmethod
    def save_all_dmsg(targets, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for target in targets:
            target.save_dmsg(output_dir=output_dir)

    @staticmethod
    def save_all_dmsg_in_one(targets, output_dir, format='svg',
                             filename='all_dmsgs'):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        dots = []
        for target in targets:
            dots.append((target.tid, target.get_dmsg()))

        return multiple_dmsgs(dots, export_dir=output_dir, format=format,
                              filename=filename)


class Mutant(BaseModel):

    mid = CharField(null=False)
    operator = CharField(null=False)
    original_symbol = CharField(null=True)
    replacement_symbol = CharField(null=True)
    method = CharField(null=False)
    line_number = IntegerField(null=False)
    transformation = CharField(null=False)
    maybe_equivalent = BooleanField(null=False)
    has_brother = BooleanField(null=False)
    path = JSONField(null=True)
    is_invalid = BooleanField(null=False)
    label = CharField(null=True)
    mutation = CharField(null=True)
    is_redundant = BooleanField(null=False)
    belongs_to_minimal = BooleanField(null=False)
    is_useless = BooleanField(null=False)
    mutation_label = CharField(null=True)
    statement_operator = CharField(null=True)
    target = ForeignKeyField(Target, null=True, backref='mutants')

    def subsumes(self):
        return [s.subsumes for s in
                Subsumption.select().where(
                    Subsumption.subsumed_by == self)]

    def subsumed_by(self):
        return [s.subsumed_by for s in
                Subsumption.select().where(
                    Subsumption.subsumes == self)]

    def brothers(self):
        return [b.brother for b in
                Brotherhood.select().where(
                    Brotherhood.mutant == self)]

    @staticmethod
    def find_all():
        return Mutant.select()

    @staticmethod
    def find_all_by_target(target):
        return Mutant.select().where((Mutant.target == target))

    @staticmethod
    def is_redundant_in_targets_group_by_mutation(targets):
        return _group_by_dict(Mutant.select(
            Mutant.mutation,
            fn.COUNT(Mutant.id)
        ).where(
            (Mutant.target.in_(targets))
            & (Mutant.is_redundant == True)
        ).group_by(Mutant.mutation))

    @staticmethod
    def is_not_redundant_in_targets_group_by_mutation(targets):
        return _group_by_dict(Mutant.select(
            Mutant.mutation,
            fn.COUNT(Mutant.id)
        ).where(
            (Mutant.target.in_(targets))
            & (Mutant.is_redundant == False)
        ).group_by(Mutant.mutation))

    @staticmethod
    def belongs_to_minimal_in_targets_group_by_mutation(targets):
        return _group_by_dict(Mutant.select(
            Mutant.mutation,
            fn.COUNT(Mutant.id)
        ).where(
            (Mutant.target.in_(targets))
            & (Mutant.belongs_to_minimal == True)
        ).group_by(Mutant.mutation))

    @staticmethod
    def doesnt_belongs_to_minimal_in_targets_group_by_mutation(targets):
        return _group_by_dict(Mutant.select(
            Mutant.mutation,
            fn.COUNT(Mutant.id)
        ).where(
            (Mutant.target.in_(targets))
            & (Mutant.belongs_to_minimal == False)
        ).group_by(Mutant.mutation))

    @staticmethod
    def kdm_in_targets_group_by_mutation(targets):
        return _group_by_dict(Mutant.select(
            Mutant.mutation,
            fn.COUNT(Mutant.id)
        ).where(
            (Mutant.target.in_(targets))
            & (Mutant.belongs_to_minimal == True)
            & (Mutant.has_brother == False)
        ).group_by(Mutant.mutation))

    @staticmethod
    def kim_in_targets_group_by_mutation(targets):
        return _group_by_dict(Mutant.select(
            Mutant.mutation,
            fn.COUNT(Mutant.id)
        ).where(
            (Mutant.target.in_(targets))
            & (Mutant.belongs_to_minimal == True)
            & (Mutant.has_brother == True)
        ).group_by(Mutant.mutation))

    @staticmethod
    def kds_in_targets_group_by_mutation(targets):
        return _group_by_dict(Mutant.select(
            Mutant.mutation,
            fn.COUNT(Mutant.id)
        ).where(
            (Mutant.target.in_(targets))
            & (Mutant.belongs_to_minimal == False)
            & (Mutant.has_brother == False)
        ).group_by(Mutant.mutation))

    @staticmethod
    def kis_in_targets_group_by_mutation(targets):
        return _group_by_dict(Mutant.select(
            Mutant.mutation,
            fn.COUNT(Mutant.id)
        ).where(
            (Mutant.target.in_(targets))
            & (Mutant.belongs_to_minimal == False)
            & (Mutant.has_brother == True)
        ).group_by(Mutant.mutation))


def redundant_abstract(targets, output_dir=None):
    red = Mutant.is_redundant_in_targets_group_by_mutation(targets)
    not_red = Mutant.is_not_redundant_in_targets_group_by_mutation(targets)
    min = Mutant.belongs_to_minimal_in_targets_group_by_mutation(targets)
    not_min = Mutant.doesnt_belongs_to_minimal_in_targets_group_by_mutation(
        targets)

    abstract = {}
    total = _group_by_dict(
        Mutant.select(
            Mutant.mutation,
            fn.COUNT(Mutant.id)
        ).where(
            (Mutant.target.in_(targets))
        ).group_by(Mutant.mutation))

    def _percent(d, key):
        return '{0:.2f}'.format(d[key]/d['total'])

    for r in total:
        abstract[r] = {
            'redundant': red[r] if r in red.keys() else 0,
            'not_redundant': not_red[r] if r in not_red.keys() else 0,
            'dominant': min[r] if r in min.keys() else 0,
            'subsumed': not_min[r] if r in not_min.keys() else 0,
            'total': total[r]
        }

    if output_dir is not None:
        write_json(abstract, output_dir=output_dir, name='abstract')
        with open(os.path.join(output_dir, 'abstract.csv'), 'w') as csv:
            csv.write("{0},{1},{2},{3},{4},{5}\n".format(
                '', 'redundant', '%', 'subsumed', '%', 'total'
            ))
            for r in abstract:
                csv.write("{0},{1},{2},{3},{4},{5}\n".format(
                    r,
                    abstract[r]['redundant'],
                    _percent(abstract[r], 'redundant'),
                    abstract[r]['subsumed'],
                    _percent(abstract[r], 'subsumed'),
                    abstract[r]['total'],
                ))
            csv.close()

    return abstract


def state_abstract(targets, output_dir=None, filename='states',
                   file_format='csv'):
    kdm = Mutant.kdm_in_targets_group_by_mutation(targets)
    kim = Mutant.kim_in_targets_group_by_mutation(targets)
    kds = Mutant.kds_in_targets_group_by_mutation(targets)
    kis = Mutant.kis_in_targets_group_by_mutation(targets)

    abstract = {}
    total = _group_by_dict(
        Mutant.select(
            Mutant.mutation,
            fn.COUNT(Mutant.id)
        ).where(
            (Mutant.target.in_(targets))
        ).group_by(Mutant.mutation))

    for r in total:
        abstract[r] = {
            'kdm': kdm[r] if r in kdm.keys() else 0,
            'kim': kim[r] if r in kim.keys() else 0,
            'kds': kds[r] if r in kds.keys() else 0,
            'kis': kis[r] if r in kis.keys() else 0,
            'total': total[r]
        }

    if output_dir is not None:
        if file_format == 'csv':
            write_state_csv(abstract, output_dir, filename)
        elif file_format == 'tex':
            write_state_tex(abstract, output_dir, filename)

    return abstract


def sum_state_abstract(abstracts):
    abstract = {}
    for a in abstracts:
        for k in a:
            if k not in abstract.keys():
                abstract[k] = {
                    'kdm': 0,
                    'kim': 0,
                    'kds': 0,
                    'kis': 0,
                    'total': 0
                }

            abstract[k]['kdm'] += a[k]['kdm']
            abstract[k]['kim'] += a[k]['kim']
            abstract[k]['kds'] += a[k]['kds']
            abstract[k]['kis'] += a[k]['kis']
            abstract[k]['total'] += a[k]['total']

    return abstract


def _percent(d, key, decimal=True):
    p = d[key] / d['total']
    return '{0:.1f}'.format(p if decimal else p * 100).replace('.', ',')


def write_state_csv(abstract, output_dir, filename):
    write_json(abstract, output_dir=output_dir, name=filename)
    with open(os.path.join(output_dir, filename + '.csv'), 'w') as csv:
        csv.write("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9}\n".format(
            '', 'kdm', '%', 'kim', '%', 'kds', '%', 'kis', '%', 'total'
        ))
        for r in sort_state(abstract):
            r = r[0]
            csv.write("{0},{1},{2},{3},{4},{5},{6},{7},{8},{9}\n".format(
                r,
                abstract[r]['kdm'],
                _percent(abstract[r], 'kdm'),
                abstract[r]['kim'],
                _percent(abstract[r], 'kim'),
                abstract[r]['kds'],
                _percent(abstract[r], 'kds'),
                abstract[r]['kis'],
                _percent(abstract[r], 'kis'),
                abstract[r]['total'],
            ))
        csv.close()


def write_state_tex(abstract, output_dir, filename):
    write_json(abstract, output_dir=output_dir, name=filename)
    with open(os.path.join(output_dir, filename + '.tex'), 'w') as tex:
        tex.write('\\begin{tabular}{@{}lccccc@{}}\n')
        tex.write('\t\\toprule\n')
        tex.write('\t\\textbf{Mutante} & \\textbf{KDM} & \\textbf{KIM} '
                  '& \\textbf{KDS} & \\textbf{KIS} & \\textbf{Total}  \\\\\n')
        tex.write('\t\\midrule\n')
        for r in sort_state(abstract):
            r = r[0]
            tex.write('\t{0: <17}& {1: <13}& {2: <13}& {3: <13}'
                      '& {4: <13}& {5: < 15}\\\\\n'
                      ''.format(
                                r.replace('%', '\%'),
                                _percent(abstract[r], 'kdm', False) + '\\%',
                                _percent(abstract[r], 'kim', False) + '\\%',
                                _percent(abstract[r], 'kds', False) + '\\%',
                                _percent(abstract[r], 'kis', False) + '\\%',
                                abstract[r]['total']
            ))
        tex.write('\t\\bottomrule\n')
        tex.write('\\end{tabular}\n')
        tex.close()


def sort_state(abstract):
    return sorted(
        abstract.items(),
        key=lambda kv: (
            (kv[1]['kdm'] + kv[1]['kim']) / kv[1]['total'],
            1 - ((kv[1]['kds'] + kv[1]['kis']) / kv[1]['total'])
        ) if kv[1]['total'] > 0 else (0, 0),
        reverse=True
    )


class Brotherhood(BaseModel):
    mutant = ForeignKeyField(Mutant)
    brother = ForeignKeyField(Mutant)


class Subsumption(BaseModel):
    subsumes = ForeignKeyField(Mutant)
    subsumed_by = ForeignKeyField(Mutant)


def dict_to_mutant(d):
    mutant = Mutant()

    mutant.mid = d['id']
    mutant.operator = d['operator']
    mutant.original_symbol = d['original_symbol']
    mutant.replacement_symbol = d['replacement_symbol']
    mutant.method = d['method']
    mutant.line_number = d['line_number']
    mutant.transformation = d['transformation']
    mutant.maybe_equivalent = d['maybe_equivalent']
    mutant.has_brother = d['has_brother']
    mutant.path = d['path']
    mutant.is_invalid = d['is_invalid']
    mutant.label = d['label']
    mutant.mutation = d['mutation']
    mutant.is_redundant = d['is_redundant']
    mutant.belongs_to_minimal = d['belongs_to_minimal']
    mutant.is_useless = d['is_useless']
    mutant.mutation_label = d['mutation_label']
    mutant.statement_operator = d['statement_operator']

    return mutant


def _group_by_dict(query):
    group = {}
    result = query.tuples()

    for r in result:
        if isinstance(r, tuple):
            group[r[0]] = r[1]

    return group


def dict_to_target(d):
    target = Target()

    target.tid = d['id']
    target.ignore = d['ignore']
    target.clazz = d['class']
    target.method = d['method']
    target.type_method = d['type_method']
    target.line = d['line']
    target.column = d['column']
    target.statement = d['statement']
    target.statement_nodes = d['statement_nodes']
    target.context = d['context']
    target.context_full = d['context_full']
    target.method_ast = d['method_ast']
    target.operand_nodes = d['operand_nodes']
    target.operator_kind = d['operator_kind']
    target.operator = d['operator']
    target.oid = d['oid'] if 'oid' in d else None
    target.target_class = d['target_class'] if 'target_class' in d else None
    target.target_repr = d['target_repr'] if 'target_repr' in d else None
    target.children = d['children'] if 'children' in d else []
    target.directory = d['directory'] if 'directory' in d else None
    target.prefix_operator = (d['prefix_operator']
                              if 'prefix_operator' in d else False)

    return target


class TestSuite(BaseModel):
    name = CharField(null=False)
    coverage = IntegerField()
    tests_total = IntegerField()
    fail_tests_total = IntegerField()
    fail_tests = JSONField()
    coverage_tests = JSONField()
    fail_coverage_tests = JSONField()
    fail_coverage_tests_total = IntegerField()
    mutant = ForeignKeyField(Mutant, backref='test_suites')


def dict_to_test_suite(name, d):

    test_suite = TestSuite()

    test_suite.name = name
    test_suite.coverage = d['coverage']
    test_suite.tests_total = d['tests_total']
    test_suite.fail_tests_total = d['fail_tests_total']
    test_suite.fail_tests = d['fail_tests']
    test_suite.coverage_tests = d['coverage_tests']
    test_suite.fail_coverage_tests = d['fail_coverage_tests']
    test_suite.fail_coverage_tests_total = d['fail_coverage_tests_total']

    return test_suite


def to_hunor_mutant(mutant):

    hunor_mutant = HunorMutant(
        mid=mutant.mid,
        operator=mutant.operator,
        original_symbol=mutant.original_symbol,
        replacement_symbol=mutant.replacement_symbol,
        method=mutant.method,
        line_number=mutant.line_number,
        transformation=mutant.transformation,
        path=os.sep.join(mutant.path)
    )

    test_results = Result()
    test_results.test_suites = {}

    for t_s in mutant.test_suites:
        test_result = TestSuiteResult(t_s.name, None, None, None)
        test_result.coverage = t_s.coverage
        test_result.fail = t_s.fail_tests_total > 0
        test_result.tests_total = t_s.tests_total
        test_result.fail_tests_total = t_s.fail_tests_total
        test_result.fail_tests = set(t_s.fail_tests)
        test_result.coverage_tests = set(t_s.coverage_tests)

        test_results.test_suites[t_s.name] = test_result

    hunor_mutant.maybe_equivalent = mutant.maybe_equivalent
    hunor_mutant.has_brother = mutant.has_brother
    hunor_mutant.brothers = []
    hunor_mutant.subsumes = []
    hunor_mutant.subsumed_by = []
    hunor_mutant.result = test_results
    hunor_mutant.is_invalid = mutant.is_invalid
    hunor_mutant.label = mutant.label
    hunor_mutant.statement_operator = mutant.statement_operator
    hunor_mutant.mutation = mutant.mutation
    hunor_mutant.mutation_label = mutant.mutation

    return hunor_mutant
