'''
Module d1pythonitk.d1client
===========================

This module implements DataOneClient which provides a client supporting basic 
interaction with the DataONE infrastructure.

:Created: 20100111
:Author: vieglais

:Dependencies:

  - python 2.6

----

.. autoclass:: RESTClient
   :members:

----

.. autoclass:: DataOneClient
   :members:
'''

# Stdlib.
import logging
import httplib
import urllib
import urllib2
import urlparse
import sys
import os
import xml.dom.minidom

try:
  import cjson as json
except:
  import json

# DataONE.
from d1common import exceptions
from d1pythonitk import const
from d1pythonitk import systemmetadata
from d1common import upload


#===============================================================================
class HttpRequest(urllib2.Request):
  '''Overrides the default Request class to enable setting the HTTP method.
  '''

  def __init__(self, *args, **kwargs):
    self._method = 'GET'
    if kwargs.has_key('method'):
      self._method = kwargs['method']
      del kwargs['method']
    urllib2.Request.__init__(self, *args, **kwargs)

  def get_method(self):
    return self._method


#===============================================================================
class RESTClient(object):
  '''Implements a simple REST client that utilizes the base DataONE exceptions
  for error handling if possible.
  '''

  logger = logging.getLogger()

  def __init__(self, target=const.URL_DATAONE_ROOT):
    self.status = None
    self.responseInfo = None
    self._BASE_DETAIL_CODE = '10000'
    self.target = self._normalizeTarget(target)
    #TODO: Need to define these detailCode values

    self.logger.debug_ = lambda *x: self.log(self.logger.debug, x)
    self.logger.warn_ = lambda *x: self.log(self.logger.warn, x)
    self.logger.err_ = lambda *x: self.log(self.logger.error, x)

  def log(self, d, x):
    d(
      'file({0}) func({1}) line({2}): {3}'.format(
        os.path.basename(sys._getframe(2).f_code.co_filename), sys._getframe(
          2).f_code.co_name, sys._getframe(2).f_lineno, x
      )
    )

  def exceptionCode(self, extra):
    return "%s.%s" % (self._BASE_DETAIL_CODE, str(extra))

  def _normalizeTarget(self, target):
    '''Internal method to ensure target url is in suitable form before 
    adding paths.
    '''
    if not target.endswith("/"):
      target += "/"
    return target

  @property
  def headers(self):
    '''Returns a dictionary of headers
    '''
    return {'User-Agent': 'Test client', 'Accept': '*/*'}

  def loadError(self, response):
    '''Try and create a DataONE exception form the response.  If successful, 
    then the DataONE error will be raised, otherwise the error is encapsulated
    with a DataONE ServiceFailure exception and re-raised.
    
    :param response: Response from urllib2.urlopen
    :returns: Should not return - always raises an exception.
    '''
    edata = response.read()
    exc = exceptions.DataOneExceptionFactory.createException(edata)
    if not exc is None:
      raise exc
    return False

  def sendRequest(self, url, method='GET', data=None, headers=None):
    '''Sends a HTTP request and returns the response as a file like object.
    
    Has the side effect of setting the status and responseInfo properties. 
    
    :param url: The target URL
    :type url: string
    :param method: The HTTP method to use.
    :type method: string
    :param data: Optional dictionary of data to pass on to urllib2.urlopen
    :type data: dictionary
    :param headers: Optional header information
    :type headers: dictionary
    '''
    if headers is None:
      headers = self.headers
    request = HttpRequest(url, data=data, headers=headers, method=method)

    self.logger.debug_('url({0}) headers({1}) method({2})'.format(url, headers, method))

    try:
      response = urllib2.urlopen(request, timeout=const.RESPONSE_TIMEOUT)
      self.status = response.code
      self.responseInfo = response.info()
    except urllib2.HTTPError, e:
      self.logger.warn_('HTTPError({0})'.format(e))
      self.status = e.code
      self.responseInfo = e.info()
      if hasattr(e, 'read'):
        if self.loadError(e):
          return None
      raise (e)
