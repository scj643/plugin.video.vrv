#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
from setuptools import setup


README = ''
try:
    f = open('README.rst')
    README = f.read()
    f.close()
except:
    pass

REQUIRES = ['chardet']

if sys.version_info < (2, 7):
    REQUIRES.append('argparse')

setup(name='pyvtt',
      version='0.0.2',
      author='Guillem Cabrera',
      author_email='"Guillem Cabrera" <guillemcabrera@gmail.com>',
      packages=['pyvtt'],
      test_suite='tests',
      use_2to3=False,
      description = "WebVTT (.vtt) subtitle parser and writer",
      long_description=README,
      install_requires=REQUIRES,
      entry_points={'console_scripts': ['vtt = pyvtt.commands:main']},
      license="GPLv3",
      platforms=["Independent"],
      keywords="WebVTT subtitle",
      url="https://github.com/guillemcabrera/pyvtt",
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: GNU General Public License (GPL)",
          "Operating System :: OS Independent",
          "Programming Language :: Python",
          "Topic :: Multimedia :: Video",
          "Topic :: Software Development :: Libraries",
          "Topic :: Text Processing :: Markup"
      ]
)
