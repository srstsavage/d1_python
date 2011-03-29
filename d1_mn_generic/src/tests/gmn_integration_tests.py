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
:mod:`gmn_integration_tests`
============================

:Synopsis:
  Integration testing of ITK and GMN.
  
:Warning:
  This test deletes any existing objects and event log records on the
  destination GMN instance.

:Details:  
  This test works by first putting the target GMN into a known state by deleting
  any existing objects and all event logs from the instance and then creating a
  set of test objects of which all object properties and exact contents are
  known. For each object, a set of fictitious events are stored in the event
  log. The test then runs through a series of tests where the GMN is queried,
  through the ITK, about all aspects of the object collection and the associated
  events and the results are compared with the known correct responses.

  GMN can handle storage of the object bytes itself ("managed" mode), or it can
  defer storage of the object bytes to another web server ("wrapped" mode). The
  mode is selectable on a per object basis. This test tests both managed and
  wrapped modes by running through all the tests twice, first registering the
  objects in managed mode and then in wrapped mode. For the wrapped mode tests
  to work, the test objects must be available on a web server. The location can
  be specified as a program argument.
  
:Created:
:Author: DataONE (dahl)
:Dependencies:
  - python 2.6
'''

# Stdlib.
import csv
import codecs
import datetime
import dateutil
import glob
import hashlib
import httplib
import json
import logging
import optparse
import os
import re
import stat
import StringIO
import sys
import time
import unittest
import urllib
import urlparse
import uuid
from xml.sax.saxutils import escape

# MN API.
try:
  #import d1_common.mime_multipart
  import d1_common.types.exceptions
  import d1_common.types.checksum_serialization
  import d1_common.types.objectlist_serialization
  import d1_common.util
  import d1_common.const
except ImportError, e:
  sys.stderr.write('Import error: {0}\n'.format(str(e)))
  sys.stderr.write('Try: svn co https://repository.dataone.org/software/cicore/trunk/api-common-python/src/d1_common\n')
  raise
try:
  import d1_client
  import d1_client.systemmetadata
  import d1_common.xml_compare
except ImportError, e:
  sys.stderr.write('Import error: {0}\n'.format(str(e)))
  sys.stderr.write('Try: svn co https://repository.dataone.org/software/cicore/trunk/itk/d1-python/src/d1_client\n')
  raise


import gmn_test_client

# Constants.

# Constants related to MN test object collection.
OBJECTS_TOTAL_DATA = 100
OBJECTS_UNIQUE_DATES = 99
OBJECTS_UNIQUE_DATE_AND_FORMAT_EML = 99
OBJECTS_PID_STARTSWITH_F = 5
OBJECTS_UNIQUE_DATE_AND_PID_STARTSWITH_F = 5
OBJECTS_CREATED_IN_90S = 32

# CONSTANTS RELATED TO LOG COLLECTION.
EVENTS_TOTAL = 554
EVENTS_READ = 198
EVENTS_UNIQUE_DATES = 351
EVENTS_UNIQUE_DATES_WITH_READ = 96
EVENTS_WITH_OBJECT_FORMAT_EML = 351
EVENTS_COUNT_OF_FIRST = 3

def log_setup():
  # Set up logging.
  # We output everything to both file and stdout.
  logging.getLogger('').setLevel(logging.DEBUG)
  formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s', '%y/%m/%d %H:%M:%S')
  file_logger = logging.FileHandler(os.path.splitext(__file__)[0] + '.log', 'a')
  file_logger.setFormatter(formatter)
  logging.getLogger('').addHandler(file_logger)
  console_logger = logging.StreamHandler(sys.stdout)
  console_logger.setFormatter(formatter)
  logging.getLogger('').addHandler(console_logger)
  
class GMNException(Exception):
  pass
import types
class TestSequenceFunctions(unittest.TestCase):
  def __init__(self, methodName='runTest'):
    unittest.TestCase.__init__(self, methodName)
    # Copy docstrings from the tests that are being called so that the unit
    # test framework can display the strings.
    for member_name in dir(self):
      member_obj = getattr(self, member_name)
      if callable(getattr(self, member_name)):
        m = re.match(r'test_\d{4}_(managed|wrapped)_(.*)', member_obj.__name__)
        if m:
          fb = getattr(self, m.group(2))
          member_obj.__func__.__doc__ = \
            m.group(1)[0].upper() + m.group(1)[1:] + ': ' + fb.__doc__

  def setUp(self):
    pass

  def assert_counts(self, object_list, start, count, total):
    self.assertEqual(object_list.start, start)
    self.assertEqual(object_list.count, count)
    self.assertEqual(object_list.total, total)
    self.assertEqual(len(object_list.objectInfo), count)
  
  def assert_response_headers(self, response):
    '''Required response headers are present.
    '''
    
    self.assertIn('Last-Modified', response)
    self.assertIn('Content-Length', response)
    self.assertIn('Content-Type', response)

  def assert_valid_date(self, date_str):
    self.assertTrue(datetime.datetime(*map(int, date_str.split('-'))))

  def find_valid_pid(self, client):
    '''Find the PID of an object that exists on the server.
    '''
    # Verify that there's at least one object on server.
    object_list = client.listObjects('<dummy token>')
    self.assertTrue(object_list.count > 0, 'No objects to perform test on')
    # Get the first PID listed. The list is in random order.
    return object_list.objectInfo[0].identifier.value()

  def get_object_info_by_identifer(self, pid):
    client = d1_client.client.DataOneClient(self.opts.gmn_url)
  
    # Get object collection.
    object_list = client.listObjects('<dummy token>')
    
    for o in object_list['objectInfo']:
      if o["identifier"].value() == pid:
        return o
  
    # Object not found
    assertTrue(False)

  def gen_sysmeta(self, pid, size, md5, now):
    return u'''<?xml version="1.0" encoding="UTF-8"?>
<D1:systemMetadata xmlns:D1="http://dataone.org/service/types/0.5.1">
  <identifier>{0}</identifier>
  <objectFormat>eml://ecoinformatics.org/eml-2.0.0</objectFormat>
  <size>{1}</size>
  <submitter>test</submitter>
  <rightsHolder>test</rightsHolder>
  <checksum algorithm="MD5">{2}</checksum>
  <dateUploaded>{3}</dateUploaded>
  <dateSysMetadataModified>{3}</dateSysMetadataModified>
  <originMemberNode>MN1</originMemberNode>
  <authoritativeMemberNode>MN1</authoritativeMemberNode>
