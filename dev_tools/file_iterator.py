#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This work was created by participants in the DataONE project, and is
# jointly copyrighted by participating institutions in DataONE. For
# more information on DataONE, see our web site at http://dataone.org.
#
#   Copyright 2009-2016 DataONE
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

import os
import fnmatch


DEFAULT_EXCLUDE_GLOB_LIST = [
  # Dirs
  'dist/', '*egg-info/', 'build/', 'generated/', '.git/', 'doc/', '.idea/',
  # Files
  '*~', '*.bak', '*.tmp', '*.pyc'
] # yapf: disable


def file_iter(
    path_list,
    include_glob_list=None,
    exclude_glob_list=None,
    recursive=True,
    ignore_invalid=False,
    default_excludes=True,
):
  """Resolve a list of file and dir paths to a list of file paths with
  optional filtering.

  This function is intended for use on a list of paths passed to a script on
  the command line.

  :param path_list: List of file- and dir paths. File paths are used
  directly and dirs are searched for files.

  :param include_glob_list:
  :param exclude_glob_list: Patterns ending with "/" are matched only against
  dir names. All other patterns are matched only against file names. If the
  include list contains any file patterns, files must match one or more of the
  patterns in order to be returned. If the include list contains any dir
  patterns, dirs must match one or more of the patterns in order for the
  recursive search to descend into them. The exclude list works in the same way
  except that matching files and dirs are excluded instead of included. If both
  include and exclude lists are specified, files and dirs must both match the
  include and not match the exclude patterns in order to be returned or
  descended into.

  :param recursive: Set to false to prevent subdirectories from being searched.
  Each dir to search must then be specified directly in path_list.

  :param ignore_invalid: True: Invalid paths in path_list are ignored. False
  (default): EnvironmentError is raised if any of the paths in {path_list} do not
  reference an existing file or dir.

  :param default_excludes: True: A list of glob patterns for files and dirs that
  should typically be ignored is added to any exclude patterns passed to the
  function. These include dirs such as .git and backup files, such as files
  appended with "~". False: No files or dirs are excluded by default.

  :return: File path iterator

  Notes:

  {path_list} does not accept glob patterns, as it's more convenient to let the
  shell expand glob patterns to directly specified files and dirs. E.g., to use
  a glob to select all .py files in a subdir, the command may be called with
  sub/dir/*.py, which the shell expands to a list of files, which are then
  passed to this function. The paths should be Unicode or UTF-8 strings. Tilde
  ("~") to home expansion is performed on the paths.

  The shell can also expand glob patterns to dir paths or a mix of file and
  dir paths.

  {include_glob_list} and {exclude_glob_list} are handy for filtering the files
  found in dir searches.

  Glob patterns are matched only against file and directory names, not the full
  paths.

  Paths passed directly in {path_list} are not filtered.

  The same file can be returned multiple times if {path_list} contains
  duplicated file paths or dir paths, or dir paths that implicitly include the
  same subdirs.

  Remember to escape the include and exclude glob patterns on the command line
  so that they're not expanded by the shell.

  Returns Unicode paths regardless of coding of {path_list} (unlike
  regular os.walk()).
  """
  include_glob_list = include_glob_list or []
  exclude_glob_list = exclude_glob_list or []

  if default_excludes:
    exclude_glob_list += DEFAULT_EXCLUDE_GLOB_LIST

  include_file_glob_list = [
    p for p in include_glob_list if not p.endswith(os.path.sep)
  ]
  exclude_file_glob_list = [
    p for p in exclude_glob_list if not p.endswith(os.path.sep)
  ]
  include_dir_glob_list = [
    p for p in include_glob_list if p.endswith(os.path.sep)
  ]
  exclude_dir_glob_list = [
    p for p in exclude_glob_list if p.endswith(os.path.sep)
  ]

  for path in path_list:
    path = os.path.expanduser(path)
    if not isinstance(path, unicode):
      path = path.decode('utf8')
    if not ignore_invalid:
      if not (os.path.isfile(path) or os.path.isdir(path)):
        raise EnvironmentError(0, 'Not a valid file or dir path', path)
    if os.path.isfile(path):
      file_name = os.path.split(path)[1]
      if not _is_filtered(
          file_name, include_file_glob_list, exclude_file_glob_list
      ):
        yield path
    if os.path.isdir(path):
      if recursive:
        file_path_iter = _filtered_walk(
          path, include_dir_glob_list, exclude_dir_glob_list
        )
      else:
        file_path_iter = os.listdir(path)
      for file_path in file_path_iter:
        file_name = os.path.split(file_path)[1]
        if not _is_filtered(
            file_name, include_file_glob_list, exclude_file_glob_list
        ):
          yield file_path


def _is_filtered(name, include_glob_list, exclude_glob_list):
  return (
    include_glob_list and
    not any(fnmatch.fnmatch(name, g)
            for g in include_glob_list) or exclude_glob_list and
    any(fnmatch.fnmatch(name, g) for g in exclude_glob_list)
  )


def _filtered_walk(root_dir_path, include_dir_glob_list, exclude_dir_glob_list):
  for dir_path, dir_list, file_list in os.walk(root_dir_path):
    dir_list[:] = [
      d for d in dir_list
      if not _is_filtered(
        os.path.split(d)[1] + u'/', include_dir_glob_list, exclude_dir_glob_list
      )
    ]
    for file_name in file_list:
      yield os.path.join(dir_path, file_name)