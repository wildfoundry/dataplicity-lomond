#!/usr/bin/env python

from setuptools import setup, find_packages

classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Programming Language :: Python',
    'License :: OSI Approved :: BSD License',
]

# http://bit.ly/2alyerp
with open('lomond/_version.py') as f:
    exec(f.read())

with open('README.md') as f:
    long_desc = f.read()

setup(
    name='lomond',
    version=__version__,
    description="Websocket Client Library",
    long_description=long_desc,
    author='WildFoundry',
    author_email='willmcgugan@gmail.com',
    url='https://www.dataplicity.com',
    platforms=['any'],
    packages=find_packages(),
    classifiers=classifiers,
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    install_requires=[

    ],
    zip_safe=True
)