#      if not self.loadError(e):
#        description = "HTTPError. Code=%s" % str(e.code)
#        traceInfo = {'body': e.read()}
#        raise exceptions.ServiceFailure('10000.0',description,traceInfo)
    except urllib2.URLError, e:
      self.logger.warn_('URLError({0})'.format(e))
      if hasattr(e, 'read'):
        if self.loadError(e):
          return None
      raise (e)
      #description = "URL Error. Reason=%s" % e.reason
      #raise exceptions.ServiceFailure('10000.1',description)
    return response

  def HEAD(self, url, headers=None):
    '''Issues a HTTP HEAD request.
    '''
    return self.sendRequest(url, headers=headers, method='HEAD')

  def GET(self, url, headers=None):
    return self.sendRequest(url, headers=headers, method='GET')

  def PUT(self, url, data, headers=None):
    if isinstance(data, dict):
      data = urllib.urlencode(data)
    return self.sendRequest(url, data=data, headers=headers, method='PUT')

  def POST(self, url, data, headers=None):
    if isinstance(data, dict):
      data = urllib.urlencode(data)
    return self.sendRequest(url, data=data, headers=headers, method='POST')

  def DELETE(self, url, data=None, headers=None):
    return self.sendRequest(url, data=data, headers=headers, method='DELETE')


