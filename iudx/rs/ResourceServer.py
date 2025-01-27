"""Module doc string. Leave empty for now.

ResourceServer.py
"""
import json
from datetime import datetime, timedelta
from typing import TypeVar, Generic, Any, List, Dict

from iudx.common.HTTPEntity import HTTPEntity
from iudx.common.HTTPResponse import HTTPResponse

from iudx.rs.ResourceQuery import ResourceQuery
from iudx.rs.ResourceResult import ResourceResult

from iudx.auth.Token import Token

import multiprocessing


class ResourceServer():
    """Abstract class for Resource Server. Helps to create a modular
       interface for the API to implement queries.
    """

    def __init__(self, rs_url: str=None, token: str=None, token_obj: Token=None,
                 headers: Dict[str, str]=None):
        """ResourceServer base class constructor
        """
        # Request access token
        if token is None and token_obj is not None:
            token = token_obj.request_token()

        self.url: str = rs_url
        self.token: str = token
        if (headers is not None):
            self.headers: Dict[str, str] = headers
        else:
            self.headers = {}
        self.pool = multiprocessing.Pool(processes=multiprocessing.cpu_count())

        if self.token is not None:
            self.headers["token"] = self.token
        return

    def status(self) -> bool:
        """Pydoc heading.

        Args:
            argument (argument-type): argument-description
        Returns:
            returned-varaible (returned-varaible-type): return-variable-description
        """
        return False

    def parse_response(self, responses: List[HTTPResponse]) -> List[ResourceResult]:
        """Parse responses

       Args:
           responses (argument-type): response fetched for the query
       Returns:
           parsed response
       """
        rs_results = []
        for response in responses:
            rs_result = ResourceResult()

            if response.get_status_code() == 401:
                raise RuntimeError("Not Authorized: Invalid Credentials")

            elif response.get_status_code() == 200:
                result_data = response.get_json()
                rs_result.type = result_data["type"]
                rs_result.title = result_data["title"]
                rs_result.results = result_data["results"]
                if ("offset" in result_data.keys()):
                    rs_result.offset = result_data["offset"]
                if ("limit" in result_data.keys()):
                    rs_result.limit = result_data["limit"]
                if ("totalHits" in result_data.keys()):
                    rs_result.totalHits = result_data["totalHits"]
                rs_results.append(rs_result)

        return rs_results

    def get_data_using_get(self, queries: List[ResourceQuery]) -> List[ResourceResult]:
        """ Get data using HTTP Get 

        Args:
            queries (List[ResourceQuery]): A list of query objects of 
            ResourceQuery class.
        Returns:
            rs_results (List[ResourceResult]): returns a list of 
                ResourceResult object.
        """
        url = self.url + "/entities"


        rs_results = []
        zipped_url = []
        offset = None
        limit = None
        for query in queries:
            offset, limit = query.get_offset_limit()
            new_url = url
            if (query._is_property_search):
                url +=  query.get_query_for_get()
            if offset is not None and limit is not None:
                new_url = url + "&offset=" + str(offset) + "&limit=" + str(limit)
            response = HTTPEntity().get(url=new_url, headers=self.headers)
            rs_results += self.parse_response([response])
        return rs_results




    def get_data(self, queries: List[ResourceQuery]) -> List[ResourceResult]:
        """Method to post the request for geo, temporal, property, add filters
            and make complex query.

        Args:
            queries (List[ResourceQuery]): A list of query objects of 
            ResourceQuery class.
        Returns:
            rs_results (List[ResourceResult]): returns a list of 
                ResourceResult object.
        """
        url = self.url + "/temporal/entityOperations/query"

        rs_results = []
        zipped_url = []
        offset = None
        limit = None
        for query in queries:
            offset, limit = query.get_offset_limit()
            new_query = query.get_query()
            new_url = url
            if offset is not None and limit is not None:
                new_url = url + "?offset=" + str(offset) + "&limit=" + str(limit)
            zipped_url.append((new_url, new_query, self.headers))

        responses: List[HTTPResponse] = self.pool.starmap(
            HTTPEntity().post,
            zipped_url
            )
        rs_results = self.parse_response(responses)
        return rs_results


    def get_latest(self, queries: List[ResourceQuery]) -> List[ResourceResult]:
        """Method to get the request for latest resource data.

        Args:
            query (ResourceQuery): A query object of ResourceQuery class.
        Returns:
            rs_result (ResourceResult): returns a ResourceResult object.
        """
        base_url = self.url + "/entities"

        zipped_url = []
        for query in queries:
            url = base_url + query.latest_search()
            zipped_url.append((url, self.headers))

        responses: List[HTTPResponse] = self.pool.starmap(
            HTTPEntity().get,
            zipped_url
            )

        rs_results = []
        for response in responses:
            rs_result = ResourceResult()

            if response.get_status_code() == 401:
                raise RuntimeError("Not Authorized: Invalid Credentials")

            elif response.get_status_code() == 200:
                result_data = response.get_json()
                rs_result.type = result_data["type"]
                rs_result.title = result_data["title"]
                rs_result.results = result_data["results"]
                rs_results.append(rs_result)

        return rs_results
