# _*_ coding: UTF-8 _*_

from setuptools import setup


def readme():
    with open('README.md') as f:
        return f.read()

test_requires = [
    'nose==1.3.7',
    'coverage==4.5.3',
    'rednose==1.3.0'
]
    
setup(
    name='hunor',
    description='The son of Nimrod',
    long_description=readme(),
    keywords='test mutant analysis equivalent',
    version='0.9.6',
    url='https://github.com/marcioaug/hunor',
    author='Marcio Augusto Guimarães',
    author_email='masg@ic.ufal.br',
    license='MIT',
    packages=[
        'hunor',
        'hunor.tools',
        'hunor.mutation',
        'hunor.db',
        'hunor.targets',
        'hunor.tools.bin'
    ],
    install_requires=[
        'argparse==1.4.0',
        'beautifulsoup4==4.6.0',
        'graphviz==0.8.3',
        'javalang==0.11.0',
        'peewee==3.7.1',
        'coloredlogs==10.0'
    ],
    test_suite='nose.collector',
    tests_require=test_requires,
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'hunor=hunor.main:main',
            'hunor-gen=hunor.mutation.generate:main',
            'hunor-pgen=hunor.mutation.genplugin:main',
            'hunor-eval=hunor.mutation.evaluation:main'
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Topic :: Test :: Mutation'
    ],
    python_requires='>=3',
    setup_requires=[

    ] + test_requires
)