#===============================================================================
class DataOneClient(object):
  '''Implements a simple DataONE client.
  '''

  def __init__(
    self,
    target=const.URL_DATAONE_ROOT,
    userAgent=const.USER_AGENT,
    clientClass=RESTClient,
  ):
    '''Initialize the test client.
    
    :param target: URL of the service to contact.
    :param UserAgent: The userAgent string being passed in the request headers
    :param clientClass: Class that will be used for HTTP connections.
    '''
    self.logger = clientClass.logger
    self.userAgent = userAgent
    self._BASE_DETAIL_CODE = '11000'
    #TODO: Need to define this detailCode base value
    self.client = clientClass(target)

  def exceptionCode(self, extra):
    return "%s.%s" % (self._BASE_DETAIL_CODE, str(extra))

  @property
  def headers(self):
    res = {'User-Agent': self.userAgent, 'Accept': 'text/xml'}
    return res

  def getObjectUrl(self):
    '''Returns the base URL to an object on target.
    '''
    return urlparse.urljoin(self.client.target, const.URL_OBJECT_PATH)

  def getObjectListUrl(self):
    '''Returns the full URL to the object collection on target.
    '''
    return urlparse.urljoin(self.client.target, const.URL_OBJECT_LIST_PATH)

  def getMetaUrl(self):
    '''Return the full URL to the SysMeta object on target.
    '''
    return urlparse.urljoin(self.client.target, const.URL_SYSMETA_PATH)

  def getAccessLogUrl(self):
    '''Returns the full URL to the access log collection on target.
    '''
    return urlparse.urljoin(self.client.target, const.URL_ACCESS_LOG_PATH)

  def getSystemMetadataSchema(self, schemaUrl=const.SYSTEM_METADATA_SCHEMA_URL):
    '''Convenience function to retrieve a copy of the system metadata schema.
    
    :param schemaUrl: The URL from which to load the schema from
    :type schemaUrl: string
    :rtype: unicode copy of the system metadata schema
    '''
    response = self.client.GET(schemaUrl)
    return response

    ## === DataONE API Methods ===
  def get(self, identifier, headers=None):
    '''Retrieve an object from DataONE.
    
    :param identifier: Identifier of object to retrieve
    :rtype: open file stream
    '''
    if len(identifier) == 0:
      self.logger.debug_("Invalid parameter(s)")

    url = urlparse.urljoin(self.getObjectUrl(), urllib.quote(identifier))
    self.logger.debug_("identifier({0}) url({1})".format(identifier, url))
    if headers is None:
      headers = self.headers
    response = self.client.GET(url, headers)

    return response

  def getSystemMetadata(self, identifier, headers=None):
    '''Retrieve system metadata for an object.
    :param identifier: Identifier of the object to retrieve
    :rtype: :class:d1sysmeta.SystemMetadata
    '''
    if len(identifier) == 0:
      self.logger.debug_("Invalid parameter(s)")

    url = urlparse.urljoin(self.getMetaUrl(), urllib.quote(identifier))
    self.logger.debug_("identifier({0}) url({1})".format(identifier, url))
    if headers is None:
      headers = self.headers
    response = self.client.GET(url, headers)
    return response

  def resolve(self, identifier, headers=None):
    url = urlparse.urljoin(self.getObjectListUrl(), identifier, 'resolve/')
    self.logger.debug_("identifier({0}) url({1})".format(identifier, url))
    if headers is None:
      headers = self.headers
    raise exceptions.NotImplemented(self.exceptioncode('1.3'), __name__)
    response = self.client.GET(url, headers)

  def listObjects(
    self,
    startTime=None,
    endTime=None,
    objectFormat=None,
    start=0,
    count=const.MAX_LISTOBJECTS,
    requestFormat="text/xml",
    headers=None
  ):
    '''Perform the MN_replication.listObjects call.
    
    :param startTime:
    :param endTime:
    :param objectFormat:
    :param start:
    :param count:
    
    :rtype: dictionary
    :returns:
    '''
    params = {}
    if start < 0:
      raise exceptions.InvalidRequest(10002, "'start' must be a positive integer")
    params['start'] = start

    try:
      if count < 0:
        raise ValueError
      if count > const.MAX_LISTOBJECTS:
        raise ValueError
    except ValueError:
      raise exceptions.InvalidRequest(
        10002,
        "'count' must be an integer between 1 and {0}".format(const.MAX_LISTOBJECTS)
      )
    else:
      params['count'] = count

    if not (startTime is None and endTime is None):
      try:
        if startTime is not None and endTime is None:
          raise ValueError
        elif endTime is not None and startTime is None:
          raise ValueError
        elif endTime is not None and startTime is not None and startTime >= endTime:
          raise ValueError
      except ValueError:
        raise exceptions.InvalidRequest(
          10002,
          "startTime and endTime must be specified together, must be valid dates and endTime must be after startTime"
        )
      else:
        params['startTime'] = startTime
        params['endTime'] = endTime

    #url = self.getObjectListUrl() + '?pretty&' + urllib.urlencode(params)
    url = "%s?%s" % (self.getObjectListUrl(), urllib.urlencode(params))
    self.logger.debug("%s: url=%s" % (__name__, url))

    if headers is None:
      headers = self.headers
    #TODO: This is stupid. Conflict between requestFormat and headers is here
    # because
    headers['Accept'] = requestFormat

    # Fetch.
    self.logger.debug_("url({0}) headers({1})".format(url, headers))
    response = self.client.GET(url, headers)

    # Deserialize.
    #send the stream to the sax parser rather than laoding hte string
    #xml = response.read()
    if requestFormat == "text/xml":
      self.logger.debug("Deserializing XML")
      return DeserializeObjectListXML(self.logger, response).get()
    if requestFormat == "application/json":
      self.logger.debug("Deserializing JSON")
      res = response.read()
      return json.loads(res)
    self.logger.debug("returning raw response")
    return response.read()

  def getLogRecords(
    self,
    startTime=None,
    endTime=None,
    objectFormat=None,
    start=0,
    count=const.MAX_LISTOBJECTS
  ):

    params = {}

    if start < 0:
      raise exceptions.InvalidRequest(10002, "start must be a positive integer")
    params['start'] = start

    try:
      if count < 1:
        raise ValueError
      if count > const.MAX_LISTOBJECTS:
        raise ValueError
    except ValueError:
      raise exceptions.InvalidRequest(
        10002, "count must be an integer between 1 and {0}".format(const.MAX_LISTOBJECTS)
      )
    params['count'] = count

    try:
      if startTime is not None and endTime is None:
        raise ValueError
      elif endTime is not None and startTime is None:
        raise ValueError
      elif endTime is not None and startTime is not None and startTime >= endTime:
        raise ValueError
    except ValueError:
      raise exceptions.InvalidRequest(
        10002,
        "startTime and endTime must be specified together, must be valid dates and endTime must be after startTime"
      )
    else:
      params['startTime'] = startTime
      params['endTime'] = endTime

    url = self.getAccessLogUrl() + '?' + urllib.urlencode(params)

    headers = self.headers
    headers['Accept'] = 'text/xml'

    self.logger.debug_("url({0}) headers({1})".format(url, headers))

    # Fetch.
    response = self.client.GET(url, headers)

    # Deserialize.
    #xml = response.read()
    return DeserializeLogRecords(self.logger, response).get()

  def create(self, identifier, object_bytes, sysmeta_bytes):
    # Parameter validation.
    if len(identifier) == 0 or len(object_bytes) == 0 or len(sysmeta_bytes) == 0:
      self.logger.debug_("Invalid parameter(s)")

      # Create MIME-multipart Mixed Media Type body.
    files = []
    files.append(('object', 'object', object_bytes))
    files.append(('systemmetadata', 'systemmetadata', sysmeta_bytes))
    content_type, mime_doc = d1common.upload.encode_multipart_formdata([], files)

    # Send REST POST call to register object.

    headers = {'Content-Type': content_type, 'Content-Length': str(len(mime_doc)), }

    crud_create_url = urlparse.urljoin(self.getObjectUrl(), urllib.quote(identifier, ''))

    #self.logger.debug_('~' * 79)
    #self.logger.debug_('REST call: {0}'.format(crud_create_url))
    #self.logger.debug_('~' * 10)
    #self.logger.debug_(headers)
    #self.logger.debug_('~' * 10)
    #self.logger.debug_(mime_doc)
    #self.logger.debug_('~' * 79)

    self.logger.debug_(
      "url({0}) identifier({1}) headers({2})".format(
        crud_create_url, identifier, headers
      )
    )

    try:
      res = self.client.POST(crud_create_url, data=mime_doc, headers=headers)
      res = '\n'.join(res)
      if res != r'OK':
        raise Exception(res)
    except Exception as e:
      logging.error('REST call failed: {0}'.format(str(e)))
      raise

    #===============================================================================
    #<?xml version='1.0' encoding='UTF-8'?>
    #<d1:response xmlns:d1="http://ns.dataone.org/core/objects">
    #  <start>0</start>
    #  <count>243</count>
    #  <total>243</total>
    #  <objectInfo>
    #    <checksum>5f173b60a36d4ce42e90b1698dcb10631de6dee0</checksum>
    #    <dateSysMetadataModified>2010-04-26T07:23:42.380413</dateSysMetadataModified>
    #    <format>eml://ecoinformatics.org/eml-2.0.0</format>
    #    <identifier>hdl:10255/dryad.1099/mets.xml</identifier>
    #    <size>3636</size>
    #  </objectInfo>
    #</d1:response>


