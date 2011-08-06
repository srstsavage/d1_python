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
:mod:`exception_handler`
=========================

:Synopsis:
  Catch, log and serialize DataONE exceptions.
  
  Implements the system for returning information about exceptional conditions
  (errors) as described in Raised by MN and CN APIs
  http://mule1.dataone.org/ArchitectureDocs/html

  Exceptions:
  
  AuthenticationTimeout
  IdentifierNotUnique
  InsufficientResources
  InvalidCredentials
  InvalidRequest
  InvalidSystemMetadata
  InvalidToken
  NotAuthorized
  NotFound
  NotImplemented
  ServiceFailure
  UnsupportedMetadataType
  UnsupportedType
  
  These are not related to Python's exception system.

.. moduleauthor:: Roger Dahl
'''

# Stdlib.
import inspect
import logging
import os
import sys
import traceback

# 3rd party.
import d1_common.ext.mimeparser

# Django.
from django.http import HttpResponse

# MN API.
import d1_common.types.exceptions
import d1_common.types.exception_serialization

# App.
import mn.util as util
import detail_codes
import settings

# Get an instance of a logger.
logger = logging.getLogger(__name__)


class exception_handler():
  def process_exception(self, request, exception):
    #return None

    # An exception within this function causes a Django exception page
    # to be returned if debugging is on and a generic 500 otherwise.

    # Log the exception.
    util.log_exception(10)

    #    # When debugging from a web browser, we want to return None to get Django's
    #    # extremely useful exception page.
    #    if settings.GMN_DEBUG == True and request.META['HTTP_USER_AGENT'] != d1_common.const.USER_AGENT:
    #      return None

    # If the exception is an EnvironmentError (file IO or OS error), we
    # translate it to a DataONE ServiceFailure error that includes details
    # of the error.
    if isinstance(exception, EnvironmentError):
      errno, strerror = exception
      err_msg += 'I/O error({0}): {1}'.format(errno, strerror)
      exception = d1_common.types.exceptions.ServiceFailure(0, err_msg)

    # If the exception is a DataONE exception, we serialize it out.
    if isinstance(exception, d1_common.types.exceptions.DataONEException):
      # Add trace information to the given DataONE exception.
      exception.detailCode = str(
        detail_codes.dataone_exception_to_detail_code().detail_code(
          request, exception
        )
      )
      exception.traceInformation = util.traceback_to_text()
      exception_serializer = d1_common.types.exception_serialization.DataONEExceptionSerialization(
        exception
      )
      exception_serialized, content_type = exception_serializer.serialize(
        request.META.get(
          'HTTP_ACCEPT', None
        )
      )
      return HttpResponse(
        exception_serialized,
        status=exception.errorCode,
        mimetype=content_type
      )

      # Add trace information to the given DataONE exception.
      exception.detailCode = str(
        detail_codes.dataone_exception_to_detail_code().detail_code(
          request, exception
        )
      )
      exception.traceInformation = util.traceback_to_text()
      exception_serializer = d1_common.types.exception_serialization.DataONEExceptionSerialization(
        exception
      )
      exception_serialized, content_type = exception_serializer.serialize(
        request.META.get(
          'HTTP_ACCEPT', None
        )
      )
      return HttpResponse(
        exception_serialized,
        status=exception.errorCode,
        mimetype=content_type
      )

    # If we get here, we got an unexpected exception. Wrap it in a DataONE exception.
    exception = d1_common.types.exceptions.ServiceFailure(0, '', '')
    exception.detailCode = str(
      detail_codes.dataone_exception_to_detail_code().detail_code(
        request, exception
      )
    )
    exception.traceInformation = util.traceback_to_text()
    exception_serializer = d1_common.types.exception_serialization.DataONEExceptionSerialization(
      exception
    )
    exception_serialized, content_type = exception_serializer.serialize(
      request.META.get(
        'HTTP_ACCEPT', None
      )
    )
    return HttpResponse(
      exception_serialized,
      status=exception.errorCode,
      mimetype=content_type
    )
