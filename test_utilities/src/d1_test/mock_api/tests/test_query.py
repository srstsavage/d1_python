# This work was created by participants in the DataONE project, and is
# jointly copyrighted by participating institutions in DataONE. For
# more information on DataONE, see our web site at http://dataone.org.
#
#   Copyright 2009-2019 DataONE
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

import pytest
import responses

import d1_common.types.exceptions

import d1_test.d1_test_case
import d1_test.mock_api.solr_query


class TestMockQuery(d1_test.d1_test_case.D1TestCase):
    @responses.activate
    def test_1000(self, cn_client_v1_v2):
        """mock_api.query() returns a JSON doc with expected structure."""
        d1_test.mock_api.solr_query.add_callback(d1_test.d1_test_case.MOCK_CN_BASE_URL)
        resp_dict = cn_client_v1_v2.query("query_engine", "query_string")
        assert isinstance(resp_dict, dict)
        assert "User-Agent" in resp_dict["header_dict"]
        del resp_dict["header_dict"]["User-Agent"]
        expected_dict = {
            "body_base64": "PG5vIGJvZHk+",
            "query_dict": {},
            "header_dict": {
                "Connection": "keep-alive",
                "Charset": "utf-8",
                "Accept-Encoding": "gzip, deflate",
                "Accept": "*/*",
            },
        }
        assert resp_dict == expected_dict

    @responses.activate
    def test_1010(self, cn_client_v1_v2):
        """mock_api.query(): Passing a trigger header triggers a DataONEException."""
        d1_test.mock_api.solr_query.add_callback(d1_test.d1_test_case.MOCK_CN_BASE_URL)
        with pytest.raises(d1_common.types.exceptions.NotAuthorized):
            cn_client_v1_v2.query(
                "query_engine", "query_string", vendorSpecific={"trigger": "401"}
            )
