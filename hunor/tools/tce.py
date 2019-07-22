import os
import subprocess
import logging

from hunor.tools.soot import Soot

from hunor.utils import config
from hunor.utils import generate_classpath
from hunor.utils import class_to_dir

logger = logging.getLogger()


class TCE:

    def __init__(self, options, mvn_build, target):
        self.options = options
        self.target = target

        self.project_dir = os.path.abspath(
            os.sep.join(config(options.config_file)['source']))
        self.classes_dir = mvn_build.classes_dir

    def run_soot(self, mid="ORIGINAL"):
        override_file_dir = os.path.abspath(
            os.path.join(self.options.mutants, self.target['directory'], mid))

        with_override_file_classpath = generate_classpath([
            override_file_dir,
            self.classes_dir
        ])

        soot = Soot(self.project_dir, with_override_file_classpath)
        soot.exec(self.target['class'], os.path.join(override_file_dir, 'opt'),
                  jimple=False)

    def run(self, mutant):
        original_file = self.optimized_file()
        mutant_file = self.optimized_file(mutant.id)

        if not os.path.exists(original_file):
            self.run_soot()

        self.run_soot(mutant.id)

        return TCE._diff(original_file, mutant_file)

    @staticmethod
    def _diff(a, b):
        try:
            subprocess.check_output("diff {0} {1}".format(a, b), shell=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def optimized_file(self, mid="ORIGINAL"):
        return os.path.abspath(
            os.path.join(self.options.mutants, self.target['directory'], mid,
                         'opt', class_to_dir(self.target['class']) + '.class'))
