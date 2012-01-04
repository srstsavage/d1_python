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
'''
Module d1_common.const
======================

:Synopsis: Provides system wide constants for the Python DataONE stack.
:Created: 2010-01-20
:Author: DataONE (Vieglais, Dahl)
'''

# Make contents of __init__ available.
import d1_common

#: :const: Version of this software
VERSION = d1_common.__version__

#: Maximum number of entries per list objects request
#: TODO: Retrieve this from the CN introspection
MAX_LISTOBJECTS = 1000

#: Default number of objects to retrieve in a list objects request
DEFAULT_LISTOBJECTS = 100

#: HTTP Response timeout in seconds, float.
#: TODO: retrieve this from D1 root
RESPONSE_TIMEOUT = 30.0

#: HTTP User Agent that this software is known as
USER_AGENT = 'pyd1/%s +http://dataone.org/' % VERSION

# The system wide default checksum algorithm.
DEFAULT_CHECKSUM_ALGORITHM = 'MD5'

# Note: Trailing slashes are important in the URLs.

#: The root of all DataONE.  Used to perform introspection on the system when
#: no other node information is provided.
URL_DATAONE_ROOT = 'http://cn.dataone.org/cn/'
#URL_DATAONE_ROOT = 'http://localhost:8000/cn/'

#: Path to append to target base for the object collection
#: TODO: retrieve this from D1 root
URL_OBJECT_LIST_PATH = 'object'

#: Path to append to target base for a specific object
#: TODO: retrieve this from D1 root
URL_OBJECT_PATH = 'object/'

#: Path to append to target base for System Metadata collection
#: TODO: retrieve this from D1 root
URL_SYSMETA_PATH = 'meta/'

#: Path to append to target base for the access log collection.
#: TODO: retrieve this from D1 root
URL_ACCESS_LOG_PATH = 'log'

#: Path to append to target base for the resolve call.
URL_RESOLVE_PATH = 'resolve/'

#: Path to append to target base for the node call.
URL_NODE_PATH = 'node/'

#: Path to append to target base for the checksum call.
URL_CHECKSUM_PATH = 'checksum/'

#: Path to append to target base for the delete call.
URL_DELETE_PATH = 'object/'

#: Path to the DataONE schema.
#: TODO: retrieve this from D1 root
SCHEMA_URL = 'https://repository.dataone.org/software/cicore/tags/D1_SCHEMA_0_6_3/dataoneTypes.xsd'

#: These HTTP response status codes are OK.
HTTP_STATUS_OK = [200, 300, 301, 302, 303, 307]

# Mimetypes.
MIMETYPE_XML = 'text/xml'
MIMETYPE_APP_XML = 'application/xml'
MIMETYPE_JSON = 'application/json'
MIMETYPE_CSV = 'text/csv'
MIMETYPE_RDF = 'application/rdf+xml'
MIMETYPE_HTML = 'text/html'
MIMETYPE_LOG = 'text/log'
MIMETYPE_TEXT = 'text/plain'
MIMETYPE_OCTETSTREAM = 'application/octet-stream'

# The default mimetype used by DataONE services.
DEFAULT_MIMETYPE = MIMETYPE_XML

DEFAULT_CHARSET = 'utf-8'

URL_PATHELEMENT_SAFE_CHARS = ":@$!()',~*&="

URL_QUERYELEMENT_SAFE_CHARS = ":;@$!()',~*/?"

AUTH_HEADER_NAME = 'Authorization'

# Symbolic subjects.
SUBJECT_VERIFIED = 'verifiedUser'
SUBJECT_AUTHENTICATED = 'authenticatedUser'
SUBJECT_PUBLIC = 'public'
