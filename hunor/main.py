#!/usr/bin/env python3
import os

from hunor.tools.java import Java
from hunor.tools.maven import Maven
from hunor.tools.junit import JUnit
from hunor.args import arg_parser, to_options
from hunor.tools.testsuite import generate_test_suites
from hunor.mutation.nimrod import equivalence_analysis
from hunor.mutation.subsuming import subsuming, create_dmsg, minimize
from hunor.utils import write_json


class Hunor:

    def __init__(self, options, using_target=False):
        self.options = options
        self.using_target = using_target

    def run(self):
        jdk = Java(self.options.java_home)

        classpath = Maven(
            jdk=jdk,
            maven_home=self.options.maven_home,
            no_compile=self.options.no_compile
        ).compile_project(self.options.source)

        junit = JUnit(
            jdk=jdk,
            sut_class=self.options.sut_class,
            classpath=classpath,
            source_dir=self.options.source
        )
        #
        # test_suites = generate_test_suites(
        #     jdk=jdk,
        #     classpath=classpath,
        #     config_file=self.options.config_file,
        #     sut_class=self.options.sut_class,
        #     output=self.options.output,
        #     is_randoop_disabled=self.options.is_randoop_disabled,
        #     is_evosuite_disabled=self.options.is_evosuite_disabled,
        #     project_dir=self.options.source,
        #     suites_evosuite=self.options.suites_evosuite,
        #     suites_randoop=self.options.suites_randoop,
        #     junit=junit
        # )

        from hunor.tools.mujava import MuJava
        from hunor.tools.evosuite_r import EvosuiteRegression
        from hunor.tools.testsuite import TestSuiteResult

        sut_class = self.options.sut_class
        mutants_dir = self.options.mutants

        mutants = MuJava(mutants_dir).read_log()
        test_suites = {}
        print("hoy")
        for i, m in enumerate(mutants):
            mutant = mutants[m]
            tests_src = os.path.join(mutants_dir, 'tests')
            for _ in range(10):
                suite = EvosuiteRegression(
                    jdk, classpath, tests_src, sut_class,
                    params=['-Dsearch_budget=10']).generate(mutant.path)
                print('end')

                test_suite = TestSuiteResult(
                    tid=suite.name,
                    source_dir=suite.source_dir,
                    classes_dir=suite.classes_dir,
                    classes=suite.test_classes,
                    prefix=suite.name
                )

                test_suites[suite.name] = test_suite

        mutants = equivalence_analysis(
            jdk=jdk,
            junit=junit,
            classpath=classpath,
            test_suites=test_suites,
            mutants=self.options.mutants,
            mutation_tool=self.options.mutation_tool,
            sut_class=self.options.sut_class,
            coverage_threshold=self.options.coverage_threshold,
            output=self.options.output,
            mutants_dir=self.options.mutants,
            using_target=self.using_target
        )

        if mutants is not None:
            subsuming_mutants = subsuming(
                mutants,
                coverage_threshold=self.options.coverage_threshold
            )

            if not self.options.is_minimal_testsuite_disabled:
                minimized, minimal_tests = minimize(
                    mutants,
                    coverage_threshold=self.options.coverage_threshold
                )

                write_json(minimized, 'subsuming_minimal_tests',
                           self.options.mutants)
                write_json(list(minimal_tests), 'minimal_tests',
                           self.options.mutants)

            create_dmsg(mutants=subsuming_mutants,
                        export_dir=self.options.output)

            mutants = subsuming(
                mutants,
                clean=False,
                coverage_threshold=self.options.coverage_threshold
            )

            mutants_dict = [mutants[m].to_dict() for m in mutants]

            write_json(mutants_dict, 'mutants',
                       self.options.mutants)
            write_json(subsuming_mutants, 'subsuming_mutants',
                       self.options.mutants)

            return mutants_dict, subsuming_mutants

        return {}, {}


def main():
    Hunor(to_options(arg_parser())).run()


if __name__ == '__main__':
    main()