</D1:systemMetadata>
'''.format(escape(pid), size, md5, datetime.datetime.isoformat(now))

  #
  # Tests that are run for both local and remote objects.
  #

  def A_delete_all_objects(self):
    '''Delete all objects.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    client.delete_all_objects()

  def B_object_collection_is_empty(self):
    '''Object collection is empty.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    # Get object collection.
    object_list = client.listObjects('<dummy token>')
    # Check header.
    self.assert_counts(object_list, 0, 0, 0)
  
  def C_create_objects(self):
    '''Populate MN with set of test objects.
    '''
    pass
  
  def D_object_collection_is_populated(self):
    '''Object collection is empty.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    # Get object collection.
    object_list = client.listObjects('<dummy token>',
                                     count=d1_common.const.MAX_LISTOBJECTS)
    # Check header.
    self.assert_counts(object_list, 0, OBJECTS_TOTAL_DATA, OBJECTS_TOTAL_DATA)

  def A_clear_event_log(self):
    '''Clear event log.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    client.delete_event_log()

  def event_log_is_empty(self):
    '''Event log is empty.
    '''
    '''Object collection is empty.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    logRecords = client.getLogRecords('<dummy token>', datetime.datetime(1800, 1, 1))
    self.assertEqual(len(logRecords.logEntry), 0)
  
  def inject_event_log(self):
    '''Inject a set of fictitious events for each object.
    '''
    csv_file = open('test_log.csv', 'rb')
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    client.inject_event_log(csv_file)

  def event_log_is_populated(self):
    '''Event log is populated.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    logRecords = client.getLogRecords('<dummy token>', datetime.datetime(1800, 1, 1))
    self.assertEqual(len(logRecords.logEntry), LOG_TOTAL)
    found = False
    for o in logRecords.logEntry:
      if o.identifier.value() == 'hdl:10255/dryad.654/mets.xml' and o.event == 'create': 
        found = True
        break
    self.assertTrue(found)
  
  def compare_byte_by_byte(self):
    '''Read set of test objects back from MN and do byte-by-byte comparison with local copies.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url, timeout=60)

    for sysmeta_path in sorted(glob.glob(os.path.join(self.opts.obj_path, '*.sysmeta'))):
      object_path = re.match(r'(.*)\.sysmeta', sysmeta_path).group(1)
      pid = urllib.unquote(os.path.basename(object_path))
      #sysmeta_str_disk = open(sysmeta_path, 'r').read()
      object_str_disk = open(object_path, 'r').read()
      #sysmeta_str_d1 = client.getSystemMetadata(pid).read()
      object_str_d1 = client.get('<dummy token>', pid).read(1024**2)
      #self.assertEqual(sysmeta_str_disk, sysmeta_str_d1)
      self.assertEqual(object_str_disk, object_str_d1)
      
 #Read objectList from MN and compare the values for each object with values
 #from sysmeta on disk.
 
  def object_properties(self):
    '''Read complete object collection and compare with values stored in local SysMeta files.
    '''
    # Get object collection.
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url, timeout=60)
    object_list = client.listObjects('<dummy token>',
                                     count=d1_common.const.MAX_LISTOBJECTS)
    
    # Loop through our local test objects.
    for sysmeta_path in sorted(glob.glob(os.path.join(self.opts.obj_path, '*.sysmeta'))):
      # Get name of corresponding object and check that it exists on disk.
      object_path = re.match(r'(.*)\.sysmeta', sysmeta_path).group(1)
      self.assertTrue(os.path.exists(object_path))
      # Get pid for object.
      pid = urllib.unquote(os.path.basename(object_path))
      # Get sysmeta xml for corresponding object from disk.
      sysmeta_file = open(sysmeta_path, 'r')
      sysmeta_obj = d1_client.systemmetadata.SystemMetadata(sysmeta_file)
  
      # Get corresponding object from objectList.
      found = False
      for object_info in object_list.objectInfo:
        if object_info.identifier.value() == sysmeta_obj.identifier:
          found = True
          break;
  
      self.assertTrue(found, 'Couldn\'t find object with pid "{0}"'.format(sysmeta_obj.identifier))
      
      self.assertEqual(object_info.identifier.value(), sysmeta_obj.identifier)
      self.assertEqual(object_info.objectFormat, sysmeta_obj.objectFormat)
      self.assertEqual(object_info.dateSysMetadataModified, sysmeta_obj.dateSysMetadataModified)
      self.assertEqual(object_info.size, sysmeta_obj.size)
      self.assertEqual(object_info.checksum.value(), sysmeta_obj.checksum)
      self.assertEqual(object_info.checksum.algorithm, sysmeta_obj.checksumAlgorithm)

  def slicing_1(self):
    '''Slicing: Starting at 0 and getting half of the available objects.
    '''
    object_cnt_half = OBJECTS_TOTAL_DATA / 2  
    # Starting at 0 and getting half of the available objects.
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    #client = d1_client.client.DataOneClient(self.opts.gmn_url)
    object_list = client.listObjects('<dummy token>', start=0,
                                     count=object_cnt_half)
    self.assert_counts(object_list, 0, object_cnt_half,
                       OBJECTS_TOTAL_DATA)
    
  def slicing_2(self):
    '''Slicing: Starting at object_cnt_half and requesting more objects
    than there are.
    '''
    object_cnt_half = OBJECTS_TOTAL_DATA / 2  
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    object_list = client.listObjects('<dummy token>', start=object_cnt_half,
                                     count=d1_common.const.MAX_LISTOBJECTS)
    self.assert_counts(object_list, object_cnt_half, object_cnt_half,
                       OBJECTS_TOTAL_DATA)
  
  def slicing_3(self):
    '''Slicing: Starting above number of objects that we have.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    object_list = client.listObjects('<dummy token>',
                                     start=OBJECTS_TOTAL_DATA * 2,
                                     count=1)
    self.assert_counts(object_list, OBJECTS_TOTAL_DATA * 2, 0,
                       OBJECTS_TOTAL_DATA)
    
  def slicing_4(self):
    '''Slicing: Requesting more than MAX_LISTOBJECTS should throw.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    object_cnt_half = OBJECTS_TOTAL_DATA / 2
    self.assertRaises(Exception, client.listObjects, '<dummy token>',
                      count=d1_common.const.MAX_LISTOBJECTS + 1)

  def date_range_1(self):
    '''Date range query: Get all objects from the 1990s.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
  
    object_list = client.listObjects('<dummy token>',
                                     count=d1_common.const.MAX_LISTOBJECTS,
                                     startTime=datetime.datetime(1990, 1, 1),
                                     endTime=datetime.datetime(1999, 12, 31))
    self.assert_counts(object_list, 0, OBJECTS_CREATED_IN_90S, OBJECTS_CREATED_IN_90S)
  
  
  def date_range_2(self):
    '''Date range query: Get first 10 objects from the 1990s.
    '''    
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
  
    object_list = client.listObjects('<dummy token>',
                                     start=0,
                                     count=10,
                                     startTime=datetime.datetime(1990, 1, 1),
                                     endTime=datetime.datetime(1999, 12, 31))
    self.assert_counts(object_list, 0, 10, OBJECTS_CREATED_IN_90S)
  
  def date_range_3(self):
    '''Date range query: Get 10 first objects from the 1990s, filtered by
    objectFormat.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
  
    object_list = client.listObjects('<dummy token>',
                                     start=0,
                                     count=10,
                                     startTime=datetime.datetime(1990, 1, 1),
                                     endTime=datetime.datetime(1999, 12, 31),
                                     objectFormat='eml://ecoinformatics.org/eml-2.0.0')
    self.assert_counts(object_list, 0, 10, 32)
  
  def date_range_4(self):
    '''Date range query: Get 10 first objects from non-existing date range.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
  
    object_list = client.listObjects('<dummy token>',
                                     start=0,                      
                                     count=10,
                                     startTime=datetime.datetime(2500, 1, 1),
                                     endTime=datetime.datetime(2500, 12, 31),
                                     objectFormat='eml://ecoinformatics.org/eml-2.0.0')
    self.assert_counts(object_list, 0, 0, 0)
  
  def get_object_count(self):
    '''Get object count.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
  
    object_list = client.listObjects('<dummy token>',
                                     start=0,
                                     count=0)
    self.assert_counts(object_list, 0, 0, OBJECTS_TOTAL_DATA)
  
  
  # /object/<pid>
  
  def get_object_by_invalid_pid(self):
    '''404 NotFound when attempting to get non-existing object /object/_invalid_pid_.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    self.assertRaises(d1_common.types.exceptions.NotFound, client.get,
                      '<dummy token>',
                      '_invalid_pid_')

  def get_object_by_valid_pid(self):
    '''Successful retrieval of valid object
    /object/valid_pid.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    response = client.get('<dummy token>', '10Dappend2.txt')
    # Todo: Verify that we got the right object.
  
  # Todo: Unicode tests.
  #def test_rest_call_object_by_pid_get_unicode(self):
  #  curl -X GET -H "Accept: application/json" http://127.0.0.1:8000/mn/object/unicode_document_%C7%8E%C7%8F%C7%90%C7%91%C7%92%C7%94%C7%95%C7%96%C7%97%C7%98%C7%99%C7%9A%C7%9B
  #  ?pid=*ǎǏǐǑǒǔǕǖǗǘǙǚǛ
  
  # /meta/<pid>
  
  def get_sysmeta_by_invalid_pid(self):
    '''404 NotFound when attempting to get non-existing SysMeta /meta/_invalid_pid_.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    self.assertRaises(d1_common.types.exceptions.NotFound,
                      client.getSystemMetadata,
                      '<dummy token>',
                      '_invalid_pid_')

  def get_sysmeta_by_valid_pid(self):
    '''Successful retrieval of valid object /meta/valid_pid.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    response = client.getSystemMetadata('<dummy token>', '10Dappend2.txt')
    self.assertTrue(response)
  
  def xml_validation(self):
    '''Returned XML document validates against the ObjectList schema.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    response = client.listObjectsResponse('<dummy token>',
                                          count=d1_common.const.MAX_LISTOBJECTS) 
    xml_doc = response.read()
    d1_common.util.validate_xml(xml_doc)

  def pxby_objectlist_xml(self):
    '''Serialization: ObjectList -> XML.
    '''
    xml_doc = open('test_objectlist.xml').read()
    object_list_1 = d1_common.types.objectlist_serialization.ObjectList()
    object_list_1.deserialize(xml_doc, 'text/xml')
    doc, content_type = object_list_1.serialize('text/xml')
    
    object_list_2 = d1_common.types.objectlist_serialization.ObjectList()
    object_list_2.deserialize(doc, 'text/xml')
    xml_doc_out, content_type = object_list_2.serialize('text/xml')
    d1_common.xml_compare.assert_xml_equal(xml_doc, xml_doc_out)
  
  def pxby_objectlist_json(self):
    '''Serialization: ObjectList -> JSON.
    '''
    xml_doc = open('test_objectlist.xml').read()
    object_list_1 = d1_common.types.objectlist_serialization.ObjectList()
    object_list_1.deserialize(xml_doc, 'text/xml')
    doc, content_type = object_list_1.serialize(d1_common.const.MIMETYPE_JSON)
    
    object_list_2 = d1_common.types.objectlist_serialization.ObjectList()
    object_list_2.deserialize(doc, d1_common.const.MIMETYPE_JSON)
    xml_doc_out, content_type = object_list_2.serialize('text/xml')
    
    d1_common.xml_compare.assert_xml_equal(xml_doc, xml_doc_out)
  
#  def pxby_objectlist_rdf_xml(self):
#    '''Serialization: ObjectList -> RDF XML.
#    '''
#    xml_doc = open('test.xml').read()
#    object_list_1 = d1_common.types.objectlist_serialization.ObjectList()
#    object_list_1.deserialize(xml_doc, 'text/xml')
#    doc, content_type = object_list_1.serialize('application/rdf+xml')
    
  def pxby_objectlist_csv(self):
    '''Serialization: ObjectList -> CSV.
    '''
    xml_doc = open('test_objectlist.xml').read()
    object_list_1 = d1_common.types.objectlist_serialization.ObjectList()
    object_list_1.deserialize(xml_doc, 'text/xml')
    doc, content_type = object_list_1.serialize(d1_common.const.MIMETYPE_CSV)
  
    object_list_2 = d1_common.types.objectlist_serialization.ObjectList()
    object_list_2.deserialize(doc, d1_common.const.MIMETYPE_CSV)
    xml_doc_out, content_type = object_list_2.serialize('text/xml')
    
    # This assert currently does not pass because there is a slight difference
    # in the ISO1601 rendering of the timestamp.
    #d1_common.xml_compare.assert_xml_equal(xml_doc, xml_doc_out)
  
  #
  # Monitor Objects
  #
  
  def monitor_object_cumulative_no_filter(self):
    '''Monitor Objects: Cumulative, no filter.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    monitor_list = client.getObjectStatistics('<dummy token>')
    self.assertEqual(len(monitor_list.monitorInfo), 1)
    self.assert_valid_date(str(monitor_list.monitorInfo[0].date))
    self.assertEqual(monitor_list.monitorInfo[0].count, OBJECTS_TOTAL_DATA)

  def monitor_object_cumulative_filter_by_time(self):
    '''Monitor Objects: Cumulative, filter by object creation time.
    '''
    # TODO: Story #1424
    pass
  
  def monitor_object_cumulative_filter_by_format(self):
    '''Monitor Objects: Cumulative, filter by object format.
    '''
    # TODO: Test set currently contains only one format. Create
    # some more formats so this can be tested properly.
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    monitor_list = client.getObjectStatistics('<dummy token>',
                                              format='eml://ecoinformatics.org/eml-2.0.0')
    self.assertEqual(len(monitor_list.monitorInfo), 1)
    self.assert_valid_date(str(monitor_list.monitorInfo[0].date))
    self.assertEqual(monitor_list.monitorInfo[0].count, OBJECTS_TOTAL_DATA)

  def monitor_object_cumulative_filter_by_time_and_format(self):
    '''Monitor Objects: Cumulative, filter by time and format.
    '''
    # TODO: Story #1424
    pass

  def monitor_object_cumulative_filter_by_pid(self):
    '''Monitor Objects: Cumulative, filter by object PID.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    monitor_list = client.getObjectStatistics('<dummy token>', pid='f*')
    self.assertEqual(len(monitor_list.monitorInfo), 1)
    self.assert_valid_date(str(monitor_list.monitorInfo[0].date))
    self.assertEqual(monitor_list.monitorInfo[0].count, OBJECTS_PID_STARTSWITH_F)

  def monitor_object_daily_no_filter(self):
    '''Monitor Objects: Daily, no filter.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    monitor_list = client.getObjectStatistics('<dummy token>', day=True)
    self.assertEqual(len(monitor_list.monitorInfo), OBJECTS_UNIQUE_DATES)
    self.assert_valid_date(str(monitor_list.monitorInfo[0].date))
    found_date = False
    for monitor_info in monitor_list.monitorInfo:
      if str(monitor_info.date) == '1982-08-17':
        found_date = True
        self.assertEqual(monitor_info.count, 2)
    self.assertTrue(found_date)
    
  def monitor_object_daily_filter_by_time(self):
    '''Monitor Objects: Daily, filter by object creation time.
    '''
    # TODO: Story #1424: Change to use the standard ISO 8601 time interval notation.
    pass

  def monitor_object_daily_filter_by_format(self):
    '''Monitor Objects: Daily, filter by object format.
    '''
    # TODO: Test set currently contains only one format. Create
    # some more formats so this can be tested properly.
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    monitor_list = client.getObjectStatistics('<dummy token>',
                                              format='eml://ecoinformatics.org/eml-2.0.0',
                                              day=True)
    self.assertEqual(len(monitor_list.monitorInfo), OBJECTS_UNIQUE_DATE_AND_FORMAT_EML)
    self.assert_valid_date(str(monitor_list.monitorInfo[0].date))
    self.assertEqual(monitor_list.monitorInfo[0].count, 1)

  def monitor_object_daily_filter_by_time_and_format(self):
    '''Monitor Objects: Daily, filter by time and format.
    '''
    # TODO: Story #1424
    pass

  def monitor_object_daily_filter_by_pid(self):
    '''Monitor Objects: Daily, filter by object PID.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    monitor_list = client.getObjectStatistics('<dummy token>', pid='f*', day=True)
    self.assertEqual(len(monitor_list.monitorInfo), OBJECTS_UNIQUE_DATE_AND_PID_STARTSWITH_F)
    self.assert_valid_date(str(monitor_list.monitorInfo[0].date))
    self.assertEqual(monitor_list.monitorInfo[0].count, 1)

  #
  # Monitor Events
  #
    
  def monitor_event_cumulative_no_filter(self):
    '''Monitor Events: Cumulative, no filter.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    monitor_list = client.getOperationStatistics('<dummy token>')
    self.assertEqual(len(monitor_list.monitorInfo), 1)
    self.assert_valid_date(str(monitor_list.monitorInfo[0].date))
    self.assertEqual(monitor_list.monitorInfo[0].count, EVENTS_TOTAL)

  def monitor_event_cumulative_filter_by_time(self):
    '''Monitor Events: Cumulative, filter by event time.
    '''
    # TODO: Story #1424: Change to use the standard ISO 8601 time interval notation.
    pass
  
  def monitor_event_cumulative_filter_by_event_type(self):
    '''Monitor Events: Cumulative, filter by event format.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    monitor_list = client.getOperationStatistics('<dummy token>',
                                              event='read')
    self.assertEqual(len(monitor_list.monitorInfo), 1)
    self.assert_valid_date(str(monitor_list.monitorInfo[0].date))
    self.assertEqual(monitor_list.monitorInfo[0].count, EVENTS_READ)
                                              
  def monitor_event_cumulative_filter_by_object_format(self):
    '''Monitor Events: Cumulative, filter by time and format.
    '''
    # TODO: Test set currently contains only one format. Create
    # some more formats so this can be tested properly.
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    monitor_list = client.getOperationStatistics('<dummy token>',
                                                 format='eml://ecoinformatics.org/eml-2.0.0')
    self.assertEqual(len(monitor_list.monitorInfo), 1)
    self.assert_valid_date(str(monitor_list.monitorInfo[0].date))
    self.assertEqual(monitor_list.monitorInfo[0].count, EVENTS_TOTAL)

  def monitor_event_cumulative_filter_by_principal(self):
    '''Monitor Events: Cumulative, filter by event PID.
    '''
    # TODO: Ticket
    pass

  def monitor_event_daily_no_filter(self):
    '''Monitor Events: Daily, no filter.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    monitor_list = client.getOperationStatistics('<dummy token>', day=True)
    self.assertEqual(len(monitor_list.monitorInfo), EVENTS_UNIQUE_DATES)
    self.assert_valid_date(str(monitor_list.monitorInfo[0].date))
    found_date = False
    for monitor_info in monitor_list.monitorInfo:
      if str(monitor_info.date) == '1981-08-28':
        found_date = True
        self.assertEqual(monitor_info.count, 1)
    self.assertTrue(found_date)
    
  def monitor_event_daily_filter_by_time(self):
    '''Monitor Events: Daily, filter by event creation time.
    '''
    # TODO: Story #1424
    pass

  def monitor_event_daily_filter_by_event_type(self):
    '''Monitor Events: Daily, filter by event format.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    monitor_list = client.getOperationStatistics('<dummy token>',
                                              event='read',
                                              day=True)
    self.assertEqual(len(monitor_list.monitorInfo), EVENTS_UNIQUE_DATES_WITH_READ)
    self.assert_valid_date(str(monitor_list.monitorInfo[0].date))
    self.assertEqual(monitor_list.monitorInfo[0].count, 1)

  def monitor_event_daily_filter_by_object_format(self):
    '''Monitor Events: Daily, filter by event format.
    '''
    # TODO: Test set currently contains only one format. Create
    # some more formats so this can be tested properly.
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    monitor_list = client.getOperationStatistics('<dummy token>',
                                              format='eml://ecoinformatics.org/eml-2.0.0',
                                              day=True)
    self.assertEqual(len(monitor_list.monitorInfo), EVENTS_WITH_OBJECT_FORMAT_EML)
    self.assert_valid_date(str(monitor_list.monitorInfo[0].date))
    self.assertEqual(monitor_list.monitorInfo[0].count, EVENTS_COUNT_OF_FIRST)

  def monitor_event_daily_filter_by_principal(self):
    '''Monitor Events: Daily, filter by time and format.
    '''
    # TODO: Story
    pass
    
  #
  #
  #