class DeserializeObjectListXML():
  '''Deserializes XML form of an ObjectList.
  '''

  def __init__(self, logger, d):
    '''
    :param logger:
    :param d: unicode, string, or file object open for reading
    '''
    self.r = {'objectInfo': []}
    self.logger = logger
    self.d = d

  def get(self):
    try:
      if isinstance(self.d, basestring):
        dom = xml.dom.minidom.parseString(self.d)
      else:
        dom = xml.dom.minidom.parse(self.d)
      self.handleObjectList(dom)
      return self.r
    except (TypeError, AttributeError, ValueError):
      self.logger.error_("Could not deserialize XML result")
      raise

  def getText(self, nodelist):
    rc = []
    for node in nodelist:
      if node.nodeType == node.TEXT_NODE:
        rc.append(node.data)
    return ''.join(rc)

  def handleObjectList(self, dom):
    # start, count and total
    self.handleObjectStart(dom.getElementsByTagName("start")[0])
    self.handleObjectCount(dom.getElementsByTagName("count")[0])
    self.handleObjectTotal(dom.getElementsByTagName("total")[0])
    objects = dom.getElementsByTagName("objectInfo")
    self.handleObjects(objects)

  def handleObjects(self, objects):
    for object in objects:
      self.handleObject(object)

  def handleObject(self, object):
    objectInfo = {}
    self.handleObjectChecksum(objectInfo, object.getElementsByTagName("checksum")[0])
    self.handleObjectDateSysMetadataModified(
      objectInfo, object.getElementsByTagName(
        "dateSysMetadataModified"
      )[0]
    )
    self.handleObjectFormat(objectInfo, object.getElementsByTagName("format")[0])
    self.handleObjectIdentifier(objectInfo, object.getElementsByTagName("identifier")[0])
    self.handleObjectSize(objectInfo, object.getElementsByTagName("size")[0])
    self.r['objectInfo'].append(objectInfo)

    # Header.

  def handleObjectStart(self, title):
    self.r['start'] = int(self.getText(title.childNodes))

  def handleObjectCount(self, title):
    self.r['count'] = int(self.getText(title.childNodes))

  def handleObjectTotal(self, title):
    self.r['total'] = int(self.getText(title.childNodes))

  # Objects.

  def handleObjectChecksum(self, objectInfo, checksum):
    objectInfo['checksum'] = self.getText(checksum.childNodes)

  def handleObjectDateSysMetadataModified(self, objectInfo, dateSysMetadataModified):
    objectInfo['dateSysMetadataModified'] = self.getText(
      dateSysMetadataModified.childNodes
    )

  def handleObjectFormat(self, objectInfo, format):
    objectInfo['format'] = self.getText(format.childNodes)

  def handleObjectIdentifier(self, objectInfo, identifier):
    objectInfo['identifier'] = self.getText(identifier.childNodes)

  def handleObjectSize(self, objectInfo, size):
    objectInfo['size'] = int(self.getText(size.childNodes))


