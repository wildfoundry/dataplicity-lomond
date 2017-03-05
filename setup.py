#!/usr/bin/env python

from setuptools import setup, find_packages

classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Programming Language :: Python',
]

# http://bit.ly/2alyerp
with open('ws/_version.py') as f:
    exec(f.read())

with open('README.md') as f:
    long_desc = f.read()

setup(
    name='ws',
    version=__version__,
    description="Websocket Client Library",
    long_description=long_desc,
    author='WildFoundry',
    author_email='willmcgugan@gmail.com',
    url='https://www.dataplicity.com',
    platforms=['any'],
    packages=find_packages(),
    classifiers=classifiers,

    # entry_points={
    #     "console_scripts": [
    #        'dataplicity = dataplicity.app:main'
    #     ]
    # },

    setup_requires=['pytest-runner'],
    tests_require=['pytest'],

    install_requires=[

    ],

    zip_safe=True
)