# TODO: Orderby is not supported in the current API spec. It will probably be completely removed.
#  def orderby_size(self):
#    '''ObjectList orderby: size.
#    '''
#    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
#    response = client.GET(client.getObjectListUrl() + '?pretty&count=10&orderby=size', {'Accept': d1_common.const.MIMETYPE_JSON})
#    doc = json.loads(response.read())
#    self.assertEqual(doc['objectInfo'][0]['size'], 1982)
#    self.assertEqual(doc['objectInfo'][9]['size'], 2746)
#
#  def orderby_size_desc(self):
#    '''ObjectList orderby: desc_size.
#    '''
#    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
#    response = client.client.GET(client.getObjectListUrl() + '?pretty&count=10&orderby=desc_size', {'Accept': d1_common.const.MIMETYPE_JSON})
#    doc = json.loads(response.read())
#    self.assertEqual(doc['objectInfo'][0]['size'], 17897472)
#    self.assertEqual(doc['objectInfo'][9]['size'], 717851)


  def delete(self):
    '''MN_crud.delete() in GMN and libraries.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    # Find the PID for a random object that exists on the server.
    pid = self.find_valid_pid(client)
    # Delete the object on GMN.
    pid_deleted = client.delete('<dummy token>', pid)
    self.assertEqual(pid, pid_deleted.value())
    # Verify that the object no longer exists.
    # We check for SyntaxError raised by the XML deserializer when it attempts
    # to deserialize a DataONEException. The exception is caused by the body
    # being empty since describe() uses a HEAD request.
    self.assertRaises(SyntaxError, client.describe, '<dummy token>', pid)

  def describe(self):
    '''MN_crud.describe in GMN and libraries.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    # Find the PID for a random object that exists on the server.
    pid = self.find_valid_pid(client)
    # Get header information for object.
    info = client.describe(pid)
    self.assertTrue(re.search(r'Content-Length', str(info))) 
    self.assertTrue(re.search(r'Date', str(info))) 
    self.assertTrue(re.search(r'Content-Type', str(info))) 
  
  def replication(self):
    '''Replication. Requires fake CN.
    '''
    # The object we will replicate.
    pid = 'hdl:10255/dryad.105/mets.xml'
    # Source and destination node references.

    # Delete the object on the destination node if it exists there.
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    try:
      pid_deleted = client.delete(pid)
      self.assertEqual(pid, pid_deleted.value())
    except d1_common.types.exceptions.NotFound:
      pass

    # Verify that the object no longer exists.
    # We check for SyntaxError raised by the XML deserializer when it attempts
    # to deserialize a DataONEException. The exception is caused by the body
    # being empty since describe() uses a HEAD request.
    self.assertRaises(SyntaxError, client.describe, pid)


    # Call to /cn/test_replicate/<pid>/<src_node_ref>
    test_replicate_url = urlparse.urljoin(self.opts.d1_root,
                                          'test_replicate/{0}/{1}'\
                                          .format(urllib.quote(self.opts.replicate_src_ref, ''),
                                                  urllib.quote(pid, '')))
    
    root = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    response = root.client.GET(test_replicate_url)
    self.assertEqual(response.code, 200)

    replicate_mime = response.read()
    # Add replication task to the destination GMN work queue.
    client_dst = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    replicate_url = urlparse.urljoin(client_dst.client.target, 'replicate')
    headers = {}
    headers['Content-Type'] = 'multipart/form-data; boundary=----------6B3C785C-6290-11DF-A355-A6ECDED72085_$'
    headers['Content-Length'] = len(replicate_mime)
    headers['User-Agent'] = d1_common.const.USER_AGENT
    client_dst.client.POST(replicate_url, replicate_mime, headers)