#===============================================================================
class DeserializeLogRecords():
  '''Deserialize log records from XML format.
  '''

  def __init__(self, logger, d):
    '''
    :param logger:
    :param d: unicode, string, or file object open for reading
    '''
    self.r = {'logRecord': []}
    self.logger = logger
    self.d = d

  def get(self):
    try:
      if isinstance(self.d, basestring):
        dom = xml.dom.minidom.parseString(self.d)
      else:
        dom = xml.dom.minidom.parse(self.d)
      self.handleLogRecords(dom)
      return self.r
    except (TypeError, AttributeError, ValueError):
      self.logger.error_("Could not deserialize XML result")
      raise

  def getText(self, nodelist):
    rc = []
    for node in nodelist:
      if node.nodeType == node.TEXT_NODE:
        rc.append(node.data)
    return ''.join(rc)

  def handleLogRecords(self, dom):
    # start, count and total
    self.handleObjectStart(dom.getElementsByTagName("start")[0])
    self.handleObjectCount(dom.getElementsByTagName("count")[0])
    self.handleObjectTotal(dom.getElementsByTagName("total")[0])
    objects = dom.getElementsByTagName("logRecord")
    self.handleObjects(objects)

  def handleObjects(self, objects):
    for object in objects:
      self.handleObject(object)

  def handleObject(self, object):
    logRecord = {}
    self.handleObjectIdentifier(logRecord, object.getElementsByTagName("identifier")[0])
    self.handleObjectOperationType(
      logRecord, object.getElementsByTagName("operationType")[0]
    )
    self.handleObjectRequestorIdentity(
      logRecord, object.getElementsByTagName(
        "requestorIdentity"
      )[0]
    )
    self.handleObjectAccessTime(logRecord, object.getElementsByTagName("accessTime")[0])
    self.r['logRecord'].append(logRecord)

    # Header.

  def handleObjectStart(self, title):
    self.r['start'] = int(self.getText(title.childNodes))

  def handleObjectCount(self, title):
    self.r['count'] = int(self.getText(title.childNodes))

  def handleObjectTotal(self, title):
    self.r['total'] = int(self.getText(title.childNodes))

  # Log Records.

  def handleObjectIdentifier(self, logRecord, identifier):
    logRecord['identifier'] = self.getText(identifier.childNodes)

  def handleObjectOperationType(self, logRecord, operationType):
    logRecord['operationType'] = self.getText(operationType.childNodes)

  def handleObjectRequestorIdentity(self, logRecord, requestorIdentity):
    logRecord['requestorIdentity'] = self.getText(requestorIdentity.childNodes)

  def handleObjectAccessTime(self, logRecord, accessTime):
    logRecord['accessTime'] = self.getText(accessTime.childNodes)
