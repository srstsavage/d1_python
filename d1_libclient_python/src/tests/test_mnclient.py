'''
Created on Jan 20, 2011

@author: vieglais
'''
import unittest
import logging
from d1_client import cnclient
import d1_common.exceptions
from testcasewithurlcompare import TestCaseWithURLCompare


class TestCNClient(TestCaseWithURLCompare):
  def setUp(self):
    #self.baseurl = 'http://daacmn-dev.dataone.org/mn'
    self.baseurl = 'http://dev-dryad-mn.dataone.org/mn'
    #    self.testpid = 'hdl:10255/dryad.105/mets.xml'
    #http://dev-dryad-mn.dataone.org/mn/meta/hdl:10255/dryad.105/mets.xml
    #http://dev-dryad-mn.dataone.org/mn/meta/hdl%3A10255%2Fdryad.105%2Fmets.xml
    #http://dev-dryad-mn.dataone.org/mn/meta/hdl:10255%2Fdryad.105%2Fmets.xml
    #http://dev-dryad-mn.dataone.org/mn/meta/hdl%3A10255/dryad.105/mets.xml
    self.token = None

  def tearDown(self):
    pass

  def test_create(self):
    raise Exception('Not Implemented')

  def test_update(self):
    raise Exception('Not Implemented')

  def test_delete(self):
    raise Exception('Not Implemented')

  def test_getChecksum(self):
    raise Exception('Not Implemented')

  def test_replicate(self):
    raise Exception('Not Implemented')

  def test_synchronizationFailed(self):
    raise Exception('Not Implemented')

  def test_getObjectStatistics(self):
    raise Exception('Not Implemented')

  def test_getOperationStatistics(self):
    raise Exception('Not Implemented')

  def test_getStatus(self):
    raise Exception('Not Implemented')

  def test_getCapabilities(self):
    raise Exception('Not Implemented')


if __name__ == "__main__":
  logging.basicConfig(level=logging.DEBUG)
  unittest.main()
