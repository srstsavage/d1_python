"""
Generates system metadata for a file.

e.g.:

export OBJECT=/some/file
generate_sysmeta.py -f $OBJECT \
                    -i "Some_Identifier" \
                    -s "CN=My Name,O=Google,C=US,DC=cilogon,DC=org" \
                    -t "some_format"

"""

from __future__ import absolute_import
from __future__ import print_function

import datetime
import logging
import optparse
import os.path
import sys
import urllib2

from d1_instance_generator import systemmetadata

import d1_common.types.dataoneTypes_v1 as dataoneTypes_v1

#from lxml import etree

# flake8: noqa: F403


def getObjectFormatFromID(fmtid, default='application/octet-stream'):
  """Returns an ObjectFormat instance given a format id
  """
  formatlistURL = (
    'https://repository.dataone.org/software/cicore/trunk/d1_common_java/src/'
    'main/resources/org/dataone/service/resources/config/v1/'
    'objectFormatList.xml'
  )
  doc = urllib2.urlopen(formatlistURL).read()
  formats = dataoneTypes_v1.CreateFromDocument(doc)
  for format in formats.objectFormat:
    if format.formatId == fmtid:
      logging.info("Found format for %s" % fmtid)
      return format
  for format in formats:
    if format.formatId == default:
      return format
  return None


def processDoc(fname, options={}):
  """Generate system metadata XML for file fname
  """
  #add script arguments to a comment in the generated metadata
  tnow = datetime.datetime.utcnow().isoformat()
  comment = etree.Comment(
    'Warning: This file was generated by an automated process. '
    'Manual edits may be overwritten without further warning.\n'
    'timestamp:: %s\n'
    'created_with:: generate_sysmeta.py\n'
    'arguments:: %s\n'
    'command:: generate_sysmeta.py %s\n' %
    (tnow, repr(sys.argv[1:]), " ".join(sys.argv[1:]))
  )
  sysm = systemmetadata.generate_from_file(fname, options)
  root = etree.fromstring(sysm.toxml('utf-8'))
  root.insert(0, comment)
  pxml = etree.tostring(
    root, pretty_print=True, encoding='UTF-8', xml_declaration=True
  )
  return pxml


if __name__ == '__main__':
  parser = optparse.OptionParser()
  parser.add_option(
    '-f', '--fname', dest='fname', action='store', type='string', default=None,
    help='File name of target object'
  )
  parser.add_option(
    '-i', '--id', dest='identifier', action='store', type='string',
    default=None, help='Identifier of target object'
  )
  parser.add_option(
    '-t', '--format', dest='format', action='store', type='string',
    default='application/octet-stream', help='Object format ID of target object'
  )
  parser.add_option(
    '-s', '--submitter', dest='submitter', action='store', type='string',
    default='dataone_integration_test_user',
    help='Subject of the submitter [default: %default].'
  )
  parser.add_option(
    '-r', '--rights', dest='rightsHolder', action='store', type='string',
    default=None,
    help='Subject of the object rights holder, defaults to submitter.'
  )
  parser.add_option(
    '-o', '--origin', dest='originMemberNode', action='store', type='string',
    default='test_documents',
    help='Origin member node identifier [default: %default].'
  )
  parser.add_option(
    '-n', "--replicas", dest="numberReplicas", type="int", default=3,
    help="Number of replicas requested."
  )
  parser.add_option(
    '-l', '--loglevel', dest='llevel', default=20, type='int',
    help='Reporting level: 10=debug, 20=Info, 30=Warning, '
    '40=Error, 50=Fatal [default: %default]'
  )
  (options, args) = parser.parse_args(sys.argv)
  if options.llevel not in [10, 20, 30, 40, 50]:
    options.llevel = 20
  logging.basicConfig(level=int(options.llevel))
  if options.fname is None:
    print('File name for object is required.')
    parser.print_help()
    sys.exit()
  if options.identifier is None:
    print('Identifier for object is required.')
    parser.print_help()
    sys.exit()
  if not os.path.exists(options.fname):
    print('File %s not found' % options.fname)
    parser.print_help()
    sys.exit()

  oopts = {}
  oopts['fname'] = options.fname
  oopts['identifier'] = options.identifier
  objectFormat = getObjectFormatFromID(options.format)
  oopts['formatId'] = objectFormat.formatId
  oopts['submitter'] = options.submitter
  if options.rightsHolder is None:
    oopts['rightsHolder'] = options.submitter
  else:
    oopts['rightsHolder'] = options.rightsHolder
  oopts['originMemberNode'] = options.originMemberNode
  oopts['authoritativeMemberNode'] = options.originMemberNode

  defrepl = dataoneTypes_v1.ReplicationPolicy()
  if options.numberReplicas == 0:
    defrepl.replicationAllowed = False
  else:
    defrepl.replicationAllowed = True
    defrepl.numberReplicas = options.numberReplicas
  oopts['replicationPolicy'] = defrepl

  defap = dataoneTypes_v1.AccessPolicy()
  ar = dataoneTypes_v1.AccessRule()
  ar.permission = [
    dataoneTypes_v1.Permission.read,
  ]
  ar.subject = [
    "public",
  ]
  defap.allow = [
    ar,
  ]
  ar = dataoneTypes_v1.AccessRule()
  ar.permission = [
    dataoneTypes_v1.Permission.write,
  ]
  ar.subject = [
    oopts['submitter'],
  ]
  defap.allow.append(ar)
  oopts['accessPolicy'] = defap

  logging.debug(str(oopts))

  print(processDoc(oopts['fname'], oopts))
  sys.exit()