#  # Get the checksum of the object from the source GMN. This also checks if
#  # we can reach the source server and that it has the object we will replicate.
#  src_checksum_obj = client_src.checksum(pid)
#  src_checksum = src_checksum_obj.value()
#  src_algorithm = src_checksum_obj.algorithm
#
#  # Get the bytes of the object from the source server.
#  src_obj_str = client_src.get(pid).read()
#
#  # Replicate.
#
#  # Clear any existing Replica items related to this pid and test
#  # source node on the CN.
#  clear_replication_status_url = urlparse.urljoin(client_dst.client.target,
#                                                  '/cn/test_clear_replication_status/{0}/{1}'.format(src_node, pid))
#  client_dst.client.GET(clear_replication_status_url)
#  
#  # Add replication task to the destination GMN work queue.
#  replicate_url = urlparse.urljoin(client_dst.client.target,
#                                                  '/replicate/{0}/{1}'.format(src_node, pid))
#  client_dst.client.PUT(replicate_url, '')
#  
#  # Poll for completed replication.
#  replication_completed = False
#  while not replication_completed:
#    test_get_replication_status_xml = urlparse.urljoin(client_dst.client.target,
#                                                    '/cn/test_get_replication_status_xml/{0}'.format(pid))
#    status_xml_str = client_dst.client.GET(test_get_replication_status_xml).read()
#    status_xml_obj = lxml.etree.fromstring(status_xml_str)
#
#    for replica in status_xml_obj.xpath('/replicas/replica'):
#      if replica.xpath('replicaMemberNode')[0].text == src_node:
#        if replica.xpath('replicationStatus')[0].text == 'completed':
#          replication_completed = True
#          break
#
#    if not replication_completed:
#      time.sleep(1)
#
#  # Get checksum of the object on the destination server and compare it to
#  # the checksum retrieved from the source server.
#  dst_checksum_obj = client_dst.checksum(pid)
#  dst_checksum = dst_checksum_obj.value()
#  dst_algorithm = dst_checksum_obj.algorithm
#  self.assertEqual(src_checksum, dst_checksum)
#  self.assertEqual(src_algorithm, dst_algorithm)
#  
#  # Get the bytes of the object on the destination and compare them with the
#  # bytes retrieved from the source.
#  dst_obj_str = client_dst.get(pid).read()
#  self.assertEqual(src_obj_str, dst_obj_str)

  def unicode_test_1(self):
    '''GMN and libraries handle Unicode correctly.
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)

    test_doc_path = os.path.join(self.opts.int_path,
                                 'src', 'test', 'resources', 'd1_testdocs', 'encodingTestSet')
    test_ascii_strings_path = os.path.join(test_doc_path, 'testAsciiStrings.utf8.txt')

    file_obj = codecs.open(test_ascii_strings_path, 'r', 'utf-8')
    for line in file_obj:
      line = line.strip()
      try:
        pid_unescaped, pid_escaped = line.split('\t')
      except ValueError:
        pass

      # Create a small test object containing only the pid. 
      scidata = pid_unescaped.encode('utf-8')

      # Create corresponding system metadata for the test object.
      size = len(scidata)
      # hashlib.md5 can't hash a unicode string. If it did, we would get a hash
      # of the internal Python encoding for the string. So we maintain scidata as a utf-8 string.
      md5 = hashlib.md5(scidata).hexdigest()
      now = datetime.datetime.now()
      sysmeta_xml = self.gen_sysmeta(pid_unescaped, size, md5, now)

      # Create the object on GMN.
      client.create(pid_unescaped, StringIO.StringIO(scidata), StringIO.StringIO(sysmeta_xml), {})

      # Retrieve the object from GMN.
      scidata_retrieved = client.get(pid_unescaped).read()
      sysmeta_obj_retrieved = client.getSystemMetadata(pid_unescaped)
      
      # Round-trip validation.
      self.assertEqual(scidata_retrieved, scidata)
      self.assertEqual(sysmeta_obj_retrieved.identifier.value(), scidata)

  #
  # Tests.
  #

  # The tests are defined manually instead of dynamically because they
  # describe the order in which the tests should be run and they can
  # be easilly commented out here when debugging.
  #

  #
  # Managed (object byte storage handled locally by GMN).
  #

  def test_1010_managed_A_delete_all_objects(self):
    self.delete_all_objects()
    
  def test_1010_managed_B_object_collection_is_empty(self):
    self.object_collection_is_empty()

  def test_1010_managed_C_create_objects(self):
    '''Managed: Populate MN with set of test objects (local).
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    for sysmeta_path in sorted(glob.glob(os.path.join(self.opts.obj_path, '*.sysmeta'))):
      # Get name of corresponding object and open it.
      object_path = re.match(r'(.*)\.sysmeta', sysmeta_path).group(1)
      object_file = open(object_path, 'r')
  
      # The pid is stored in the sysmeta.
      sysmeta_file = open(sysmeta_path, 'r')
      sysmeta_xml = sysmeta_file.read()
      sysmeta_obj = d1_client.systemmetadata.SystemMetadata(sysmeta_xml)
          
      # To create a valid URL, we must quote the pid twice. First, so
      # that the URL will match what's on disk and then again so that the
      # quoting survives being passed to the web server.
      #obj_url = urlparse.urljoin(self.opts.obj_url, urllib.quote(urllib.quote(pid, ''), ''))
  
      # To test the MIME Multipart poster, we provide the Sci object as a file
      # and the SysMeta as a string.
      client.create('<dummy token>', sysmeta_obj.identifier, object_file, sysmeta_xml, {})

  def test_1010_managed_D_object_collection_is_populated(self):
    self.object_collection_is_populated()

  def test_1020_managed_A_clear_event_log(self):
    self.clear_event_log()
  
  def test_1020_managed_B_event_log_is_empty(self):
    self.event_log_is_empty()
  
  def test_1020_managed_C_inject_event_log(self):
    self.inject_event_log()

  def test_1020_managed_D_event_log_is_populated(self):
    self.event_log_is_populated()
  
  def test_1030_managed_compare_byte_by_byte(self):
    self.compare_byte_by_byte()
       
  def test_1040_managed_object_properties(self):
    self.object_properties()

  def test_1100_managed_slicing_1(self):
    self.slicing_1()

  def test_1110_managed_slicing_2(self):
    self.slicing_2()

  def test_1120_managed_slicing_3(self):
    self.slicing_3()

  def test_1130_managed_slicing_4(self):
    self.slicing_4()

  def test_1140_managed_date_range_1(self):
    self.date_range_1()

  def test_1150_managed_date_range_2(self):
    self.date_range_2()

  def test_1160_managed_date_range_3(self):
    self.date_range_3()

  def test_1170_managed_date_range_4(self):
    self.date_range_4()

  def test_1180_managed_get_object_count(self):
    self.get_object_count()

  def test_1190_managed_get_object_by_invalid_pid(self):
    self.get_object_by_invalid_pid()

  def test_1200_managed_get_object_by_valid_pid(self):
    self.get_object_by_valid_pid()

  def test_1210_managed_get_sysmeta_by_invalid_pid(self):
    self.get_sysmeta_by_invalid_pid()

  def test_1220_managed_get_sysmeta_by_valid_pid(self):
    self.get_sysmeta_by_valid_pid()

  def test_1230_managed_xml_validation(self):
    self.xml_validation()

  def test_1240_managed_pxby_objectlist_xml(self):
    self.pxby_objectlist_xml()
  
  def test_1250_managed_pxby_objectlist_json(self):
    self.pxby_objectlist_json()

