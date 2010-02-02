#!/usr/bin/env python
# -*- coding: utf-8 -*-
""":mod:`tests` -- Unit Tests
=============================

:module: tests
:platform: Linux
:synopsis: Unit Tests

.. moduleauthor:: Roger Dahl
"""

# Stdlib.
import json
import StringIO

# Django.
from django.test import TestCase

# Lxml.
from lxml import etree

# App.
import settings
import util
import sysmeta

# Constants related to simulated MN object collection.
mn_objects_total = 354
mn_objects_total_data = 100
mn_objects_total_metadata = 77
mn_objects_total_sysmeta = 177


class mn_service_tests(TestCase):
  fixtures = ['base.fixture.json']

  #
  # Helpers. The test runner will not run these because they don't start with
  # the word "test".
  #

  def check_response_headers_present(self, response):
    """Check that required response headers are present."""

    self.failUnlessEqual('Last-Modified' in response, True)
    self.failUnlessEqual('Content-Length' in response, True)
    self.failUnlessEqual('Content-Type' in response, True)

  def get_valid_guid(self, object_type):
    """Get a valid GUID of a specific type from the db.

    Current valid object types: data, metadata, sysmeta
    
    Assumes that there are 3 valid objects of the given type in the db.
    """

    response = self.client.get('/mn/object/', {'start': '3', 'count': '1', 'oclass': object_type}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 200)
    res = json.loads(response.content)
    return res['data'][0]['guid']

  #
  # /object/ collection calls.
  #
  # GET
  #

  # TODO: Set up test of update_db admin command.

  def test_rest_call_object_count_get(self):
    """Test call: curl -X GET -H "Accept: application/json" http://127.0.0.1:8000/mn/object/?start=0&count=0"""

    response = self.client.get('/mn/object/', {'start': '0', 'count': '0'}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)
    res = json.loads(response.content)
    # {u'count': 0, u'start': 0, u'total': mn_objects_total, u'data': {}}
    self.failUnlessEqual(res['count'], 0)
    self.failUnlessEqual(res['start'], 0)
    self.failUnlessEqual(res['total'], mn_objects_total)
    # Check if results contains number of objects that was reported to be returned.
    self.failUnlessEqual(len(res['data']), res['count'])

  def test_rest_call_object_count_by_oclass_data_get(self):
    """Test call: curl -X GET -H "Accept: application/json" http://127.0.0.1:8000/mn/object/?start=0&count=0&oclass=data"""

    response = self.client.get('/mn/object/', {'start': '0', 'count': '0', 'oclass': 'data'}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)
    res = json.loads(response.content)
    self.failUnlessEqual(res['count'], 0)
    self.failUnlessEqual(res['start'], 0)
    self.failUnlessEqual(res['total'], mn_objects_total_data)
    # Check if results contains number of objects that was reported to be returned.
    self.failUnlessEqual(len(res['data']), res['count'])

  def test_rest_call_object_count_by_oclass_metadata_get(self):
    """Test call: curl -X GET -H "Accept: application/json" http://127.0.0.1:8000/mn/object/?start=0&count=0&oclass=metadata"""

    response = self.client.get('/mn/object/', {'start': '0', 'count': '0', 'oclass': 'metadata'}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)
    res = json.loads(response.content)
    # {u'count': 0, u'start': 0, u'total': mn_objects_total, u'data': {}}
    self.failUnlessEqual(res['count'], 0)
    self.failUnlessEqual(res['start'], 0)
    self.failUnlessEqual(res['total'], mn_objects_total_metadata)
    # Check if results contains number of objects that was reported to be returned.
    self.failUnlessEqual(len(res['data']), res['count'])

  def test_rest_call_collection_of_objects_all_get(self):
    """Test call: curl -X GET -H "Accept: application/json" http://127.0.0.1:8000/mn/object/"""

    response = self.client.get('/mn/object/', HTTP_ACCEPT='application/json')
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)
    #print response.content
    res = json.loads(response.content)
    self.failUnlessEqual(res['count'], mn_objects_total)
    self.failUnlessEqual(res['start'], 0)
    self.failUnlessEqual(res['total'], mn_objects_total)
    # Check if results contains number of objects that was reported to be returned.
    self.failUnlessEqual(len(res['data']), res['count'])

  def test_rest_call_collection_of_objects_section_get(self):
    """curl -X GET -H "Accept: application/json" http://127.0.0.1:8000/mn/object/?start=20&count=10"""

    response = self.client.get('/mn/object/', {'start': '20', 'count': '10'}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)
    res = json.loads(response.content)
    self.failUnlessEqual(res['count'], 10)
    self.failUnlessEqual(res['start'], 20)
    self.failUnlessEqual(res['total'], mn_objects_total)
    # Check if results contains number of objects that was reported to be returned.
    self.failUnlessEqual(len(res['data']), res['count'])
    # Check the first of the data objects for the correct format.
    self.failUnlessEqual(len(res['data'][0]['hash']), 40)

  def test_rest_call_collection_of_objects_section_oclass_filter_get(self):
    """Test multiple filters.
    
    Example call: curl -X GET -H "Accept: application/json" http://127.0.0.1:8000/mn/object/?start=10&count=5&oclass=metadata
    """

    response = self.client.get('/mn/object/', {'start': '10', 'count': '5', 'oclass': 'metadata'}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)
    res = json.loads(response.content)
    self.failUnlessEqual(res['count'], 5) # Number of objects returned.
    self.failUnlessEqual(res['start'], 10) # Starting object.
    self.failUnlessEqual(res['total'], mn_objects_total_metadata)
    # Check if results contains number of objects that was reported to be returned.
    self.failUnlessEqual(len(res['data']), res['count'])
    # Check the first of the data objects for the correct format.
    self.failUnlessEqual(res['data'][0]['oclass'], 'metadata')
    self.failUnlessEqual(len(res['data'][0]['hash']), 40)

  def test_rest_call_collection_of_objects_section_oclass_filter_unavailable_get(self):
    """Test the corner case where we ask for more objects of a certain type than
    are available.
    
    curl -X GET -H "Accept: application/json" http://127.0.0.1:8000/mn/object/?start=15&count=10&oclass=metadata
    """

    response = self.client.get('/mn/object/', {'start': mn_objects_total_metadata - 5, 'count': '10', 'oclass': 'metadata'}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)
    res = json.loads(response.content)
    self.failUnlessEqual(
      res['count'], 5
    ) # We should get the 5 remaining objects even though we asked for 10.
    self.failUnlessEqual(res['start'], mn_objects_total_metadata - 5) # Starting object.
    self.failUnlessEqual(
      res['total'], mn_objects_total_metadata
    ) # Total number of objects of type metadata.
    # Check if results contains number of objects that was reported to be returned.
    self.failUnlessEqual(len(res['data']), res['count'])
    # Check the first of the data objects for the correct format.
    self.failUnlessEqual(res['data'][0]['oclass'], 'metadata')
    self.failUnlessEqual(len(res['data'][0]['hash']), 40)

  #
  # /object/ collection calls.
  #
  # HEAD
  #

  def test_rest_call_object_count_head(self):
    """Test call: curl -I http://127.0.0.1:8000/mn/object/?start=0&count=0
    """

    response = self.client.head('/mn/object/', {'start': '0', 'count': '0'}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)

  def test_rest_call_object_count_by_oclass_data_head(self):
    """Test call: curl -I http://127.0.0.1:8000/mn/object/?start=0&count=0&oclass=data
    """

    response = self.client.head('/mn/object/', {'start': '0', 'count': '0', 'oclass': 'data'}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)

  #
  # /object/ specific object calls.
  #
  # GET.
  #

  def test_rest_call_object_by_guid_get(self):
    """curl -X GET -H "Accept: application/json" http://127.0.0.1:8000/mn/object/<valid guid>
    """

    response = self.client.get('/mn/object/%s' % self.get_valid_guid('metadata'), {}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)
    #self.failUnlessEqual(response.content, 'data_guid:c93ee59c-990f-4b2f-af53-995c0689bf73\nmetadata:0.904577532946\n')

  def test_rest_call_object_by_guid_404_get(self):
    """curl -X GET -H "Accept: application/json" http://127.0.0.1:8000/mn/object/invalid_guid
    """

    response = self.client.get('/mn/object/invalid_guid', {}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 404)

  def test_rest_call_sysmeta_by_object_guid_get(self):
    """curl -X GET -H "Accept: application/json" http://127.0.0.1:8000/mn/object/<valid guid>/meta
    
    NOTE: This test fails if the /update/ call has not been run from outside the
    test framework first.
    """

    response = self.client.get('/mn/object/%s/meta' % self.get_valid_guid('data'), {}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)
    # Check that this sysmeta validates against the schema.
    try:
      xsd_file = open(settings.XSD_PATH, 'r')
    except IOError as (errno, strerror):
      sys_log.error('XSD could not be opened: %s' % settings.XSD_PATH)
      sys_log.error('I/O error({0}): {1}'.format(errno, strerror))
      return
    except:
      sys_log.error('Unexpected error: ', sys.exc_info()[0])
      raise

    xmlschema_doc = etree.parse(settings.XSD_PATH)
    xmlschema = etree.XMLSchema(xmlschema_doc)
    xml = etree.parse(StringIO.StringIO(response.content))
    xmlschema.assertValid(xml)
    self.failUnlessEqual(xmlschema.validate(xml), True)

  def test_rest_call_sysmeta_by_object_guid_404_get(self):
    """curl -X GET -H "Accept: application/json" http://127.0.0.1:8000/mn/object/<invalid guid>/meta
    """

    response = self.client.get('/mn/object/invalid_guid/meta', {}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 404)

  #
  # /object/ specific object calls.
  #
  # HEAD
  #

  def test_rest_call_object_header_by_guid_head(self):
    """curl -I http://127.0.0.1:8000/mn/object/<valid guid>
    """

    response = self.client.head('/mn/object/%s' % self.get_valid_guid('data'))
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)

  def test_rest_call_last_modified_head(self):
    """curl -I http://mn1.dataone.org/object/
    """

    response = self.client.head('/mn/object/')
    self.failUnlessEqual(response.status_code, 200)
    self.check_response_headers_present(response)

  #
  # PUT.
  #

  def test_rest_call_sysmeta_by_object_guid_put(self):
    """curl -X PUT -H "Accept: application/json"
    http://127.0.0.1:8000/mn/object/<valid guid>/meta
    
    
    """

    response = self.client.put('/mn/object/%s/meta' % self.get_valid_guid('data'), {}, HTTP_ACCEPT = 'application/json')
    self.failUnlessEqual(response.status_code, 200)

  def test_s(self):
    sysmeta.set_replication_status('fedd5f19-9ca3-45a6-91a4-c247322c98e9', 'test')

  #
  # Authentication.
  #

  def test_rest_call_cn_auth(self):
    """Check that CN is successfully authenticated if matching an IP in the
    CN_IP list.
    
    Test call: curl -X GET -H "Accept: application/json"
    http://127.0.0.1:8000/mn/object/?start=0&count=0"""

    response = self.client.get('/mn/object/', {'start': '0', 'count': '0'},
                                REMOTE_ADDR = '192.168.1.200')
    self.failUnlessEqual(response.status_code, 200)

  def test_rest_call_cn_no_auth(self):
    """Check that client is blocked if not matching an IP in the CN_IP list.
    """

    response = self.client.get('/mn/object/', {'start': '0', 'count': '0'},
                                REMOTE_ADDR = '111.111.111.111')
    self.failUnlessEqual(response.content[:9], 'Attempted')
