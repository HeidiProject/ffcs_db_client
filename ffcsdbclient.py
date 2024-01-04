# Standard Libraries
from datetime import datetime
import json
import random
import re
import os
import string
from typing import List, Optional, Dict, Union, Any

# Third-Party Libraries
from bson import ObjectId
import requests

################################
# NOTE: If changes are made to location or port of database or database name, they also needs to be incorporated
# and deployed in other software that uses them, like ZMQ server/clients deployed in Docker containers

class Settings:
    pass

def load_env_variables(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                value = value.strip('"').strip("'")
                setattr(Settings, key, value)

load_env_variables('.env')

### Function to generate a random string
def random_string(length=10):
    return ''.join(random.choice(string.ascii_letters) for _ in range(length))

### Function to generate a int with 5 digits
def random_five_digit_str() -> str:
    return str(random.randint(10000, 99999))

class MockUpdateResult:
    def __init__(self, matched_count: int, modified_count: int, upserted_id: Optional[str], raw_result: dict):
        self.matched_count = matched_count
        self.modified_count = modified_count
        self.upserted_id = upserted_id
        self.raw_result = raw_result

    def to_dict(self):
        return {
            "matched_count": self.matched_count,
            "modified_count": self.modified_count,
            "upserted_id": self.upserted_id,
            "raw_result": self.raw_result,
        }

class MockInsertOneResult:
    """
    Mock class for InsertOneResult oject.
    """

    def __init__(self, acknowledged, inserted_id):
        self.acknowledged = acknowledged
        self.inserted_id = ObjectId(inserted_id)

class MockUpdateOneResultOld:
    """
    Mock class for UpdateOneResult oject.
    """

    def __init__(self, nModified, ok, n):
        self.nModified = nModified
        self.ok = ok
        self.n = n

    def to_dict(self):
        return {
            "nModified": self.nModified,
            "ok": self.ok,
            "n": self.n,
        }

class CursorMock:
    """
    This mock now supports chaining methods like cursor.sort('userAccount').limit(10).skip(5).
    Note: Methods like distinct() can be implemented, but it would require a bit more complexity and knowing the field for which distinct values are required.
    """

    def __init__(self, data):
        self.original_data = data
        self.data = data.copy()
        self.index = 0

    def __iter__(self):
        return self

    def next(self):
        if self.index < len(self.data):
            item = self.data[self.index]
            self.index += 1
            return item
        else:
            raise StopIteration

    def rewind(self):
        self.index = 0
        return self

    def count(self, with_limit_and_skip=False):
        if with_limit_and_skip:
            return len(self.data)
        return len(self.original_data)

    def sort(self, key, direction=1):
        self.data.sort(key=lambda x: x[key], reverse=(direction == -1))
        return self

    def skip(self, n):
        self.data = self.data[n:]
        return self

    def limit(self, n):
        self.data = self.data[:n]
        return self

    def batch_size(self, size):
        ### Mocking batch size as it won't make much sense here without a genuine connection
        return self

    def close(self):
        ### As this is a mock, there isn't anything to "close", but we can mimic the behavior
        self.data = []
        self.index = 0

    @property
    def alive(self):
        return self.index < len(self.data)

def convert_strings_to_objectids(input_data):
    """
    Function to identify all strings in a document or list of documents that resemble the string ob an ObjectID
    and convert them to ObjectIDs.
    """

    ### Check if the given string matches ObjectId pattern
    def is_objectid_like(s):
        pattern = r"^[a-f\d]{24}$"
        return bool(re.match(pattern, s))

    ### Recursive function to search and replace ObjectID-like strings
    def search_and_replace(data):
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and is_objectid_like(value):
                    data[key] = ObjectId(value)
                elif isinstance(value, (dict, list)):
                    search_and_replace(value)
        elif isinstance(data, list):
            for index, item in enumerate(data):
                if isinstance(item, str) and is_objectid_like(item):
                    data[index] = ObjectId(item)
                elif isinstance(item, (dict, list)):
                    search_and_replace(item)

    ### If the input data is not empty, process it
    if input_data:
        search_and_replace(input_data)

    return input_data


def convert_objects_to_serializable(data):
    """
    Converts datetime and ObjectId objects in a dictionary to a serializable form.

    Args:
        data (dict): The input dictionary.

    Returns:
        dict: A new dictionary with datetime and ObjectId objects converted.
    """
    if not isinstance(data, dict):
        raise ValueError("Input must be a dictionary.")

    def serialize_object(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, ObjectId):
            return str(obj)  # Convert ObjectId to string
        return obj

    def convert_recursive(obj):
        if isinstance(obj, dict):
            return {key: convert_recursive(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [convert_recursive(item) for item in obj]
        else:
            return serialize_object(obj)

    return convert_recursive(data)


class ffcsdbclient(object):
    def __init__(self, base_url=Settings.BASE_URL):
        self.base_url = base_url

    ### FETCH_TAG delete_by_id
    def delete_by_id(self, collection: str, doc_id: str) -> dict:
        response = requests.delete(f"{self.base_url}/delete_by_id/{collection}/{doc_id}")

        try:
            ### Get the response data
            delete_info = response.json()
            return delete_info
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG delete_by_id

    ### FETCH_TAG delete_by_query
    def delete_by_query(self, collection: str, query: dict) -> dict:
        response = requests.post(f"{self.base_url}/delete_by_query/{collection}", json=query)

        try:
            ### Get the response data
            delete_info = response.json()
            return delete_info
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG delete_by_query

    ### FETCH_TAG merge_two_dictionaries
    def __merge_two_dictionaries(self, d1, d2):
        """
        Function added for python 2.* backwards compatybility.
        In Python3 merging two dicts can be done with {**d1, **d2}
        """

        out = copy.deepcopy(d1)
        out.update(d2)
        return out
    ### FETCH_TAG merge_two_dictionaries

    ### FETCH_TAG check_if_db_connected
    def check_if_db_connected(self) -> bool:
        """
        Checks the connection to the database by making a GET request to the server's /check_if_db_connected endpoint.
    
        Returns:
            bool: True if the connection is successful, otherwise raises an Exception.
    
        Raises:
            Exception: If the response status code is not 200 or other errors occur during the request.
        """
        try:
            response = requests.get(f"{self.base_url}/check_if_db_connected")
            response.raise_for_status()
        except Exception as e:
            ### Handle exceptions and raise a detailed error message
            raise Exception(f"Failed to check DB connection: {e}, Response Content: {response.content if 'response' in locals() else ''}")
        
        ### Return the parsed JSON content
        return json.loads(response.content)
    ### FETCH_TAG check_if_db_connected

    ### FETCH_TAG get_collection
    def __get_collection(self, name: str) -> str:
        response = requests.get(f"{self.base_url}/get_collection/{name}")

        try:
            ### Get the response data
            collection_info = response.json()
            return collection_info['collection']
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG get_collection

    ### FETCH_TAG get_libraries
    def get_libraries(self) -> list:
        """
        Sends a GET request to the FastAPI server to retrieve all libraries.
    
        This method sends a request to the FastAPI server's '/get_libraries/' endpoint and processes the JSON response to extract library information. 
        In case of an error during the request or while parsing the JSON response, it handles the exception and returns an empty list.
    
        Returns:
            list: A list of dictionaries, each representing a library. Returns an empty list in case of an error.
    
        Raises:
            Exception: Captures any exception that occurs during the request or JSON parsing and logs the error message.
        """
        response = requests.get(f"{self.base_url}/get_libraries/")
    
        try:
            libraries = response.json()
            return libraries
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return []
    ### FETCH_TAG get_libraries

    ### FETCH_TAG get_campaign_libraries
    def get_campaign_libraries(self, user: str, campaign_id: str) -> list:
        """
        Sends a POST request to the FastAPI server to retrieve all libraries associated with a specific user and campaign ID.
    
        This method constructs a payload with user and campaign identifiers, sends a POST request to the server, 
        and processes the JSON response to extract library information. If the response cannot be parsed or an error 
        occurs during the request, it handles the exception and returns an empty list.
    
        Args:
            user (str): The identifier of the user account.
            campaign_id (str): The identifier of the campaign.
    
        Returns:
            list: A list of dictionaries, each representing a library. Returns an empty list in case of an error.
    
        Raises:
            Exception: Captures any exception that occurs during the request or JSON parsing and logs the error message.
        """
        payload = {
            'user': user,
            'campaign_id': campaign_id
        }
        try:
            response = requests.post(f"{self.base_url}/get_campaign_libraries/", json=payload)
            libraries = response.json()
            return libraries
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return []
    ### FETCH_TAG get_campaign_libraries

    ### FETCH_TAG get_plate
    def get_plate(self, user_account: str, campaign_id: int, plate_id: int) -> dict:
        response = requests.get(f"{self.base_url}/get_plate/{user_account}/{campaign_id}/{plate_id}")

        try:
            ### Get the response data
            plate_info = response.json()
            return plate_info
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG get_plate

    ### FETCH_TAG get_plates
    def get_plates(self, user_account: str, campaign_id: int) -> list:
        response = requests.get(f"{self.base_url}/get_plates/{user_account}/{campaign_id}")

        try:
            ### Get the response data
            plates_info = response.json()
            datetime_fields = ['createdOn', 'lastImaged', 'soakExportTime']
            datetime_format = "%Y-%m-%dT%H:%M:%S"

            for item in plates_info:
                for field in datetime_fields:
                    if field in item and item[field] is not None:
                        dt_str = item[field]
                        if '.' in dt_str:
                            ### Handles datetime with microseconds
                            datetime_format = "%Y-%m-%dT%H:%M:%S.%f"
                            item[field] = datetime.strptime(dt_str, datetime_format)
                        else:
                            ### Handles datetime without microseconds
                            datetime_format = "%Y-%m-%dT%H:%M:%S"
                            item[field] = datetime.strptime(dt_str, datetime_format)
            return plates_info
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG get_plates

    ### FETCH_TAG get_campaigns
    def get_campaigns(self, user_account: str) -> list:
        response = requests.get(f"{self.base_url}/get_campaigns/{user_account}")

        try:
            ### Get the response data
            campaigns_info = response.json()
            return campaigns_info
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG get_campaigns

    ### FETCH_TAG add_plate
    def add_plate(self, plate: dict) -> dict:
        plate = convert_objects_to_serializable(plate)
        response = requests.post(f"{self.base_url}/add_plate/", json=plate)

        try:
            ### Get the response data
            plate_info = response.json()
            return plate_info
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG add_plate

    ### FETCH_TAG add_well
    def add_well(self, well: dict) -> dict:
        well = convert_objects_to_serializable(well)
        response = requests.post(f"{self.base_url}/add_well/", json=well)

        try:
            ### Get the response data
            well_info = response.json()
            result = MockInsertOneResult(well_info["acknowledged"], well_info["inserted_id"])
            return result
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG add_well

    ### FETCH_TAG insert_campaign_library
    def insert_campaign_library(self, campaign_library: dict) -> MockInsertOneResult:
        """
        Sends a POST request to the FastAPI server to insert a new campaign library.
    
        This method constructs a payload with the campaign library data, sends a POST request to the server, 
        and processes the JSON response to extract the insertion result. It returns an instance of MockInsertOneResult.
        If the response cannot be parsed or an error occurs during the request, it handles the exception and returns None.
    
        Args:
            campaign_library (dict): A dictionary representing the campaign library data to be inserted.
    
        Returns:
            MockInsertOneResult: An object representing the result of the insertion operation.
    
        Raises:
            Exception: Captures any exception that occurs during the request or JSON parsing and logs the error message.
        """
        campaign_library = convert_objects_to_serializable(campaign_library)
        try:
            response = requests.post(f"{self.base_url}/insert_campaign_library/", json=campaign_library)
            campaign_library_info = response.json()
            return MockInsertOneResult(campaign_library_info["acknowledged"], campaign_library_info["inserted_id"])
        except Exception as e:
            print(f"Could not process the request or parse JSON: {e}")
            return None
    ### FETCH_TAG insert_campaign_library

    ### FETCH_TAG add_wells
    def add_wells(self, list_of_wells: List[dict]) -> dict:
        list_of_wells = [convert_objects_to_serializable(item) for item in list_of_wells]
        response = requests.post(f"{self.base_url}/add_wells/", json=list_of_wells)
        try:
            ### Get the response data
            wells_info = response.json()
            return wells_info ### old add_wells from ffcsdbclient has not return (=null), which is correctly passed through the API here
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG add_wells

    ### FETCH_TAG update_by_object_id
    def update_by_object_id(self, user: str, campaign_id: int, collection: str, doc_id: str, **kwargs: dict) -> dict:
        
        kwargs = convert_objects_to_serializable(kwargs)

        response = requests.put(f"{self.base_url}/update_by_object_id",
                                json={
                                    "user_account": user,
                                    "campaign_id": campaign_id,
                                    "collection": collection,
                                    "doc_id": doc_id,
                                    "kwargs": kwargs
                                })

        try:
            ### Get the response data
            result = response.json()
            return result
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG update_by_object_id

    ### FETCH_TAG update_by_object_id_NEW
    def update_by_object_id_NEW(self, user: str, campaign_id: int, collection: str, doc_id: str, **kwargs: dict) -> dict:

        kwargs = convert_objects_to_serializable(kwargs)

        response = requests.put(f"{self.base_url}/update_by_object_id_NEW",
                                json={
                                    "user_account": user,
                                    "campaign_id": campaign_id,
                                    "collection": collection,
                                    "doc_id": doc_id,
                                    "kwargs": kwargs
                                })

        try:
            ### Get the response data
            result = response.json()
            return result
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG update_by_object_id_NEW

    ### FETCH_TAG is_plate_in_database
    def is_plate_in_database(self, plate_id: str) -> bool:
        response = requests.get(f"{self.base_url}/is_plate_in_database/{plate_id}")
        try:
            ### Get the response data
            result = response.json()
            return result["exists"]
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG is_plate_in_database

    ### FETCH_TAG get_unselected_plates
    def get_unselected_plates(self, user_account: str) -> List[dict]:
        response = requests.get(f"{self.base_url}/get_unselected_plates/{user_account}")
        try:
            result = response.json()

            ### Convert data formats to match the output of the old ffcsdbclient
            for item in result:
                item['_id'] = ObjectId(item['_id'])
                item['createdOn'] = datetime.strptime(item['createdOn'], '%Y-%m-%dT%H:%M:%S.%f')

            return result
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG get_unselected_plates

    ### FETCH_TAG mark_plate_done
    def mark_plate_done(self, user_account, campaign_id, plate_id, last_imaged, batch_id):
        ### If last_imaged is a datetime object, convert it to string
        if isinstance(last_imaged, datetime):
            last_imaged = last_imaged.isoformat()

        data = {
            "user_account": user_account,
            "campaign_id": campaign_id,
            "plate_id": plate_id,
            "last_imaged": last_imaged,
            "batch_id": batch_id
        }

        response = requests.put(f"{self.base_url}/mark_plate_done", json=data)

        try:
            ### Get the response data
            result = response.json()
            return result['Result']
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG mark_plate_done

    ### FETCH_TAG get_all_wells
    def get_all_wells(self, user_account: str, campaign_id: str) -> List[dict]:
        params = {
            "user_account": user_account,
            "campaign_id": campaign_id
        }
        response = requests.get(f"{self.base_url}/get_all_wells/", params=params)

        try:
            wells = response.json()

            ### Convert "_id" and "libraryID" to ObjectId
            for well in wells:
                if "_id" in well:
                    well["_id"] = ObjectId(well["_id"])
                if "libraryID" in well:
                    well["libraryID"] = ObjectId(well["libraryID"])

            datetime_fields = ['soakExportTime', 'soakTransferTime', 'cryoExportTime', 'shifterTimeOfArrival', 'shifterTimeOfDeparture', 'shifterDuration']
            for item in wells:
                for field in datetime_fields:
                    if field in item and item[field] is not None:
                        dt_str = item[field]
                        if '.' in dt_str:
                            datetime_format = "%Y-%m-%dT%H:%M:%S.%f"
                            item[field] = datetime.strptime(dt_str, datetime_format)
                        else:
                            datetime_format = "%Y-%m-%dT%H:%M:%S"
                            item[field] = datetime.strptime(dt_str, datetime_format)

            return wells
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return []
    ### FETCH_TAG get_all_wells

    ### FETCH_TAG get_wells_from_plate
    def get_wells_from_plate(self, user_account: str, campaign_id: str, plate_id: str, **kwargs) -> list:

        kwargs = convert_objects_to_serializable(kwargs)

        base_request = {"user_account": user_account, "campaign_id": campaign_id, "plate_id": plate_id}
        request = {**base_request, **kwargs}
        response = requests.get(f"{self.base_url}/get_wells_from_plate/",
                                params=request)

        try:
            wells = response.json()
            ### Convert all ObjectId strings to ObjectId
            wells = convert_strings_to_objectids(wells)
            #wells = [convert_objects_to_serializable(item) for item in wells]
            return wells
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return []
    ### FETCH_TAG get_wells_from_plate

    ### FETCH_TAG get_one_well
    def get_one_well(self, well_id: str) -> dict:
        response = requests.get(f"{self.base_url}/get_one_well/", params={"well_id": well_id})

        try:
            well = response.json()

            ### Convert "_id" and "libraryID" to ObjectId
            if "_id" in well:
                well["_id"] = ObjectId(well["_id"])
            if "libraryID" in well:
                well["libraryID"] = ObjectId(well["libraryID"])

            return well
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return {}
    ### FETCH_TAG get_one_well

    ### FETCH_TAG get_one_campaign_library
    def get_one_campaign_library(self, library_id: str) -> dict:
        response = requests.get(f"{self.base_url}/get_one_campaign_library/", params={"library_id": library_id})

        try:
            library = response.json()
            ### Convert all ObjectId strings to ObjectId
            library = convert_strings_to_objectids(library)
            #if "_id" in library:
            #    library["_id"] = ObjectId(library["_id"])
            return library
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return {}
    ### FETCH_TAG get_one_campaign_library

    ### FETCH_TAG get_one_library
    def get_one_library(self, library_id: str) -> dict:
        """
        Sends a GET request to the FastAPI server to retrieve a single library record by its ID.

        This method constructs a request with the library ID and sends it to the server's '/get_one_library/' endpoint.
        The response is processed to obtain the library data. If the response cannot be parsed or an error occurs 
        during the request, it returns an empty dictionary. The library ID is assumed to be a valid ObjectId in string format.

        Args:
            library_id (str): The string representation of the library's ObjectId.
        
        Returns:
            dict: A dictionary representing the library data if found, otherwise an empty dictionary.
        
        Raises:
            Exception: Captures any exception that occurs during the request or JSON parsing and logs the error message.
        """
        response = requests.get(f"{self.base_url}/get_one_library/", params={"library_id": library_id})

        try:
            library = response.json()
            return library
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return {}
    ### FETCH_TAG get_one_library

    ### FETCH_TAG get_smiles
    def get_smiles(self, user_account: str, campaign_id: str, xtal_name: str) -> Optional[str]:
        """
        Sends a GET request to the FastAPI server to retrieve the SMILES string for a specific crystal.
    
        This method constructs the parameters with the user account, campaign ID, and crystal name and sends a GET request
        to the server's '/get_smiles/' endpoint. It processes the JSON response to extract the SMILES string. If the response 
        cannot be parsed or an error occurs during the request, it handles the exception and returns None.
    
        Args:
            user_account (str): The identifier of the user account.
            campaign_id (str): The identifier of the campaign.
            xtal_name (str): The name of the crystal.
    
        Returns:
            Optional[str]: The SMILES string if found, otherwise None.
    
        Raises:
            Exception: Captures any exception that occurs during the request or JSON parsing and logs the error message.
        """
        response = requests.get(f"{self.base_url}/get_smiles/", params={"user_account": user_account, "campaign_id": campaign_id, "xtal_name": xtal_name})
        
        try:
            data = response.json()
            return data.get("smiles")
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG get_smiles

    ### FETCH_TAG get_not_matched_wells
    def get_not_matched_wells(self, user_account: str, campaign_id: str) -> list:
        """
        Sends a GET request to retrieve wells from the database that are not matched based on specific criteria.
        These wells are filtered by user account and campaign ID and further based on the 'compoundCode' and 
        'cryoProtection' status.
    
        Args:
            user_account (str): The user account identifier.
            campaign_id (str): The campaign identifier.
    
        Returns:
            list: A list of dictionaries, each representing a well that matches the query criteria, retrieved from the server.
    
        Raises:
            Exception: If the JSON response cannot be parsed or if there's a network-related issue, it prints the error and returns an empty list.
        """
        try:
            # Prepare the request with query parameters
            params = {"user_account": user_account, "campaign_id": campaign_id}
            response = requests.get(f"{self.base_url}/get_not_matched_wells/", params=params)
    
            # Attempt to parse the JSON response
            wells = response.json()
            return wells
        except Exception as e:
            # Handle exceptions related to response parsing or network issues
            print(f"Could not parse JSON or network issue occurred: {e}")
            return []
    ### FETCH_TAG get_not_matched_wells

    ### FETCH_TAG get_id_of_plates_to_soak
    def get_id_of_plates_to_soak(self, user_account: str, campaign_id: str) -> list:
        """
        Sends a GET request to the server to retrieve the IDs of plates for soaking operation, 
        along with the count of wells with and without an assigned library for each plate, 
        filtered by user account and campaign ID.
    
        This function communicates with a FastAPI server endpoint that queries a MongoDB 
        collection to find plates matching the given user account and campaign ID. It then
        aggregates data to count total wells, wells with a library assigned, and wells 
        without a library assigned for each plate.
    
        Args:
            user_account (str): The user account identifier.
            campaign_id (str): The campaign identifier.
    
        Returns:
            list: A list of dictionaries, each containing the plate ID, total well count, 
                  count of wells with a library, and count of wells without a library.
    
        Raises:
            JSONDecodeError: If the response body does not contain valid JSON.
            RequestException: For issues like network problems, or connection timeouts.
        """
        try:
            response = requests.get(f"{self.base_url}/get_id_of_plates_to_soak/",
                                    params={"user_account": user_account, "campaign_id": campaign_id})
            response.raise_for_status()  # Raises an HTTPError, if the HTTP request returned an unsuccessful status code
            return response.json()
        except json.JSONDecodeError as e:
            print(f"Could not parse JSON: {e}")
            return []
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return []
    ### FETCH_TAG get_id_of_plates_to_soak

    ### FETCH_TAG get_id_of_plates_to_cryo_soak
    def get_id_of_plates_to_cryo_soak(self, user_account: str, campaign_id: str) -> list:
        """
        Sends a GET request to the server to retrieve the IDs of plates for cryo soaking 
        operation, along with the count of wells with and without cryo protection for 
        each plate, filtered by user account and campaign ID.
    
        This function communicates with a FastAPI server endpoint that queries a MongoDB
        collection to find plates matching the given user account and campaign ID. It then
        aggregates data to count total wells, wells with cryo protection, and wells without
        cryo protection for each plate.
    
        Args:
            user_account (str): The user account identifier.
            campaign_id (str): The campaign identifier.
    
        Returns:
            list: A list of dictionaries, each containing the plate ID, total well count,
                  count of wells with cryo protection, and count of wells without cryo protection.
    
        Raises:
            JSONDecodeError: If the response body does not contain valid JSON.
        """
        response = requests.get(f"{self.base_url}/get_id_of_plates_to_cryo_soak/",
                                params={"user_account": user_account, "campaign_id": campaign_id})
    
        try:
            plates = response.json()
            return plates
        except json.JSONDecodeError as e:
            print(f"Could not parse JSON: {e}")
            return []
    ### FETCH_TAG get_id_of_plates_to_cryo_soak

    ### FETCH_TAG get_id_of_plates_for_redesolve
    def get_id_of_plates_for_redesolve(self, user_account: str, campaign_id: str) -> list:
        """
        Sends a GET request to the server to retrieve the IDs of plates for redesolve operation,
        along with the count of wells with and without new solvent for each plate, filtered by
        user account and campaign ID.
    
        This function communicates with a FastAPI server endpoint that queries a MongoDB 
        collection to find plates matching the given user account and campaign ID. It then
        aggregates data to count total wells, wells with new solvent, and wells without new 
        solvent for each plate.
    
        Args:
            user_account (str): The user account identifier.
            campaign_id (str): The campaign identifier.
    
        Returns:
            list: A list of dictionaries, each containing the plate ID, total well count, 
            count of wells with new solvent, and count of wells without new solvent.
    
        Raises:
            JSONDecodeError: If the response body does not contain valid JSON.
        """
        response = requests.get(f"{self.base_url}/get_id_of_plates_for_redesolve/",
                                params={"user_account": user_account, "campaign_id": campaign_id})
    
        try:
            plates = response.json()
            return plates
        except json.JSONDecodeError as e:
            print(f"Could not parse JSON: {e}")
            return []
    ### FETCH_TAG get_id_of_plates_for_redesolve

    ### FETCH_TAG export_to_soak_selected_wells
    def export_to_soak_selected_wells(self, user: str, campaign_id: str, data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Sends a POST request to export soak data for selected wells.

        Args:
            user (str): The user account associated with the wells to be updated.
            campaign_id (str): The campaign identifier associated with the wells to be updated.
            data (List[Dict[str, Any]]): A list of dictionaries, each containing the 'plateId' of a well to update.

        Returns:
            Optional[Dict[str, Any]]: The result of the update operation as a dictionary if the response can be parsed as JSON; otherwise, None.

        Raises:
            Exception: If the server request fails or the response cannot be parsed as JSON.
        """
        data = [convert_objects_to_serializable(item) for item in data]
        url = f"{self.base_url}/export_to_soak_selected_wells/"
        payload = {"user": user, "campaign_id": campaign_id, "data": data}

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()  # Raises HTTPError for bad requests (4xx or 5xx)
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")  # Python 3.6
            return None
        except requests.exceptions.RequestException as err:
            print(f"An error occurred: {err}")
            return None
        except ValueError as json_err:
            print(f"JSON decode error: {json_err}")
            return None
    ### FETCH_TAG export_to_soak_selected_wells

    ### FETCH_TAG export_cryo_to_soak_selected_wells
    def export_cryo_to_soak_selected_wells(self, user: str, campaign_id: str, data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Sends a POST request to export cryopreservation data for selected wells.

        This method communicates with the FastAPI server to trigger an update operation on
        the database, setting 'cryoExportTime' to the current time and 'cryoStatus' to 'exported'.

        Args:
            user (str): The username associated with the wells to update.
            campaign_id (str): The campaign ID associated with the wells to update.
            data (List[Dict[str, Any]]): A list of well information, with each well represented as a dictionary.

        Returns:
            Optional[Dict[str, Any]]: A dictionary with the update operation's result if successful, 
                                      or an empty dictionary if JSON parsing fails.

        Raises:
            requests.exceptions.RequestException: If the request to the server fails.
            ValueError: If the response from the server cannot be parsed as JSON.
        """

        data = [convert_objects_to_serializable(item) for item in data]

        url = f"{self.base_url}/export_cryo_to_soak_selected_wells/"
        payload = {"user": user, "campaign_id": campaign_id, "data": data}
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"Error during requests to {url}: {req_err}")
        except ValueError as json_err:
            print(f"JSON parsing error: {json_err}")

        return {}

    # Assume other necessary methods follow below
    ### FETCH_TAG export_cryo_to_soak_selected_wells

    ### FETCH_TAG export_redesolve_to_soak_selected_wells
    def export_redesolve_to_soak_selected_wells(self, user: str, campaign_id: str, data: List[dict]) -> dict:
        """
        Sends a POST request to the server to export 'redesolve' data to soak selected wells.
    
        Args:
            user (str): The user account associated with the wells to be updated.
            campaign_id (str): The campaign identifier associated with the wells to be updated.
            data (List[dict]): A list of dictionaries where each dictionary contains
                                details of a well to update, identified by 'plateId'.
    
        Returns:
            dict: A dictionary containing the server response. Typically includes a "result" key.
    
        Raises:
            requests.exceptions.RequestException: If the request to the server fails.
            ValueError: If the server response cannot be parsed as JSON.
        """

        data = [convert_objects_to_serializable(item) for item in data]

        url = f"{self.base_url}/export_redesolve_to_soak_selected_wells/"
        headers = {'Content-Type': 'application/json'}
        payload = {"user": user, "campaign_id": campaign_id, "data": data}
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()  # Raises a RequestException for HTTP errors
            try:
                return response.json()
            except ValueError as e:  # Includes JSONDecodeError
                raise ValueError(f"Could not parse JSON: {e}")
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(f"Server request failed: {e}")
    ### FETCH_TAG export_redesolve_to_soak_selected_wells

    ### FETCH_TAG export_to_soak
    def export_to_soak(self, data: List[Dict[str, Any]]) -> Optional[Any]:
        """
        Sends a POST request to export soak data for wells and plates.
    
        This method sends soak times for plates to the server and expects a JSON response
        with the details of the update operation, including counts of matched and modified
        documents, and any upserted or raw results.
    
        Args:
            data: A list of dictionaries containing plate IDs and their corresponding soak times.
                  Each dictionary must have 'plateId' and 'soakExportTime' keys.
    
        Returns:
            Optional[Any]: The result of the update operation as a dictionary if the
                           response can be parsed as JSON, otherwise None.
    
        Raises:
            requests.exceptions.RequestException: If the POST request fails.
            ValueError: If the response cannot be parsed as JSON.
        """

        data = [convert_objects_to_serializable(item) for item in data]

        try:
            response = requests.post(f"{self.base_url}/export_to_soak/", json=data)
            response.raise_for_status()  # Check for HTTP request errors
            result = response.json()
            # Assuming MockUpdateResult simulates the structure of the actual result
            update_result = MockUpdateResult(
                matched_count=result["matched_count"],
                modified_count=result["modified_count"],
                upserted_id=result["upserted_id"],
                raw_result=result["raw_result"],
            )
            return update_result
        except requests.exceptions.RequestException as e:
            raise requests.exceptions.RequestException(f"Server request failed: {e}")
        except ValueError as e:
            raise ValueError(f"Could not parse JSON: {e}")
    ### FETCH_TAG export_to_soak

    ### FETCH_TAG export_redesolve_to_soak
    def export_redesolve_to_soak(self, data: List[Dict[str, Any]]) -> MockUpdateResult:
        """
        Sends a POST request to the server to export 'redesolve' data for wells and plates.

        The method posts data to the '/export_redesolve_to_soak/' endpoint. The server should
        process this data to update the 'redesolveExportTime' for wells and 'redesolveApplied' for
        plates to mark them as exported. It handles the JSON response which includes the
        update results.

        Args:
            data: A list of dictionaries, each containing the 'plateId' and the 'soak_time'
                  when the 'redesolve' data was exported.

        Returns:
            MockUpdateResult: An object that mimics the structure of a pymongo UpdateResult
                              with 'matched_count', 'modified_count', 'upserted_id', and 'raw_result'
                              keys if the JSON response is valid.

        Raises:
            requests.HTTPError: If an HTTP error occurs during the POST request.
            ValueError: If the server response cannot be parsed as JSON.
        """

        data = [convert_objects_to_serializable(item) for item in data]

        try:
            response = requests.post(f"{self.base_url}/export_redesolve_to_soak/", json=data)
            response.raise_for_status()  # Raises HTTPError if one occurred during the request
            result = response.json()
            # MockUpdateResult mimics the pymongo UpdateResult object
            update_result = MockUpdateResult(
                matched_count=result.get("matched_count"),
                modified_count=result.get("modified_count"),
                upserted_id=result.get("upserted_id"),
                raw_result=result.get("raw_result")
            )
            return update_result
        except requests.HTTPError as http_err:
            # Specific handling for HTTP errors with detailed message
            raise requests.HTTPError(f"HTTP error occurred: {http_err}") from http_err
        except ValueError as json_err:
            # Specific handling for JSON decoding errors with detailed message
            raise ValueError(f"Could not parse JSON: {json_err}") from json_err
    ### FETCH_TAG export_redesolve_to_soak

    ### FETCH_TAG export_cryo_to_soak
    def export_cryo_to_soak(self, data: List[Dict[str, Any]]) -> Optional[Any]:
        """
        Sends a POST request to export cryopreservation data for soaking wells and plates.

        This method sends soak times for plates to the server and expects a JSON response
        with the details of the update operation, including counts of matched and modified
        documents, and any upserted or raw results.

        Args:
            data: A list of dictionaries containing plate IDs and their corresponding soak times.

        Returns:
            Optional[Any]: The result of the update operation as a MockUpdateResult object if the
                           response can be parsed as JSON, otherwise None.

        Raises:
            Exception: If the POST request fails or the response cannot be parsed as JSON.
        """

        data = [convert_objects_to_serializable(item) for item in data]

        try:
            response = requests.post(f"{self.base_url}/export_cryo_to_soak/", json=data)
            response.raise_for_status()  # Check for HTTP request errors
            result = response.json()
            # MockUpdateResult is used for demonstration; replace with actual parsing logic
            update_result = MockUpdateResult(
                matched_count=result.get("matched_count"),
                modified_count=result.get("modified_count"),
                upserted_id=result.get("upserted_id"),
                raw_result=result.get("raw_result"),
            )
            return update_result
        except Exception as e:
            print(f"Could not parse JSON or server request failed: {e}")
            return None
    ### FETCH_TAG export_cryo_to_soak

    ### FETCH_TAG import_soaking_results
    def import_soaking_results(self, wells_data: List[Dict[str, Any]]) -> Any:
        """
        Sends a request to import soaking results for the provided well data.

        This function posts the well data to the 'import_soaking_results' endpoint
        and returns the response. It handles JSON parsing and exceptions that may occur
        during the request.

        Args:
            wells_data: A list of dictionaries, each containing data for a well,
                        including 'plateId', 'wellEcho', and 'transferStatus'.

        Returns:
            A dictionary with the result of the import operation or None in case of
            an exception.

        Raises:
            requests.exceptions.RequestException: If the request to the server fails.
            ValueError: If the response contains invalid JSON.
        """

        wells_data = [convert_objects_to_serializable(item) for item in wells_data]


        try:
            response = requests.post(f"{self.base_url}/import_soaking_results/", json=wells_data)
            response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            return None
        except requests.exceptions.RequestException as err:
            print(f"An error occurred during the request: {err}")
            return None
        except ValueError as json_err:
            print(f"Could not parse JSON: {json_err}")
            return None
    ### FETCH_TAG import_soaking_results



    ### FETCH_TAG mark_soak_for_well_in_echo_done
    def mark_soak_for_well_in_echo_done(self, user: str, campaign_id: str, plate_id: str, well_echo: str, transfer_status: str) -> Any:
        """
        Sends a POST request to the server to mark a well's soak status as 'done' after an Echo transfer.
    
        This method prepares and sends the data required for the operation in JSON format. The server response is then
        parsed into a MockUpdateResult object.
    
        Args:
            user: The user account performing the update.
            campaign_id: The campaign identifier associated with the well.
            plate_id: The plate identifier where the well is located.
            well_echo: The specific well identifier in Echo.
            transfer_status: The status of the transfer operation.
    
        Returns:
            A MockUpdateResult object with the server's response data or None if parsing failed.
    
        Raises:
            requests.exceptions.RequestException: If the request to the server fails.
            ValueError: If the server response cannot be parsed as JSON.
            KeyError: If expected keys are not present in the response JSON.
        """
        data = {
            "user": user,
            "campaign_id": campaign_id,
            "plate_id": plate_id,
            "well_echo": well_echo,
            "transfer_status": transfer_status
        }
        response = requests.post(f"{self.base_url}/mark_soak_for_well_in_echo_done/", json=data)
        
        # Check for successful request before attempting to parse the response.
        if response.status_code != 200:
            response.raise_for_status()
    
        try:
            result = response.json()
            update_result = MockUpdateResult(
                matched_count=result["matched_count"],
                modified_count=result["modified_count"],
                upserted_id=result.get("upserted_id"),  # Use get to avoid KeyError if key is absent.
                raw_result=result["raw_result"]
            )
            return update_result
        except ValueError as e:
            raise ValueError(f"Could not parse JSON: {e}") from e
        except KeyError as e:
            raise KeyError(f"Expected key not found in the response JSON: {e}") from e
    ### FETCH_TAG mark_soak_for_well_in_echo_done
    
    ### FETCH_TAG add_cryo
    def add_cryo(self, data: Dict[str, Any]) -> Optional[MockUpdateResult]:
        """
        Sends a POST request to add cryoprotection details to a well.
    
        This method communicates with a server endpoint to add details about the 
        cryoprotectant to a specific well. It expects a dictionary containing 
        cryoprotection information and returns a `MockUpdateResult` object.
    
        Args:
            data: A dictionary with keys corresponding to cryoprotection details such
                  as 'user_account', 'campaign_id', 'target_plate', 'target_well',
                  'cryo_desired_concentration', 'cryo_transfer_volume', 'cryo_source_well',
                  'cryo_name', and 'cryo_barcode'.
    
        Returns:
            An instance of `MockUpdateResult` representing the result of the update operation
            if successful, otherwise `None`.
    
        Raises:
            JSONDecodeError: If the response body does not contain valid JSON.
            requests.exceptions.RequestException: If the request to the server fails.
        """

        data = convert_objects_to_serializable(data)

        try:
            response = requests.post(f"{self.base_url}/add_cryo/", json=data)
            response.raise_for_status()  # Raise an HTTPError if the HTTP request returned an unsuccessful status code
    
            result = response.json()
            return MockUpdateResult(
                matched_count=result["matched_count"],
                modified_count=result["modified_count"],
                upserted_id=result["upserted_id"],
                raw_result=result["raw_result"],
            )
        except json.JSONDecodeError:
            print(f"Could not parse JSON from response. Response content: {response.content}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None
    ### FETCH_TAG add_cryo

    ### FETCH_TAG remove_cryo_from_well
    def remove_cryo_from_well(self, well_id: str) -> Any:
        """
        Sends a PATCH request to the server to remove cryoprotectant data from a specified well by its ID.

        Args:
            well_id (str): The string representation of the well's ObjectId.

        Returns:
            Any: An instance of MockUpdateResult with the response data or None if an error occurs.

        Raises:
            ValueError: If the response from the server cannot be parsed as JSON.
            HTTPError: If the server responds with a non-200 status code.
        """
        response = requests.patch(f"{self.base_url}/remove_cryo_from_well/{well_id}")

        if response.ok:
            try:
                result = response.json()
                update_result = MockUpdateResult(
                    matched_count=result["matched_count"],
                    modified_count=result["modified_count"],
                    upserted_id=result.get("upserted_id"),  # Use .get for optional keys
                    raw_result=result["raw_result"],
                )
                return update_result
            except ValueError as e:  # More specific exception for JSON parsing issues
                raise ValueError(f"Could not parse JSON: {e}") from e
        else:
            # Handle non-200 responses by raising an HTTPError
            response.raise_for_status()  # This will raise an HTTPError if the response is an http error
    ### FETCH_TAG remove_cryo_from_well


    ### FETCH_TAG remove_new_solvent_from_well
    def remove_new_solvent_from_well(self, well_id: str) -> Any:
        """
        Sends a PATCH request to the server to remove the New Solvent from a specified well.
    
        This method attempts to parse the JSON response and wraps the relevant data into 
        a `MockUpdateResult` instance, providing a structured access to the result of the 
        removal operation.
    
        Args:
            well_id (str): The string representation of the well's unique identifier.
    
        Returns:
            MockUpdateResult: An object containing counts of matched and modified documents, 
                              along with raw server response data.
    
        Raises:
            JSONDecodeError: If the response is not a valid JSON.
            RequestException: If the HTTP request fails.
        """
        try:
            response = requests.patch(f"{self.base_url}/remove_new_solvent_from_well/{well_id}")
            response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code
            result = response.json()
    
            return MockUpdateResult(
                matched_count=result["matched_count"],
                modified_count=result["modified_count"],
                upserted_id=result.get("upserted_id"),  # .get() is used to avoid KeyError if the key doesn't exist
                raw_result=result["raw_result"],
            )
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as req_err:
            print(f"Other error occurred: {req_err}")
        except ValueError as json_err:  # JSONDecodeError inherits ValueError
            print(f"JSON decode error: {json_err}")
        return None
    ### FETCH_TAG remove_new_solvent_from_well

    ### FETCH_TAG get_cryo_usage
    def get_cryo_usage(self, user: str, campaign_id: str) -> Any:
        """
        Fetch cryo usage details for a given user and campaign ID.
        
        Args:
            user (str): The user account ID.
            campaign_id (str): The campaign ID.
        
        Returns:
            Any: The cryo usage details if successfully fetched, otherwise None.
        
        Exceptions:
            Prints an error message if JSON parsing fails.
        """
        # Construct the URL for the GET request
        request_url = f"{self.base_url}/get_cryo_usage/{user}/{campaign_id}"
        
        # Send the GET request and capture the response
        response = requests.get(request_url)
        
        try:
            # Attempt to parse the JSON response
            result = response.json()
            return result
        except Exception as e:
            ### Failed to parse JSON
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG get_cryo_usage

    ### FETCH_TAG get_solvent_usage
    def get_solvent_usage(self, user: str, campaign_id: str) -> Any:
        """
        Fetch the solvent usage data for a given user and campaign.
    
        Sends a GET request to the FastAPI server to obtain the aggregated
        solvent usage for wells that have cryoProtection set to True
        and cryoStatus set to pending, for a specific user and campaign.
    
        Parameters:
        user (str): The user account ID.
        campaign_id (str): The ID of the campaign.
    
        Returns:
        Any: A JSON-serializable object representing the solvent usage,
        or None if JSON parsing fails.
    
        Exceptions:
        Prints an exception message if JSON parsing fails.
        """
        ### Construct the URL for the GET request.
        request_url = f"{self.base_url}/get_solvent_usage/{user}/{campaign_id}"
    
        ### Execute the GET request.
        response = requests.get(request_url)
    
        try:
            ### Parse the JSON response.
            result = response.json()
            return result
        except Exception as json_parse_error:
            ### Handle JSON parsing errors.
            print(f"Could not parse JSON: {json_parse_error}")
            return None
    ### FETCH_TAG get_solvent_usage

    ### FETCH_TAG redesolve_in_new_solvent
    def redesolve_in_new_solvent(self, user_account, campaign_id, target_plate, target_well, redesolve_transfer_volume,
                                 redesolve_source_well, redesolve_name, redesolve_barcode):
        """
        Send a PATCH request to the server to perform redesolve_in_new_solvent operation.
    
        Parameters:
        - user_account: The user account identifier
        - campaign_id: The campaign identifier
        - target_plate: The target plate ID
        - target_well: The target well ID
        - redesolve_transfer_volume: The volume to be transferred during redesolve
        - redesolve_source_well: The source well for redesolve
        - redesolve_name: The name for redesolve operation
        - redesolve_barcode: The barcode for redesolve operation
    
        Returns:
        - update_result: A MockUpdateResult object containing various result attributes
        """
    
        # Prepare request data
        request_data = {
            "user_account": user_account,
            "campaign_id": campaign_id,
            "target_plate": target_plate,
            "target_well": target_well,
            "redesolve_transfer_volume": redesolve_transfer_volume,
            "redesolve_source_well": redesolve_source_well,
            "redesolve_name": redesolve_name,
            "redesolve_barcode": redesolve_barcode
        }
    
        # Send PATCH request
        try:
            response = requests.patch(f"{self.base_url}/redesolve_in_new_solvent/", json=request_data)
            response.raise_for_status()  # Check if the request was successful
        except requests.RequestException as req_error:
            print(f"Failed to send request: {req_error}")
            return None
    
        # Parse and return the result
        try:
            parsed_result = response.json()
            update_result = MockUpdateResult(
                matched_count=parsed_result["matched_count"],
                modified_count=parsed_result["modified_count"],
                upserted_id=parsed_result["upserted_id"],
                raw_result=parsed_result["raw_result"]
            )
            return update_result
        except ValueError as json_error:
            print(f"Could not parse JSON: {json_error}")
            return None
    ### FETCH_TAG redesolve_in_new_solvent

    ### FETCH_TAG update_notes
    def update_notes(self, user: str, campaign_id: str, doc_id: str, note: str) -> Any:
        """
        Sends a PATCH request to update the notes field for a specific well in the database.
        
        Parameters:
            user (str): User account identifier.
            campaign_id (str): Campaign identifier.
            doc_id (str): Document identifier for the well.
            note (str): New note to be added.
            
        Returns:
            Any: JSON response data from the server. None if JSON parsing fails.
            
        Side Effects:
            Updates the notes field in the database for the specified well.
            
        Exceptions:
            Prints an error message if JSON parsing fails.
        """
    
        # Create the payload for the PATCH request
        payload = {
            "user": user,
            "campaign_id": campaign_id,
            "doc_id": doc_id,
            "note": note
        }
    
        # Perform the PATCH request
        response = requests.patch(f"{self.base_url}/update_notes/", json=payload)
    
        # Try to parse the JSON response
        try:
            parsed_response = response.json()
            return parsed_response
        except Exception as json_parse_error:
            ### Could not parse the JSON response
            print(f"Could not parse JSON: {json_parse_error}")
            return None
    ### FETCH_TAG update_notes

    ### FETCH_TAG is_crystal_already_fished
    def is_crystal_already_fished(self, plate_id: str, well_id: str) -> bool:
        """
        Sends a request to the server to check if the crystal from a given plate and well is already fished.
    
        Parameters:
            plate_id (str): ID of the plate.
            well_id (str): ID of the well.
    
        Returns:
            bool: True if the crystal is already fished, False otherwise.
                Returns None if an error occurs while parsing JSON.
    
        Raises:
            None: Any exceptions are caught and printed.
        """
        ### Send a GET request to the corresponding API endpoint
        response = requests.get(f"{self.base_url}/is_crystal_already_fished/{plate_id}/{well_id}")
    
        try:
            ### Parse the JSON result from the server response
            result = response.json()
    
            ### Extract and return the 'result' field
            return result["result"]
        except Exception as json_parse_error:
            ### Print error message if JSON parsing fails
            print(f"Could not parse JSON: {json_parse_error}")
            
            ### Return None if an error occurs
            return None
    ### FETCH_TAG is_crystal_already_fished

    ### FETCH_TAG update_shifter_fishing_result
    def update_shifter_fishing_result(self, well_shifter_data: dict, xtal_name_index: int, xtal_name_prefix: str) -> Any:
        response = requests.patch(f"{self.base_url}/update_shifter_fishing_result", json={
            'well_shifter_data': well_shifter_data,
            'xtal_name_index': xtal_name_index,
            'xtal_name_prefix': xtal_name_prefix
        })
        try:
            result = response.json()

            update_result = MockUpdateResult(
                matched_count=result["matched_count"],
                modified_count=result["modified_count"],
                upserted_id=result["upserted_id"],
                raw_result=result["raw_result"],
                )
            return update_result

        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG update_shifter_fishing_result

    ### FETCH_TAG import_fishing_results
    def import_fishing_results(self, fishing_results: List[dict]) -> Any:
        """
        Import fishing results by sending them to the ffcs_db server via a POST request.
        
        This method sends a list of dictionaries containing fishing results to the server's 
        `/import_fishing_results` endpoint. It then processes the server's JSON response 
        and returns an instance of MockUpdateResult.
        
        Parameters:
            fishing_results (List[dict]): A list of dictionaries containing fishing results.
            
        Returns:
            MockUpdateResult: An object containing the results of the update operation.
            None: If there's an error in parsing the JSON response.
            
        Raises:
            Prints an error message if JSON parsing fails.
        """

        fishing_results = [convert_objects_to_serializable(item) for item in fishing_results]


        try:
            ### Make a POST request to the ffcs_db server with fishing results as JSON payload
            response = requests.post(f"{self.base_url}/import_fishing_results", json=fishing_results)
    
            ### Attempt to parse the JSON response from the server
            result = response.json()
    
            ### Create and populate a MockUpdateResult instance based on the parsed JSON
            update_result = MockUpdateResult(
                matched_count=result["matched_count"],
                modified_count=result["modified_count"],
                upserted_id=result["upserted_id"],
                raw_result=result["raw_result"]
            )
    
            return update_result
        except Exception as e:
            ### Print an error message and return None if JSON parsing fails
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG import_fishing_results

    ### FETCH_TAG find_user_from_plate_id
    def find_user_from_plate_id(self, plate_id: str) -> Any:
        """
        Retrieves user information based on the provided plate ID by sending a GET request to the server.
        
        Parameters:
        - plate_id (str): The plate ID used to search for the user.
        
        Returns:
        - Any: A dictionary containing user information if successful, or None if an exception occurs or the plate ID is not found.
        
        Side Effects:
        - May print an error message if JSON parsing fails.
        
        Exceptions:
        - Raises any exceptions originating from the requests library or from JSON parsing.
        """
        response = requests.get(f"{self.base_url}/find_user_from_plate_id/{plate_id}")
    
        try:
            result = response.json()  ### Parse the JSON response
            return result  ### Return the parsed result
        except Exception as e:
            ### Handle exceptions during JSON parsing
            print(f"Could not parse JSON: {e}")
            return None  ### Return None if JSON parsing fails
    ### FETCH_TAG find_user_from_plate_id

    ### FETCH_TAG find_last_fished_xtal
    def find_last_fished_xtal(self, user: str, campaign_id: str) -> Any:
        """
        Retrieves the last fished crystal based on the user and campaign ID.
    
        Args:
            user (str): The user account.
            campaign_id (str): The ID of the campaign.
    
        Returns:
            Any: A list of the results if found, otherwise None.
    
        Raises:
            Prints an error message if JSON could not be parsed.
        """
        ### Construct the URL
        url = f"{self.base_url}/find_last_fished_xtal/{user}/{campaign_id}"
        
        ### Perform the HTTP GET request
        try:
            response = requests.get(url)
            response.raise_for_status()  ### Raise HTTPError for bad responses
        except requests.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            return None
        except Exception as err:
            print(f"An error occurred: {err}")
            return None
    
        ### Parse the JSON response
        try:
            result = response.json()
        except Exception as json_err:
            print(f"Could not parse JSON: {json_err}")
            return None
    
        ### Process the result
        if "result" in result:
            for well in result["result"]:
                well["_id"] = ObjectId(well["_id"])  ### Convert string back to ObjectId
            return result["result"]  ### Return the list of results
        else:
            return None
    ### FETCH_TAG find_last_fished_xtal

    ### FETCH_TAG get_next_xtal_number
    def get_next_xtal_number(self, plate_id: str) -> int:
        """
        Fetches the next available crystal number given a plate identifier.
        
        :param plate_id: The identifier for the plate
        :return: An integer representing the next available crystal number or None if unsuccessful
        """
        try:
            response = requests.get(f"{self.base_url}/get_next_xtal_number/{plate_id}")
            response.raise_for_status()  ### Raise exception for HTTP errors
    
            result = response.json()
            return result["next_xtal_number"]  ### Directly return the integer
        except requests.RequestException as http_error:
            print(f"HTTP error occurred: {http_error}")
        except KeyError:
            print("Unexpected format: 'next_xtal_number' key missing in the JSON response.")
        except json.JSONDecodeError as json_error:
            print(f"Could not parse JSON: {json_error}")
    
        return None  ### Return None if any exception occurs
    ### FETCH_TAG get_next_xtal_number

    ### FETCH_TAG get_soaked_wells
    def get_soaked_wells(self, user: str, campaign_id: str) -> Any:
        """
        Retrieve soaked wells from the server for a given user and campaign ID.
    
        :param user: The user account as a string.
        :param campaign_id: The campaign identifier as a string.
        :return: A list of dictionaries representing the soaked wells or None if an error occurs.
        """
        try:
            # Make the HTTP request
            response = requests.get(f"{self.base_url}/get_soaked_wells/{user}/{campaign_id}")
    
            # Validate HTTP response
            if response.status_code != 200:
                print(f"Received HTTP {response.status_code} response: {response.reason}")
                return None
    
            # Validate Content-Type
            if 'application/json' not in response.headers['Content-Type']:
                print("Received response is not in JSON format")
                print("Response content:", response.content.decode())
                return None
    
            # Parse JSON response
            result = response.json().get('result', [])
    
            # Convert ObjectIds from string to ObjectId type
            if result:
                for well in result:
                    well["_id"] = ObjectId(well["_id"])
    
            return result
    
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    ### FETCH_TAG get_soaked_wells

    ### FETCH_TAG get_number_of_unsoaked_wells
    def get_number_of_unsoaked_wells(self, user: str, campaign_id: str) -> int:
        """
        Retrieve the number of unsoaked wells for a given user and campaign ID by querying the FastAPI server.
        :param user: The username to query.
        :param campaign_id: The campaign ID to query.
        :return: Integer representing the number of unsoaked wells or None if an error occurs.
        """
    
        ### Initialize the URL for the GET request
        url = f"{self.base_url}/get_number_of_unsoaked_wells/{user}/{campaign_id}"
        
        try:
            ### Send the GET request to the server
            response = requests.get(url)
            
            ### Parse the JSON response
            result = response.json()
            return result["number_of_unsoaked_wells"]
            
        except requests.RequestException as e:
            ### Handle request errors
            print(f"Request error: {e}")
            
        except ValueError as e:
            ### Handle JSON parsing errors
            print(f"Could not parse JSON: {e}")
        
        return None
    ### FETCH_TAG get_number_of_unsoaked_wells

    ### FETCH_TAG update_soaking_duration
    def update_soaking_duration(self, user: str, campaign_id: str, wells: list):
        """
        Send a PUT request to update the soakDuration of wells.
    
        Parameters:
            user (str): The user requesting the update.
            campaign_id (str): The campaign ID associated with the wells.
            wells (list): List of dictionaries containing well data.
    
        Returns:
            MockUpdateOneResultOld: An object containing MongoDB update result information.
        """

        wells = [convert_objects_to_serializable(item) for item in wells]

    
        payload = {"user": user, "campaign_id": campaign_id, "wells": wells}
    
        try:
            # Sending the PUT request
            response = requests.put(f"{self.base_url}/update_soaking_duration", json=payload)
            response.raise_for_status()  # Raise exception for HTTP errors
            result_json = response.json()  # Parse the JSON response
        except requests.RequestException as req_err:
            print(f"Request failed: {req_err}")
            return None
        except json.JSONDecodeError as json_err:
            print(f"Could not parse JSON: {json_err}")
            return None
    
        # Create and return the result object
        return MockUpdateOneResultOld(
            nModified=result_json["nModified"],
            ok=result_json["ok"],
            n=result_json["n"],
        )
    ### FETCH_TAG update_soaking_duration

    ### FETCH_TAG get_all_fished_wells
    def get_all_fished_wells(self, user: str, campaign_id: str) -> list:
        """
        Client function to get all fished wells from the server.
        
        Parameters:
        - user: The user account as a string.
        - campaign_id: The campaign identifier as a string.
        
        Returns:
        - A list of fished wells if successful, otherwise an empty list.
        
        Raises:
        - Prints an exception message if JSON parsing fails.
        """
        ### Formulate the API endpoint URL
        api_url = f"{self.base_url}/get_all_fished_wells/{user}/{campaign_id}"
        
        ### Execute the GET request to fetch data from the server
        response = requests.get(api_url)
        
        try:
            ### Parse the JSON response from the server
            result = response.json()
            
            ### Return the list of fished wells
            return result["fished_wells"]
            
        except Exception as e:
            ### Handle exceptions related to JSON parsing
            print(f"Could not parse JSON: {e}")
            
            ### Return an empty list in case of error
            return []
    ### FETCH_TAG get_all_fished_wells

    ### FETCH_TAG get_all_wells_not_exported_to_datacollection_xls
    def get_all_wells_not_exported_to_datacollection_xls(self, user: str, campaign_id: str) -> list:
        """
        Client function to get all wells not exported to datacollection xls.
        Args:
            user (str): The user account.
            campaign_id (str): The campaign ID.
        Returns:
            list: A list of well data that meet the conditions, or an empty list if an error occurs.
        """
        url = f"{self.base_url}/get_all_wells_not_exported_to_datacollection_xls/{user}/{campaign_id}"
        response = requests.get(url)
        try:
            result = response.json()
            if "wells_not_exported_to_xls" in result:
                for well in result["wells_not_exported_to_xls"]:
                    well["_id"] = ObjectId(well["_id"])  # Convert string back to ObjectId
                return result["wells_not_exported_to_xls"]
            else:
                return []
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return []
    ### FETCH_TAG get_all_wells_not_exported_to_datacollection_xls

    ### FETCH_TAG mark_exported_to_xls
    def mark_exported_to_xls(self, wells: list):
        """
        Marks a list of wells as exported to XLS in the database.
    
        :param wells: A list of dictionaries, each representing well data.
        :return: An instance of MockUpdateOneResultOld containing the update result.
        """

        wells = [convert_objects_to_serializable(item) for item in wells]

        payload = {"wells": wells}
        url = f"{self.base_url}/mark_exported_to_xls"
        
        try:
            response = requests.put(url, json=payload)
            response.raise_for_status()
            response_json = response.json()
            
            update_result = MockUpdateOneResultOld(
                nModified=response_json["nModified"],
                ok=response_json["ok"],
                n=response_json["n"],
            )
            return update_result
        except Exception as e:
            print(f"Error during request: {e}")
            return None
    ### FETCH_TAG mark_exported_to_xls

    ### FETCH_TAG send_notification
    def send_notification(self, user_account: str, campaign_id: str, notification_type: str) -> dict:
        """
        Sends a notification by making a POST request to the server.
    
        Parameters:
        - user_account (str): The account to which the notification is sent.
        - campaign_id (str): The ID of the campaign related to the notification.
        - notification_type (str): The type of the notification.
    
        Returns:
        dict: A dictionary containing acknowledgement status and inserted_id if successful.
        """
        try:
            response = requests.post(f"{self.base_url}/send_notification/{user_account}/{campaign_id}/{notification_type}")
            response.raise_for_status()
            data = response.json()
            if 'status' in data and data['status'] == "success":
                return {'acknowledged': True, 'inserted_id': data['inserted_id']}
        except requests.RequestException as e:
            print(f"Error sending notification: {str(e)}")
        return {'acknowledged': False, 'inserted_id': None}
    ### FETCH_TAG send_notification

    ### FETCH_TAG get_notifications
    def get_notifications(self, user_account: str, campaign_id: str, timestamp: str) -> CursorMock:
        """
        Fetches the notifications by making a GET request to the server's /get_notifications endpoint.
    
        Args:
            user_account (str): The user account to filter notifications for.
            campaign_id (str): The campaign ID to filter notifications for.
            timestamp (str): The starting timestamp for filtering notifications.
    
        Returns:
            CursorMock: A cursor-like object that mimics the behavior of a MongoDB cursor.
    
        Side-effects:
            - Prints an error message if the operation fails.
        """
        response = requests.get(f"{self.base_url}/get_notifications/{user_account}/{campaign_id}/{timestamp}")
        if response.status_code == 200:
            data = response.json()["notifications"]
    
            ### Convert string representations of ObjectId back to ObjectId format
            for item in data:
                item["_id"] = ObjectId(item["_id"])
    
            return CursorMock(data)
        else:
            ### Handle unsuccessful operation by printing an error message
            print(f"Error getting notifications: {response.text}")
            return None
    ### FETCH_TAG get_notifications

    ### FETCH_TAG add_fragment_to_well
    def add_fragment_to_well(self, library, well_id, fragment, solvent_volume,
                             ligand_transfer_volume, ligand_concentration,
                             is_solvent_test=False):
        """
        Sends a POST request to the server to add a fragment to a specified well. The method constructs
        and sends a payload containing all necessary details about the fragment and the well.
    
        Args:
            library (dict): Information about the library including its ID, name, and barcode.
            well_id (ObjectId): The MongoDB ObjectId of the well to which the fragment is being added.
            fragment (dict): Information about the fragment including its code, SMILES notation, and concentration.
            solvent_volume (float): The volume of the solvent to be used.
            ligand_transfer_volume (float): The volume of ligand to be transferred.
            ligand_concentration (float): The concentration of the ligand.
            is_solvent_test (bool, optional): Flag to indicate if this is a solvent test. Defaults to False.
    
        Returns:
            dict: A dictionary representing the response from the server, typically including the number
                  of modified documents, operation status, and matched documents count.
    
        Raises:
            Exception: If there is an error in parsing the JSON response or in the HTTP request.
        """
        library['_id'] = str(library['_id'])
        payload = {
            "library": library,
            "well_id": str(well_id),
            "fragment": fragment,
            "solvent_volume": solvent_volume,
            "ligand_transfer_volume": ligand_transfer_volume,
            "ligand_concentration": ligand_concentration,
            "is_solvent_test": is_solvent_test
        }
    
        try:
            response = requests.post(f"{self.base_url}/add_fragment_to_well/", json=payload)
            response.raise_for_status()  # Check for HTTP request errors
            result = response.json()
            return MockUpdateOneResultOld(result["result"]["nModified"], result["result"]["ok"], result["result"]["n"])
        except Exception as e:
            print(f"Error in add_fragment_to_well request: {e}")
            return None
    ### FETCH_TAG add_fragment_to_well

    ### FETCH_TAG remove_fragment_from_well
    def remove_fragment_from_well(self, well_id: ObjectId) -> dict:
        """
        Sends a POST request to the server to remove a fragment from a specified well. The well ID 
        is provided as an argument, and the function communicates with the FastAPI server endpoint 
        to perform the removal operation in the database.
    
        Args:
            well_id (ObjectId): The MongoDB ObjectId of the well from which the fragment is to be removed.
    
        Returns:
            dict: A dictionary representing the result of the database update operation. It includes 
                  'nModified' for the count of modified documents, 'ok' to indicate success, and 
                  'n' for the count of matched documents.
    
        Raises:
            JSONDecodeError: If the response body does not contain valid JSON.
            RequestException: For issues like network problems, or connection timeouts.
        """
        try:
            response = requests.post(f"{self.base_url}/remove_fragment_from_well/?well_id={str(well_id)}")
            response.raise_for_status()  # Raises HTTPError for bad HTTP response statuses
    
            result = response.json()
            result = MockUpdateOneResultOld(result["result"]["nModified"], result["result"]["ok"], result["result"]["n"])
            return result
        except json.JSONDecodeError as e:
            print(f"Could not parse JSON: {e}")
            return {}
        except requests.RequestException as e:
            print(f"Request failed: {e}")
            return {}
    ### FETCH_TAG remove_fragment_from_well

    ### FETCH_TAG import_library
    def import_library(self, library: dict) -> dict:
        """
        Sends a POST request to the FastAPI server to import a new library into the database.
    
        This method constructs a payload with the library data, converts the 'libraryBarcode' to a string for compatibility,
        and sends a POST request to the server's '/import_library/' endpoint. It processes the JSON response to extract the import result.
        In case of an error during the request or while parsing the JSON response, it handles the exception and returns an empty dictionary.
    
        Args:
            library (dict): A dictionary representing the library data to be imported.
    
        Returns:
            dict: A dictionary representing the result of the import operation. Returns an empty dictionary in case of an error.
    
        Raises:
            Exception: Captures any exception that occurs during the request or JSON parsing and logs the error message.
        """
        library['libraryBarcode'] = str(library['libraryBarcode'])
        library = convert_objects_to_serializable(library)
        response = requests.post(f"{self.base_url}/import_library/", json=library)
        try:
            result = response.json()
            return MockInsertOneResult(result["result"]["ok"] == 1.0, result["result"]["_id"])
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return {}
    ### FETCH_TAG import_library

    ### FETCH_TAG add_campaign_library
    def add_campaign_library(self, campaign_library: dict) -> dict:
        ### campaign_library = [convert_objects_to_serializable(item) for item in campaign_library]
        campaign_library = convert_objects_to_serializable(campaign_library)
        response = requests.post(f"{self.base_url}/add_campaign_library/", json=campaign_library)

        try:
            ### Get the response data
            campaign_library_info = response.json()
            ### The return format here is less important since add_campaign_library is an auxilliary function not present in the old ffcsdbclient
            ### For consistency, one might modify this function to resemble the output of add_well, which is a MockInsertOneResult object
            return campaign_library_info
        except Exception as e:
            print(f"Could not parse JSON: {e}")
            return None
    ### FETCH_TAG add_campaign_library

    ### FETCH_TAG get_library_usage_count
    def get_library_usage_count(self, user: str, campaign_id: str, library_id: str) -> int:
        """
        Sends a GET request to the FastAPI server to retrieve the count of wells associated with a specific 
        library within a user account and campaign. It handles the response and extracts the count.

        Args:
            user (str): The identifier of the user account.
            campaign_id (str): The identifier of the campaign.
            library_id (str): The identifier of the library.

        Returns:
            int: The count of wells associated with the specified library. Returns -1 to indicate an error 
                 in case the JSON response cannot be parsed.

        Raises:
            Exception: Captures any exception that occurs during the request or JSON parsing and logs the 
                       error message.
        """
        try:
            response = requests.get(
                f"{self.base_url}/get_library_usage_count/",
                params={"user": user, "campaign_id": campaign_id, "library_id": library_id}
            )
            data = response.json()
            return data.get("count", -1)  # Default to -1 if "count" key is not found
        except Exception as e:
            print(f"Error during GET request or JSON parsing: {e}")
            return -1

    # Map count_libraries_in_campaign to get_library_usage_count for backward compatibility
    count_libraries_in_campaign = get_library_usage_count
    ### FETCH_TAG get_library_usage_count

    ### FETCH_TAG_TEST test_dummy_01
    def test_dummy_01(self):
        print("test_dummy_01")
    ### FETCH_TAG_TEST test_dummy_01

    ### FETCH_TAG_TEST test_dummy_02
    def test_dummy_02(self):
        print("test_dummy_02")
    ### FETCH_TAG_TEST test_dummy_02

    ### FETCH_TAG_TEST test_dummy_03
    def test_dummy_03(self):
        print("test_dummy_03")
    ### FETCH_TAG_TEST test_dummy_03

def main():

    print("###")
    print("TEST IN main")
    print("###\n")

if __name__ == "__main__":
    main()