#  def test_1260_managed_pxby_objectlist_rdf_xml(self):
#    self.pxby_objectlist_rdf_xml()
    
  def test_1270_managed_pxby_objectlist_csv(self):
    self.pxby_objectlist_csv()

  def test_1280_managed_monitor_object_cumulative_no_filter(self):
    self.monitor_object_cumulative_no_filter()

  def test_1281_managed_monitor_object_cumulative_filter_by_time(self):
    self.monitor_object_cumulative_filter_by_time()

  def test_1282_managed_monitor_object_cumulative_filter_by_format(self):
    self.monitor_object_cumulative_filter_by_format()

  def test_1283_managed_monitor_object_cumulative_filter_by_time_and_format(self):
    self.monitor_object_cumulative_filter_by_time_and_format()

  def test_1284_managed_monitor_object_cumulative_filter_by_pid(self):
    self.monitor_object_cumulative_filter_by_pid()
  
  def test_1285_managed_monitor_object_daily_no_filter(self):
    self.monitor_object_daily_no_filter()

  def test_1286_managed_monitor_object_daily_filter_by_time(self):
    self.monitor_object_daily_filter_by_time()

  def test_1287_managed_monitor_object_daily_filter_by_format(self):
    self.monitor_object_daily_filter_by_format()

  def test_1288_managed_monitor_object_daily_filter_by_time_and_format(self):
    self.monitor_object_daily_filter_by_time_and_format()

  def test_1289_managed_monitor_object_daily_filter_by_pid(self):
    self.monitor_object_daily_filter_by_pid()

  def test_1290_managed_monitor_event_cumulative_no_filter(self):
    self.monitor_event_cumulative_no_filter()

  def test_1291_managed_monitor_event_cumulative_filter_by_time(self):
    self.monitor_event_cumulative_filter_by_time()

  def test_1292_managed_monitor_event_cumulative_filter_by_event_type(self):
    self.monitor_event_cumulative_filter_by_event_type()

  def test_1293_managed_monitor_event_cumulative_filter_by_object_format(self):
    self.monitor_event_cumulative_filter_by_object_format()

  def test_1294_managed_monitor_event_cumulative_filter_by_principal(self):
    self.monitor_event_cumulative_filter_by_principal()

  def test_1295_managed_monitor_event_daily_no_filter(self):
    self.monitor_event_daily_no_filter()

  def test_1296_managed_monitor_event_daily_filter_by_time(self):
    self.monitor_event_daily_filter_by_time()

  def test_1297_managed_monitor_event_daily_filter_by_event_type(self):
    self.monitor_event_daily_filter_by_event_type()

  def test_1298_managed_monitor_event_daily_filter_by_object_format(self):
    self.monitor_event_daily_filter_by_object_format()

  def test_1299_managed_monitor_event_daily_filter_by_principal(self):
    self.monitor_event_daily_filter_by_principal()

