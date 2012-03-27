#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This work was created by participants in the DataONE project, and is
# jointly copyrighted by participating institutions in DataONE. For
# more information on DataONE, see our web site at http://dataone.org.
#
#   Copyright ${year}
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
:mod:`setup`
====================

:Synopsis: Create egg.
:Author: DataONE (Dahl)
"""

from setuptools import setup, find_packages
import d1_common

setup(
  name='DataONE_Common',
  version=d1_common.__version__,
  author='DataONE Project',
  author_email='developers@dataone.org',
  url='http://dataone.org',
  description='Contains functionality common to projects that interact with the DataONE infrastructure via Python',
  license='Apache License, Version 2.0',
  packages=find_packages(),

  # Dependencies that are available through PYPI / easy_install.
  install_requires=[
    'iso8601 >= 0.1',
    'pyxb >= 1.1.2',
  ],
  package_data={
    # If any package contains *.txt or *.rst files, include them:
    '': ['*.txt', '*.rst'],
  }
)
