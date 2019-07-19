
import os

PATH = os.path.dirname(os.path.abspath(__file__))

JUNIT = os.sep.join([PATH, 'junit-4.12.jar'])
HAMCREST = os.sep.join([PATH, 'hamcrest-core-1.3.jar'])
EVOSUITE = os.sep.join([PATH, 'evosuite-1.0.6.jar'])
EVOSUITE_RUNTIME = os.sep.join([PATH, 'evosuite-standalone-runtime-1.0.6.jar'])
JMOCKIT = os.sep.join([PATH, 'jmockit-1.40-marcio.1.jar'])
RANDOOP = os.sep.join([PATH, 'randoop-all-4.0.3.jar'])
SAFIRA = os.sep.join([PATH, 'safira.jar'])
MUJAVA = os.path.join(PATH, 'mujava.jar')
COMMONSIO = os.path.join(PATH, 'commons-io-2.4.jar')
OPENJAVA = os.path.join(PATH, 'openjava.jar')


__all__ = ['JUNIT', 'HAMCREST', 'EVOSUITE', 'EVOSUITE_RUNTIME',
           'JMOCKIT', 'RANDOOP', 'SAFIRA', 'MUJAVA', 'COMMONSIO',
           'OPENJAVA']