#  # TODO: Orderby will probably be completely removed.
#  def test_1300_managed_orderby_size(self):
#    self.orderby_size()

#  # TODO: Orderby will probably be completely removed.
#  def test_1310_managed_orderby_size_desc(self):
#    self.orderby_size_desc()

# TODO: Include checksum tests if we keep getChecksum().

  def test_1330_managed_delete(self):
    self.delete()

  def test_1340_managed_describe(self):
    self.describe()
  
  def test_1350_managed_replication(self):
    self.replication()

#  def test_1360_managed_unicode_test_1(self):
#    self.unicode_test_1()

  #
  # Wrapped (object bytes store by remote web server).
  #
  
  def test_2010_wrapped_A_delete_all_objects(self):
    self.delete_all_objects()
    
  def test_2010_wrapped_B_object_collection_is_empty(self):
    self.object_collection_is_empty()
  
  def test_2010_wrapped_C_create_objects(self):
    '''Wrapped: Populate MN with set of test objects (Remote).
    '''
    client = gmn_test_client.GMNTestClient(self.opts.gmn_url)
    for sysmeta_path in sorted(glob.glob(os.path.join(self.opts.obj_path, '*.sysmeta'))):
      # Get name of corresponding object and open it.
      object_path = re.match(r'(.*)\.sysmeta', sysmeta_path).group(1)
      object_file = open(object_path, 'r')
  
      # The pid is stored in the sysmeta.
      sysmeta_file = open(sysmeta_path, 'r')
      sysmeta_xml = sysmeta_file.read()
      sysmeta_obj = d1_client.systemmetadata.SystemMetadata(sysmeta_xml)
          
      # This test requires the objects to also be available on a web server
      # (http://localhost:80/test_client_objects by default). This simulates
      # remote storage of the objects.

      # To create a valid URL, we must quote the pid twice. First, so
      # that the URL will match what's on disk and then again so that the
      # quoting survives being passed to the web server.
      sciobj_url = urlparse.urljoin(self.opts.obj_url, urllib.quote(urllib.quote(sysmeta_obj.identifier, ''), ''))
      scimeta_abs_url = urlparse.urljoin(self.opts.obj_url, sciobj_url)
    
      # To test the MIME Multipart poster, we provide the Sci object as a file
      # and the SysMeta as a string.
      client.create('<dummy token>', sysmeta_obj.identifier, object_file,
                    sysmeta_xml, {'vendor_gmn_remote_url': scimeta_abs_url})
    
  def test_2010_wrapped_D_object_collection_is_populated(self):
    self.object_collection_is_populated()

  def test_2020_wrapped_A_clear_event_log(self):
    self.clear_event_log()
  
  def test_2020_wrapped_B_event_log_is_empty(self):
    self.event_log_is_empty()

  def test_2020_wrapped_C_inject_event_log(self):
    self.inject_event_log()

  def test_2020_wrapped_D_event_log_is_populated(self):
    self.event_log_is_populated()

  def test_2030_wrapped_compare_byte_by_byte(self):
    self.compare_byte_by_byte()
       
  def test_2040_wrapped_object_properties(self):
    self.object_properties()

  def test_2100_wrapped_slicing_1(self):
    self.slicing_1()

  def test_2110_wrapped_slicing_2(self):
    self.slicing_2()

  def test_2120_wrapped_slicing_3(self):
    self.slicing_3()

  def test_2130_wrapped_slicing_4(self):
    self.slicing_4()

  def test_2140_wrapped_date_range_1(self):
    self.date_range_1()

  def test_2150_wrapped_date_range_2(self):
    self.date_range_2()

  def test_2160_wrapped_date_range_3(self):
    self.date_range_3()

  def test_2170_wrapped_date_range_4(self):
    self.date_range_4()

  def test_2180_wrapped_get_object_count(self):
    self.get_object_count()

  def test_2190_wrapped_get_object_by_invalid_pid(self):
    self.get_object_by_invalid_pid()

  def test_1200_wrapped_get_object_by_valid_pid(self):
    self.get_object_by_valid_pid()

  def test_1210_wrapped_get_sysmeta_by_invalid_pid(self):
    self.get_sysmeta_by_invalid_pid()

  def test_1220_wrapped_get_sysmeta_by_valid_pid(self):
    self.get_sysmeta_by_valid_pid()

  def test_1230_wrapped_xml_validation(self):
    self.xml_validation()

  def test_1240_wrapped_pxby_objectlist_xml(self):
    self.pxby_objectlist_xml()
  
  def test_1250_wrapped_pxby_objectlist_json(self):
    self.pxby_objectlist_json()

