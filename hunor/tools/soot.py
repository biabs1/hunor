from hunor.tools.java_factory import JavaFactory
from hunor.tools.bin import SOOT
from hunor.utils import generate_classpath

TIMEOUT = 30


class Soot:

    def __init__(self, cwd, classpath):
        self.java = JavaFactory.get_instance()
        self.cwd = cwd
        self.classpath = classpath

    def exec(self, class_file, dest_dir, jimple=True):

        params = (
            '-jar', SOOT,
            '-cp', generate_classpath([self.classpath, self.java.rt]),
            '-d', dest_dir,
            '-O', class_file
        )

        if jimple:
            params += ('-f', 'jimple')

        return self.java.exec_java(self.cwd, self.java.get_env(),
                                   TIMEOUT, *params)
