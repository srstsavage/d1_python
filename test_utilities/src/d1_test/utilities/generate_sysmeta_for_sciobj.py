# This work was created by participants in the DataONE project, and is
# jointly copyrighted by participating institutions in DataONE. For
# more information on DataONE, see our web site at http://dataone.org.
#
#   Copyright 2009-2017 DataONE
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
"""Generates system metadata for a file.

e.g.:

export OBJECT=/some/file
generate_sysmeta.py -f $OBJECT \
                    -i "Some_Identifier" \
                    -s "CN=My Name,O=Google,C=US,DC=cilogon,DC=org" \
                    -t "some_format"

"""
import logging
import sys
import urllib.request
import xml.etree

import d1_common.date_time
import d1_common.types.dataoneTypes_v1
import d1_common.utils.ulog

# from lxml import etree

# flake8: noqa: F403


log = logging.getLogger(__name__)
d1_common.utils.ulog.setup(is_debug=True)


def getObjectFormatFromID(fmtid, default="application/octet-stream"):
    """Returns an ObjectFormat instance given a format id."""
    formatlistURL = (
        "https://repository.dataone.org/software/cicore/trunk/d1_common_java/src/"
        "main/resources/org/dataone/service/resources/config/v1/"
        "objectFormatList.xml"
    )
    doc = urllib.request.urlopen(formatlistURL).read()
    formats = d1_common.types.dataoneTypes_v1.CreateFromDocument(doc)
    for format in formats.objectFormat:
        if format.formatId == fmtid:
            logging.info("Found format for %s" % fmtid)
            return format
    for format in formats:
        if format.formatId == default:
            return format
    return None


def processDoc(fname, options={}):
    """Generate system metadata XML for file fname."""
    # add script arguments to a comment in the generated metadata
    tnow = d1_common.date_time.local_now_iso()
    comment = xml.etree.Comment(
        "Warning: This file was generated by an automated process. "
        "Manual edits may be overwritten without further warning.\n"
        "timestamp:: %s\n"
        "created_with:: generate_sysmeta.py\n"
        "arguments:: %s\n"
        "command:: generate_sysmeta.py %s\n"
        % (tnow, repr(sys.argv[1:]), " ".join(sys.argv[1:]))
    )
    sysm = systemmetadata.generate_from_file(fname, options)
    root = xml.etree.fromstring(sysm.toxml("utf-8"))
    root.insert(0, comment)
    pxml = xml.etree.tostring(
        root, pretty_print=True, encoding="utf-8", xml_declaration=True
    )
    return pxml