#  def test_1260_wrapped_pxby_objectlist_rdf_xml(self):
#    self.pxby_objectlist_rdf_xml()
    
  def test_1270_wrapped_pxby_objectlist_csv(self):
    self.pxby_objectlist_csv()

  def test_2280_wrapped_monitor_object_cumulative_no_filter(self):
    self.monitor_object_cumulative_no_filter()

  def test_2281_wrapped_monitor_object_cumulative_filter_by_time(self):
    self.monitor_object_cumulative_filter_by_time()

  def test_2282_wrapped_monitor_object_cumulative_filter_by_format(self):
    self.monitor_object_cumulative_filter_by_format()

  def test_2283_wrapped_monitor_object_cumulative_filter_by_time_and_format(self):
    self.monitor_object_cumulative_filter_by_time_and_format()

  def test_2284_wrapped_monitor_object_cumulative_filter_by_pid(self):
    self.monitor_object_cumulative_filter_by_pid()
  
  def test_2285_wrapped_monitor_object_daily_no_filter(self):
    self.monitor_object_daily_no_filter()

  def test_2286_wrapped_monitor_object_daily_filter_by_time(self):
    self.monitor_object_daily_filter_by_time()

  def test_2287_wrapped_monitor_object_daily_filter_by_format(self):
    self.monitor_object_daily_filter_by_format()

  def test_2288_wrapped_monitor_object_daily_filter_by_time_and_format(self):
    self.monitor_object_daily_filter_by_time_and_format()

  def test_2289_wrapped_monitor_object_daily_filter_by_pid(self):
    self.monitor_object_daily_filter_by_pid()

  def test_2290_wrapped_monitor_event_cumulative_no_filter(self):
    self.monitor_event_cumulative_no_filter()

  def test_2291_wrapped_monitor_event_cumulative_filter_by_time(self):
    self.monitor_event_cumulative_filter_by_time()

  def test_2292_wrapped_monitor_event_cumulative_filter_by_event_type(self):
    self.monitor_event_cumulative_filter_by_event_type()

  def test_2293_wrapped_monitor_event_cumulative_filter_by_object_format(self):
    self.monitor_event_cumulative_filter_by_object_format()

  def test_2294_wrapped_monitor_event_cumulative_filter_by_principal(self):
    self.monitor_event_cumulative_filter_by_principal()

  def test_2295_wrapped_monitor_event_daily_no_filter(self):
    self.monitor_event_daily_no_filter()

  def test_2296_wrapped_monitor_event_daily_filter_by_time(self):
    self.monitor_event_daily_filter_by_time()

  def test_2297_wrapped_monitor_event_daily_filter_by_event_type(self):
    self.monitor_event_daily_filter_by_event_type()

  def test_2298_wrapped_monitor_event_daily_filter_by_object_format(self):
    self.monitor_event_daily_filter_by_object_format()

  def test_2299_wrapped_monitor_event_daily_filter_by_principal(self):
    self.monitor_event_daily_filter_by_principal()

