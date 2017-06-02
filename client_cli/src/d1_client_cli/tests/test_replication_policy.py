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

import StringIO
import sys
import unittest

import d1_client_cli.impl.replication_policy as replication_policy

#===============================================================================


class TestReplicationPolicy(unittest.TestCase):
  def setUp(self):
    pass

  def test_0010(self):
    """The replication policy object can be instantiated"""
    self.assertNotEquals(None, replication_policy.ReplicationPolicy())

  def test_0020(self):
    """After instatiation, get_preferred() returns empty list."""
    s = replication_policy.ReplicationPolicy()
    self.assertFalse(len(s.get_preferred()))

  def test_0030(self):
    """After instatiation, get_blocked() returns empty list."""
    s = replication_policy.ReplicationPolicy()
    self.assertFalse(len(s.get_blocked()))

  def test_0040(self):
    """add_preferred() retains added MN"""
    s = replication_policy.ReplicationPolicy()
    s.add_preferred(['preferred_mn_1', 'preferred_mn_2', 'preferred_mn_3'])
    self.assertEqual(3, len(s.get_preferred()))
    self.assertTrue('preferred_mn_1' in s.get_preferred())
    self.assertTrue('preferred_mn_2' in s.get_preferred())
    self.assertTrue('preferred_mn_3' in s.get_preferred())

  def test_0050(self):
    """add_blocked() retains added MN"""
    s = replication_policy.ReplicationPolicy()
    s.add_blocked(['blocked_mn_1', 'blocked_mn_2', 'blocked_mn_3'])
    self.assertEqual(3, len(s.get_blocked()))
    self.assertTrue('blocked_mn_1' in s.get_blocked())
    self.assertTrue('blocked_mn_2' in s.get_blocked())
    self.assertTrue('blocked_mn_3' in s.get_blocked())

  def test_0060(self):
    """add_preferred() followed by add_blocked() switches item from preferred to blocked"""
    s = replication_policy.ReplicationPolicy()
    s.add_preferred(['preferred_mn'])
    self.assertFalse('preferred_mn' in s.get_blocked())
    s.add_blocked(['preferred_mn'])
    self.assertTrue('preferred_mn' in s.get_blocked())

  def test_0070(self):
    """add_blocked() followed by add_preferred() switches item from blocked to preferred"""
    s = replication_policy.ReplicationPolicy()
    s.add_preferred(['blocked_mn'])
    self.assertFalse('blocked_mn' in s.get_blocked())
    s.add_blocked(['blocked_mn'])
    self.assertTrue('blocked_mn' in s.get_blocked())

  def test_0080(self):
    """Replication is allowed by default."""
    s = replication_policy.ReplicationPolicy()
    self.assertTrue(s.get_replication_allowed())

  def test_0090(self):
    """set_replication_allowed() is retained and can be retrieved with get_replication_policy()"""
    s = replication_policy.ReplicationPolicy()
    s.set_replication_allowed(True)
    self.assertTrue(s.get_replication_allowed())
    s.set_replication_allowed(False)
    self.assertFalse(s.get_replication_allowed())

  def test_0100(self):
    """number_of_replicas can be retrieved and is 0 by default"""
    s = replication_policy.ReplicationPolicy()
    self.assertEqual(3, s.get_number_of_replicas()) # 3 by default

  def test_0110(self):
    """set_number_of_replicas() is retained and can be retrieved with get_number_of_replicas()"""
    s = replication_policy.ReplicationPolicy()
    s.set_number_of_replicas(5)
    self.assertEqual(5, s.get_number_of_replicas())
    s.set_number_of_replicas(10)
    self.assertEqual(10, s.get_number_of_replicas())

  def test_0120(self):
    """set_replication_allowed(False) implicitly sets number_of_replicas to 0"""
    s = replication_policy.ReplicationPolicy()
    s.set_number_of_replicas(5)
    self.assertEqual(5, s.get_number_of_replicas())
    s.set_replication_allowed(False)
    self.assertEqual(0, s.get_number_of_replicas())

  def test_0130(self):
    """set_number_of_replicas(0) implicitly sets replication_allowed to False"""
    s = replication_policy.ReplicationPolicy()
    s.set_replication_allowed(True)
    self.assertTrue(s.get_replication_allowed())
    s.set_number_of_replicas(0)
    self.assertFalse(s.get_replication_allowed())

  def test_0140(self):
    """print_replication_policy() is available and appears to work"""
    s = replication_policy.ReplicationPolicy()
    s.add_preferred(['preferred_mn_1'])
    s.add_preferred(['preferred_mn_2'])
    s.add_preferred(['preferred_mn_3'])
    s.add_blocked(['blocked_mn_1'])
    s.add_blocked(['blocked_mn_2'])
    s.add_blocked(['blocked_mn_3'])
    s.set_number_of_replicas(5)
    s.set_replication_allowed(True)
    old = sys.stdout
    sys.stdout = StringIO.StringIO()
    # run print
    s.print_replication_policy()
    ## release stdout
    out = sys.stdout.getvalue()
    sys.stdout = old
    # validate
    self.assertTrue(len(out) > 100)
    self.assertTrue('preferred member nodes' in out)
    self.assertTrue('blocked member nodes' in out)

  def test_0150(self):
    """clear() sets everything to default"""
    s = replication_policy.ReplicationPolicy()
    s.add_preferred(['preferred_mn_1'])
    s.add_preferred(['preferred_mn_2'])
    s.add_blocked(['blocked_mn_1'])
    s.add_blocked(['blocked_mn_2'])
    s.set_number_of_replicas(5)
    s.set_replication_allowed(True)
    s.clear()
    self.assertTrue(not len(s.get_preferred()))
    self.assertTrue(not len(s.get_blocked()))
    self.assertTrue(s.get_replication_allowed())
    self.assertEqual(s.get_number_of_replicas(), 3)