#  # TODO: Orderby will probably be completely removed.
  def test_2300_wrapped_orderby_size(self):
    self.orderby_size()

#  # TODO: Orderby will probably be completely removed.
  def test_2310_wrapped_orderby_size_desc(self):
    self.orderby_size_desc()
  
  def test_2330_wrapped_delete(self):
    self.delete_test()

  def test_2340_wrapped_describe(self):
    self.describe()

#  def test_2350_wrapped_replication(self):
#    self.replication(self)

#  def test_2360_wrapped_unicode_test_1(self):
#    self.unicode_test_1()


def main():
  log_setup()
  
  # Command line opts.
  parser = optparse.OptionParser()
  parser.add_option('--d1-root', dest='d1_root', action='store', type='string', default='http://0.0.0.0:8000/cn/') # default=d1_common.const.URL_DATAONE_ROOT
  parser.add_option('--gmn-url', dest='gmn_url', action='store', type='string', default='http://0.0.0.0:8000/')
  parser.add_option('--gmn2-url', dest='gmn2_url', action='store', type='string', default='http://0.0.0.0:8001/')
  parser.add_option('--gmn-replicate-src-ref', dest='replicate_src_ref', action='store', type='string', default='gmn_dryad')
  parser.add_option('--cn-url', dest='cn_url', action='store', type='string', default='http://cn-dev.dataone.org/cn/')
  parser.add_option('--xsd-path', dest='xsd_url', action='store', type='string', default='http://129.24.0.11/systemmetadata.xsd')
  parser.add_option('--obj-path', dest='obj_path', action='store', type='string', default='./test_client_objects')
  parser.add_option('--obj-url', dest='obj_url', action='store', type='string', default='http://localhost:80/test_client_objects/')
  parser.add_option('--verbose', action='store_true', default=False, dest='verbose')
  parser.add_option('--quick', action='store_true', default=False, dest='quick')
  parser.add_option('--test', action='store', default='', dest='test', help='run a single test')
#  parser.add_option('--unicode-path', dest='unicode_path', action='store', type='string', default='/home/roger/D1/svn/allsoftware/cicore/d1_integration/src/test/resources/d1_testdocs/encodingTestSet/testUnicodeStrings.utf8.txt')
  parser.add_option('--integration-path', dest='int_path', action='store', type='string', default='./d1_integration')
  parser.add_option('--debug', action='store_true', default=False, dest='debug')

  (opts, args) = parser.parse_args()

  if not opts.verbose:
    logging.getLogger('').setLevel(logging.ERROR)
  
  s = TestSequenceFunctions
  s.opts = opts
 
  if opts.test != '':
    suite = unittest.TestSuite(map(s, [opts.test]))
    #suite.debug()
  else:
    suite = unittest.TestLoader().loadTestsFromTestCase(s)

#  if opts.debug == True:    
#    unittest.TextTestRunner(verbosity=2).debug(suite)
#  else:
  unittest.TextTestRunner(verbosity=2).run(suite)

if __name__ == '__main__':
  main()

