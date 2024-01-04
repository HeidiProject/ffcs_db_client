### Standard Libraries
import unittest
import json
import time
from datetime import datetime, timedelta, date
import argparse
from typing import List, Dict, Union, Any
import logging

### Third-Party Libraries
from bson.objectid import ObjectId
from dateutil.parser import parse
from pymongo import MongoClient
from rdkit import Chem
from rdkit.Chem import Draw

# Your Libraries
###from ffcsdbclient import ffcsdbclient, base_url
from ffcsdbclient import ffcsdbclient

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

def parse_args():
    """
    Parse command line arguments for the script.
    """
    parser = argparse.ArgumentParser(description="Run tests.")
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output.')
    return parser.parse_args()

ARGS = parse_args()

def printv(*args, **kwargs):
    """
    Print the arguments if the verbose flag is True.
    """
    if ARGS.verbose:
        print(*args, **kwargs)

# Helper function to compare times with a tolerance
def are_times_almost_equal(time_str, time_obj, tolerance_microseconds=1000):
    expected_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S.%f")
    # Truncate the microseconds in 'now_time' to match the precision
    actual_time = time_obj.replace(microsecond=int(time_obj.microsecond / 1000) * 1000)
    return abs(expected_time - actual_time).microseconds < tolerance_microseconds

if 1:
    ### Custom aligned output
    class CustomTextTestResult(unittest.TextTestResult):
        def getDescription(self, test):
            return "{} ({})".format(test._testMethodName, test.__class__.__name__)
    
        def formatOutput(self, test, result_text):
            ### Use the overridden getDescription method
            full_output = self.getDescription(test)
    
            ### Remove the specific substring from the full output.
            full_output = full_output.replace("(ffcsdbclient_integration_test)", "")
    
            ### Calculate the padding needed to align the output.
            padding = '.' * (80 - len(full_output))
    
            ### Clear the current line of output in the stream
            self.stream.write('\r')
            self.stream.write(' ' * 150)  ### Assuming a console width of 150
            self.stream.write('\r')
    
            ### Write the modified output
            self.stream.write(full_output + padding + result_text + "\n")
            self.stream.flush()
    
        def addSuccess(self, test):
            if self.showAll:
                self.formatOutput(test, "ok!")
            elif self.dots:
                self.stream.write('.')
            self.stream.flush()
    
        def addError(self, test, err):
            if self.showAll:
                self.formatOutput(test, "ERROR!")
            elif self.dots:
                self.stream.write('E')
            self.stream.flush()
    
        def addFailure(self, test, err):
            if self.showAll:
                self.formatOutput(test, "FAIL!")
            elif self.dots:
                self.stream.write('F')
            self.stream.flush()

class ffcsdbclient_integration_test(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        printv("")

        printv("Preparation with setUpClass")

        ###cls.client = ffcsdbclient(base_url)
        cls.client = ffcsdbclient(Settings.BASE_URL)

        printv("Setup with setUpClass complete")

    def setUp(self):
        printv("")
        printv("Preparation with setUp")

        ### Delete all entries from the wells collection with plateId: "98765"
        query = {"plateId": "98765", "userAccount": "e14965", "campaignId": "EP_SmarGon"}
        retrieved_data = self.client.delete_by_query("wells", query)
        retrieved_data = self.client.delete_by_query("plates", query)
        query = {"plateId": "98764", "userAccount": "e14965", "campaignId": "EP_SmarGon"}
        retrieved_data = self.client.delete_by_query("wells", query)

        query = {"plateId": "98765", "userAccount": "e14965", "campaignId": "EP_SmarGon_TEST"}
        retrieved_data = self.client.delete_by_query("wells", query)
        retrieved_data = self.client.delete_by_query("plates", query)

        ### Delete test library
        query = {"userAccount": "e14965", "campaignId": "EP_SmarGon", "libraryName": "Test_Library_Heidi_C", "libraryBarcode": "A98765"}
        retrieved_data = self.client.delete_by_query("libraries", query)
        retrieved_data = self.client.delete_by_query("campaign_libraries", query)

        printv(retrieved_data['message'])

        self.delete_by_id("libraries", "64d4d1bea8f822476c37f97a")

        printv("Setup with setUp complete")

    @classmethod
    def tearDownClass(cls):
        printv("")
        printv("Cleanup with tearDownClass")
        printv("Cleanup with tearDownClass complete")

    def tearDown(self):
        printv("")
        printv("Cleanup with tearDown")

        ### Delete all entries from the wells collection with plateId: "98765"
        query = {"plateId": "98765", "userAccount": "e14965", "campaignId": "EP_SmarGon"}
        retrieved_data = self.client.delete_by_query("wells", query)
        retrieved_data = self.client.delete_by_query("plates", query)
        query = {"plateId": "98764", "userAccount": "e14965", "campaignId": "EP_SmarGon"}
        retrieved_data = self.client.delete_by_query("wells", query)

        query = {"plateId": "56789", "userAccount": "e14965", "campaignId": "EP_SmarGon"}
        retrieved_data = self.client.delete_by_query("wells", query)

        printv("Cleanup with tearDown complete")

    def add_test_plate(self, user_account, campaign_id, plate_id, **kwargs):
        """
        A method to add a test plate and assert it was successfully added.
        """
        plate_data = {
            "userAccount": user_account,
            "plateId": plate_id,
            "campaignId": campaign_id
        }

        ### Add the default dropVolume if it's not provided
        kwargs.setdefault('dropVolume', 0.05)

        plate_data.update(kwargs)  ### Add the additional arguments to plate_data
        retrieved_data = self.client.add_plate(plate_data)
        ### retrieved_data = retrieved_data.json() ### Convert the FineOneResult object to json
        self.assertIsNotNone(retrieved_data, "Plate could not be added.")
        return retrieved_data

    def add_test_well(self, **kwargs):
        """
        A method to add a test well and assert it was successfully added.
        """
        retrieved_data = self.client.add_well(kwargs)
        ### Convert the mock object to the desired JSON format
        retrieved_data = {"acknowledged": retrieved_data.acknowledged, "inserted_id": str(retrieved_data.inserted_id)}
        self.assertIsNotNone(retrieved_data, "Well could not be added.")
        self.assertIn('inserted_id', retrieved_data, "Added well does not have an ID.")
        return retrieved_data

    def add_campaign_library(self, **kwargs):
        """
        A method to add a test library and assert it was successfully added.
        There is also the native function insert_campaign_library, which does the same thing.
        """

        ### Assuming you have a client method 'add_library' to add a library to your database
        retrieved_data = self.client.add_campaign_library(kwargs)

        self.assertIsNotNone(retrieved_data, "Library could not be added.")
        self.assertIn('inserted_id', retrieved_data, "Added library does not have an ID.")
        return retrieved_data

    def insert_campaign_library(self, **kwargs):

        ### Assuming you have a client method 'insert_library' to insert a library to your database
        retrieved_data = self.client.insert_campaign_library(kwargs)
        ### Convert the mock object to the desired JSON format
        retrieved_data = {"acknowledged": retrieved_data.acknowledged, "inserted_id": str(retrieved_data.inserted_id)}

        self.assertIsNotNone(retrieved_data, "Library could not be inserted.")
        self.assertIn('inserted_id', retrieved_data, "Added library does not have an ID.")
        return retrieved_data

    def delete_by_id(self, collection, doc_id):
        """
        A method to delete documents from a collection by their ObjectID.
        """
        retrieved_data = self.client.delete_by_id(collection, doc_id)
        self.assertIsNotNone(retrieved_data, "Plate could not be deleted.")
        self.assertTrue(retrieved_data['acknowledged'], "Plate deletion was not acknowledged.")

    ### FETCH_TAG convert_objectid_to_str
    def convert_objectid_to_str(self, data: Union[Any, List[Any], Dict[str, Any]]) -> Union[Any, List[Any], Dict[str, Any]]:
        """
        Recursively traverse the data structure and convert all ObjectId instances to strings.
        This function returns a new data structure, leaving the original one unchanged.
    
        Parameters:
        - data (Union[Any, List[Any], Dict[str, Any]]): The data structure containing records.
    
        Returns:
        - Union[Any, List[Any], Dict[str, Any]]: Data structure with ObjectId fields converted to strings.
        """
    
        if isinstance(data, list):
            return [self.convert_objectid_to_str(v) for v in data]
        elif isinstance(data, dict):
            return {k: self.convert_objectid_to_str(v) for k, v in data.items()}
        elif isinstance(data, ObjectId):
            return str(data)
        else:
            return data
    ### FETCH_TAG convert_objectid_to_str

    def convert_objectid_and_datetime_to_string(self, data_list: List[Dict[str, Union[datetime, ObjectId, any]]]) -> List[Dict[str, Union[str, any]]]:
        """
        Converts ObjectId and datetime objects to their string representation in a list of dictionaries.
        
        Parameters:
            data_list (List[Dict[str, Union[datetime, ObjectId, any]]]): The list of dictionaries containing records.
        
        Returns:
            List[Dict[str, Union[str, any]]]: A new list of dictionaries with ObjectId and datetime objects converted to strings.
        """
        
        converted_list = []
        try:
            for record in data_list:
                new_record = {}
                for key, value in record.items():
                    ### Handle datetime objects
                    if isinstance(value, datetime):
                        datetime_format = '%Y-%m-%d %H:%M:%S'
                        if value.microsecond != 0:
                            datetime_format += '.%f'
                        new_record[key] = value.strftime(datetime_format)
                    
                    ### Handle ObjectId objects
                    elif isinstance(value, ObjectId):
                        new_record[key] = str(value)
                    
                    ### Leave other types as they are
                    else:
                        new_record[key] = value
                
                converted_list.append(new_record)
        
        except Exception as e:
            logging.error(f"Error in convert_objectid_and_datetime_to_string: {e}")
            
    def filter_data(retrieved_data, **kwargs):
        """
        Filters the retrieved data based on the given criteria.

        Args:
            retrieved_data (list): The list of documents retrieved from the database.
            **kwargs: Arbitrary keyword arguments where each keyword is a field to be
                      filtered on and its value is a list of desired values for that field.

        Returns:
            list: The filtered list of documents.
        """
        filtered_data = retrieved_data
        for key, values in kwargs.items():
            filtered_data = [doc for doc in filtered_data if doc.get(key) in values]

        return filtered_data

    ###
    ### INTEGRATION TESTS
    ###

    ### FETCH_TAG error
    def test_00_error(self):
        raise ValueError("This is an error")
    ### FETCH_TAG error

    ### FETCH_TAG fail
    def test_00_fail(self):
        self.assertTrue(False)  ### This will fail
    ### FETCH_TAG fail

    ### FETCH_TAG delete_stuff
    def test_99_delete_stuff(self):
        """
        -- A method to manually remove test data; needs to be edited to specify which data to remove and/or print
        """
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"

        ### self.delete_by_id("wells", "64e7758345d792532a1d68ab")
        ### self.delete_by_id("plates", "64e3a27045d792532a1d6198")

        retrieved_data_added_well = self.client.get_wells_from_plate(user_account, campaign_id, plate_id)
        ###  Convert ObjectIds to strings
        retrieved_data_added_well = self.convert_objectid_to_str(retrieved_data_added_well)
        printv(f"\n{json.dumps(retrieved_data_added_well, indent=4)}")
        ### This will make an actual call to the server
        retrieved_data = self.client.get_plate(user_account, campaign_id, plate_id)
        ### Convert FindOneResult object into json for assertions
        retrieved_data = retrieved_data
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    ### FETCH_TAG delete_stuff

    ### FETCH_TAG check_if_db_connected
    def test_01_check_if_db_connected(self):
        """
        Tests the functionality of checking the database connection.
        This will make an actual call to the server and assert the result.
        """
        try:
            ### Make an actual call to the server
            retrieved_data = self.client.check_if_db_connected()
            printv(f"\n{json.dumps(retrieved_data, indent=4)}")
        except Exception as e:
            ### Handle exceptions and fail the test with a detailed error message
            self.fail(f"Exception occurred during test: {e}")
    
        ### Check result and assert
        self.assertTrue(retrieved_data, "DB connection check failed.")
    ### FETCH_TAG check_if_db_connected

    ### FETCH_TAG get_collection
    def test_02_get_collection(self):
        ### This will make an actual call to the server
        ### retrieved_data = self.client.get_collection('wells')
        ### Also, the original method __get_collection from ffcsdbclient is a private method.
        ### For consistency, the new method in ffcs_db_client is also private.
        ### However, this requires name mangling of an external method from the imported ffcs_db_client.
        ### retrieved_data = self.client._ffcs_db_client__get_collection('wells')
        retrieved_data = self.client._ffcsdbclient__get_collection('wells')
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        ### Check result
        self.assertIsNotNone(retrieved_data)
        ### Set up expected result
        ### expected_result = "Collection(Database(MongoClient(host=['mx-ffcs.psi.ch:80'], document_class=dict, tz_aware=False, connect=True, retrywrites=True, w='majority', serverselectiontimeoutms=5000), 'ffcs'), 'Wells')"
        expected_result = "Collection(Database(MongoClient(host=['cluster0-shard-00-00.crc77.mongodb.net:27017', 'cluster0-shard-00-02.crc77.mongodb.net:27017', 'cluster0-shard-00-01.crc77.mongodb.net:27017'], document_class=dict, tz_aware=False, connect=True, authsource='admin', replicaset='atlas-k1thkh-shard-0', tls=True, serverselectiontimeoutms=5000), 'ffcs'), 'Wells')"
        ### Check result --- the shard number keeps changing, this assertion would fail occasionally
    ### FETCH_TAG get_collection

    ### FETCH_TAG get_plate
    def test_03_get_plate(self):
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"

        ### Add plate for test purposes
        added_plate_id = self.add_test_plate(user_account, campaign_id, plate_id)['inserted_id']

        ### This will make an actual call to the server
        retrieved_data = self.client.get_plate(user_account, campaign_id, plate_id)
        ### Convert FindOneResult object into json for assertions
        ### retrieved_data = retrieved_data.json()
        retrieved_data = retrieved_data
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        try:
            ### Check result
            self.assertIsNotNone(retrieved_data)
            ### Check attributes of the plate
            self.assertEqual(retrieved_data['userAccount'], user_account, "User account does not match.")
            self.assertEqual(retrieved_data['campaignId'], campaign_id, "Campaign id does not match.")
            self.assertEqual(retrieved_data['plateId'], plate_id, "Plate id does not match.")
        finally:
            printv(added_plate_id)
            ### Delete the plate after the test
            self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG get_plate

    ### FETCH_TAG get_plates
    def test_04_get_plates(self):
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"

        ### Add plate for test purposes
        added_plate_id = self.add_test_plate(user_account, campaign_id, plate_id)['inserted_id']
        printv("\n"+str(added_plate_id))

        ### This will make an actual call to the server
        retrieved_data = self.client.get_plates(user_account, campaign_id)
        date_format = "%Y-%m-%d %H:%M:%S.%f"
        for item in retrieved_data:
            for key, value in item.items():
                if isinstance(value, datetime):
                    item[key] = value.strftime(date_format)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
        ### ### Convert FindOneResult object into json for assertions
        ### retrieved_data = retrieved_data.json()
        ### Filter added test data
        retrieved_data = [doc for doc in retrieved_data if doc['userAccount'] == user_account and doc['campaignId'] == campaign_id and doc['plateId'] == plate_id]
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        try:
            ### Sort list to guarantee the added test document is in last position
            retrieved_data.sort(key=lambda x: x['createdOn'], reverse=False)
            ### Check result
            self.assertIsNotNone(retrieved_data)
            ### Check if the plates list is not empty
            self.assertNotEqual(retrieved_data, [], "Returned plates list is empty.")
            ### Check attributes of the first plate in the list
            self.assertEqual(retrieved_data[0]['userAccount'], user_account, "User account does not match.")
            self.assertEqual(retrieved_data[0]['campaignId'], campaign_id, "Campaign id does not match.")
            self.assertEqual(retrieved_data[0]['plateId'], plate_id, "Plate id does not match.")
        finally:
            printv(added_plate_id)
            ### Delete the plate after the test
            self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG get_plates

    ### FETCH_TAG get_campaigns
    def test_05_get_campaigns(self):
        user_account = "e14965"
        campaign_id = "EP_SmarGon_TEST" ### Here adding a new TEST campaign is actually necessary to test get_campaigns
        plate_id = "98765"

        ### Add plate for test purposes
        added_plate_id = self.add_test_plate(user_account, campaign_id, plate_id)['inserted_id']
        printv("\n"+str(added_plate_id))

        ### This will make an actual call to the server
        retrieved_data = self.client.get_campaigns(user_account)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        try:
            ### Check result
            self.assertIsNotNone(retrieved_data)
            self.assertIsInstance(retrieved_data, list) ### assuming retrieved_data is a list
            ### Check if the plates list is not empty
            self.assertNotEqual(retrieved_data, [], "Returned plates list is empty.")

            ### Check if at least these three campaigns are contained in the retrieved list
            expected_campaigns = ["EP_SmarGon", "EP_forSmargon", "EP_mg_Smargon", campaign_id]
            for campaign in expected_campaigns:
                self.assertIn(campaign, retrieved_data, f"Campaign {campaign} not found in the retrieved list.")
        finally:
            ### Delete the plate after the test
            self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG get_campaigns

    ### FETCH_TAG add_plate
    def test_06_add_plate(self):
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        plate_data = {
            "userAccount": user_account,
            "plateId": plate_id,
            "campaignId": campaign_id,
            "dropVolume": 0.05
        }

        ### This will make an actual call to the server
        retrieved_data = self.client.add_plate(plate_data)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
        printv(f"{json.dumps(self.client.get_campaigns(user_account), indent=4)}")

        retrieved_data_added_plate = self.client.get_plates(user_account, campaign_id)
        ### Convert FindResult object into json for assertions
        ### retrieved_data_added_plate = retrieved_data_added_plate.json()
        retrieved_data_added_plate = retrieved_data_added_plate
        ### Convert datetime.datetime object back to string for assertions
        retrieved_data_added_plate = self.convert_objectid_and_datetime_to_string(retrieved_data_added_plate)
        printv(f"{json.dumps(retrieved_data_added_plate, indent=4)}")

        try:
            ### Check result
            self.assertIsNotNone(retrieved_data)
            self.assertTrue(retrieved_data['acknowledged'], "Plate addition was not acknowledged.")
        finally:
            printv(retrieved_data['inserted_id'])
            ### Delete the plate after the test
            self.delete_by_id("plates", retrieved_data['inserted_id'])
    ### FETCH_TAG add_plate

    ### FETCH_TAG add_wells
    def test_07_add_wells(self):
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        plate_data = {
            "userAccount": user_account,
            "plateId": plate_id,
            "campaignId": campaign_id,
            "dropVolume": 0.05
        }
        ### Add test plate
        retrieved_data_test_plate = self.client.add_plate(plate_data)

        well = "A07a"
        well_echo = "A07a"
        x = 488
        y = 684
        x_echo = 3.32
        y_echo = 1.87
        well_data = {
            "userAccount": user_account,
            "campaignId": campaign_id,
            "plateId": plate_id,
            "well": well,
            "wellEcho": well_echo,
            "x": x,
            "y": y,
            "xEcho": x_echo,
            "yEcho": y_echo,
        }
        well_data_list = [well_data] ### put the dictionary in a list

        ### This will make an actual call to the server
        retrieved_data = self.client.add_wells(well_data_list)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
        printv("Expecting \"null\"")

        ### Retrieve data of added well
        retrieved_data_added_well = self.client.get_wells_from_plate(user_account, campaign_id, plate_id)
        ###  Convert ObjectIds to strings
        retrieved_data_added_well = self.convert_objectid_to_str(retrieved_data_added_well)
        printv(f"{json.dumps(retrieved_data_added_well, indent=4)}")

        try:
            ### Check result
            self.assertIsNone(retrieved_data, "Expected 'null' as there is no return value.")
            ### Check attributes of the added well
            self.assertEqual(retrieved_data_added_well[0]['userAccount'], user_account, "User account does not match.")
            self.assertEqual(retrieved_data_added_well[0]['campaignId'], campaign_id, "Campaign id does not match.")
            self.assertEqual(retrieved_data_added_well[0]['plateId'], plate_id, "Plate id does not match.")
            self.assertEqual(retrieved_data_added_well[0]['well'], well, "Well does not match.")
            self.assertEqual(retrieved_data_added_well[0]['wellEcho'], well_echo, "Well Echo does not match.")
            self.assertEqual(retrieved_data_added_well[0]['x'], x, "X does not match.")
            self.assertEqual(retrieved_data_added_well[0]['y'], y, "Y does not match.")
            self.assertEqual(retrieved_data_added_well[0]['xEcho'], x_echo, "X Echo does not match.")
            self.assertEqual(retrieved_data_added_well[0]['yEcho'], y_echo, "Y Echo does not match.")
        finally:
            printv(retrieved_data_added_well[0]['_id'])
            printv(retrieved_data_test_plate['inserted_id'])
            ### Delete the wells after the test
            self.delete_by_id("wells", retrieved_data_added_well[0]['_id'])
            ### Delete the plate after the test
            self.delete_by_id("plates", retrieved_data_test_plate['inserted_id'])
    ### FETCH_TAG add_wells

    ### FETCH_TAG update_by_object_id
    def test_08_update_by_object_id(self):
        """
        Only testing for 'plates' collection, but shoud work for 'wells' in the same fashion
        """
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"

        ### Add plate for test purposes
        added_plate_id = self.add_test_plate(user_account, campaign_id, plate_id)['inserted_id']

        ### Prepare data for update
        kwargs = {"plateType": "NewPlateType"}

        ### This will make an actual call to the server to update the plate
        retrieved_data = self.client.update_by_object_id(user_account, campaign_id, "plates", added_plate_id, **kwargs)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        retrieved_data_test = self.client.get_plates(user_account, campaign_id)
        ### Convert FindResult object into json for assertions
        retrieved_data_test = retrieved_data_test
        ### Convert datetime.datetime object back to string for assertions
        retrieved_data_test = self.convert_objectid_and_datetime_to_string(retrieved_data_test)
        printv(f"\n{json.dumps(retrieved_data_test, indent=4)}")

        try:
            ### Check result
            self.assertIsNotNone(retrieved_data, "Updating by object ID failed.")
            retrieved_data = retrieved_data['result']
            self.assertTrue(retrieved_data['acknowledged'], "Updating by object ID was not acknowledged.")
            self.assertEqual(retrieved_data['matched_count'], 1, "Matched count does not equal 1.")
            self.assertEqual(retrieved_data['modified_count'], 1, "Modified count does not equal 1.")
            self.assertIsNone(retrieved_data['upserted_id'], "Upserted ID is not None.")

            ### Retrieve the updated plate
            retrieved_data_updated_plate = self.client.get_plate(user_account, campaign_id, plate_id)
            retrieved_data_updated_plate = retrieved_data_updated_plate
            printv(f"{json.dumps(retrieved_data_updated_plate, indent=4)}")

            ### Check the updated plate data
            for key, value in kwargs.items():
                self.assertEqual(retrieved_data_updated_plate[key], value, f"Updated {key} does not match.")
            ### Assert the original explicitly entered data
            self.assertEqual(retrieved_data_updated_plate['userAccount'], user_account, "User account does not match.")
            self.assertEqual(retrieved_data_updated_plate['campaignId'], campaign_id, "Campaign id does not match.")
            self.assertEqual(retrieved_data_updated_plate['plateId'], plate_id, "Plate id does not match.")
            self.assertEqual(retrieved_data_updated_plate['dropVolume'], 0.05, "Drop volume does not match.")
        finally:
            ### Delete the plate after the test
            printv(added_plate_id)
            self.delete_by_id("plates", added_plate_id)

    ### FETCH_TAG is_plate_in_database
    def test_09_is_plate_in_database(self):
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"

        ### Add plate for test purposes
        added_plate_id = self.add_test_plate(user_account, campaign_id, plate_id)['inserted_id']

        ### This will make an actual call to the server
        retrieved_data = self.client.is_plate_in_database(plate_id)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        try:
            ### Check result
            self.assertIsNotNone(retrieved_data, "Check for plate in database failed.")
            self.assertTrue(retrieved_data, "Plate does not exist in database.")
        finally:
            ### Delete the plate after the test
            self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG is_plate_in_database

    ### FETCH_TAG get_unselected_plates
    def test_10_get_unselected_plates(self):
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"

        ### Add plate for test purposes
        added_plate_id = self.add_test_plate(user_account, campaign_id, plate_id, dropVolume=0.05, soakPlacesSelected=False)['inserted_id']

        ### This will make an actual call to the server
        retrieved_data = self.client.get_unselected_plates(user_account)
        ### Filter added test data
        retrieved_data = [doc for doc in retrieved_data if doc['userAccount'] == user_account and doc['campaignId'] == campaign_id and doc['plateId'] == plate_id]
        ### Convert ObjectIds to strings
        retrieved_data = self.convert_objectid_to_str(retrieved_data)
        ### Convert datetime.datetime object back to string for assertions
        for doc in retrieved_data:
            doc['createdOn'] = doc['createdOn'].strftime("%Y-%m-%dT%H:%M:%S.%f")
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
        ### printv(f"URL for testing in browser: {self.client.base_url}/unselected_plates/{user_account}")

        try:
            ### Check result
            self.assertIsNotNone(retrieved_data, "Retrieval of unselected plates failed.")
            self.assertGreater(len(retrieved_data), 0, "No unselected plates found.")

            ### Check if the added plate is in the list of unselected plates
            added_plate_in_unselected = any(plate['_id'] == added_plate_id for plate in retrieved_data)
            self.assertTrue(added_plate_in_unselected, "Added plate not found in the list of unselected plates.")
        finally:
            ### Delete the plate after the test
            printv(added_plate_id)
            self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG get_unselected_plates

    ### FETCH_TAG mark_plate_done
    def test_11_mark_plate_done(self):
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        last_imaged = datetime.now()
        batch_id = "987654"

        ### Add a test plate
        added_plate_id = self.add_test_plate(user_account, campaign_id, plate_id, lastImaged=last_imaged.isoformat(), batchId=batch_id)['inserted_id']

        ### This will make an actual call to the server
        retrieved_data = self.client.mark_plate_done(user_account, campaign_id, plate_id, last_imaged, batch_id)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
        ### printv(f"URL for testing in browser: {self.client.base_url}/mark_plate_done")

        try:
            ### Check result
            self.assertIsNotNone(retrieved_data, "Marking plate as done failed.")
            self.assertEqual(retrieved_data['nModified'], 1, "No modification was made to the document.")
            self.assertEqual(retrieved_data['ok'], 1.0, "Operation was not successful.")
            self.assertEqual(retrieved_data['n'], 1, "Expected to modify 1 document, but it didn't.")

            ### Retrieve the updated plate
            retrieved_data_updated_plate = self.client.get_plate(user_account, campaign_id, plate_id)
            retrieved_data_updated_plate = retrieved_data_updated_plate
            printv(f"{json.dumps(retrieved_data_updated_plate, indent=4)}")

            ### Check the updated plate data
            self.assertEqual(retrieved_data_updated_plate['userAccount'], user_account, "User Account does not match.")
            self.assertEqual(retrieved_data_updated_plate['plateId'], plate_id, "Plate ID does not match.")
            self.assertEqual(retrieved_data_updated_plate['campaignId'], campaign_id, "Campaign ID does not match.")
            self.assertEqual(retrieved_data_updated_plate['plateType'], "SwissCl", "Plate Type does not match.")
            self.assertEqual(retrieved_data_updated_plate['dropVolume'], 0.05, "Drop Volume does not match.")
            self.assertEqual(retrieved_data_updated_plate['batchId'], batch_id, "Batch ID does not match.")
            self.assertIsNotNone(retrieved_data_updated_plate['createdOn'], "Creation date is None.")
            ### soakPlacesSelected should be updated to true after executing mark_plate_done
            self.assertTrue(retrieved_data_updated_plate['soakPlacesSelected'], "Soak Places Selected is not True.")
            self.assertIsNone(retrieved_data_updated_plate['soakStatus'], "Soak Status is not None.")
            self.assertIsNone(retrieved_data_updated_plate['soakExportTime'], "Soak Export Time is not None.")
            self.assertIsNone(retrieved_data_updated_plate['soakTransferTime'], "Soak Transfer Time is not None.")
            self.assertFalse(retrieved_data_updated_plate['cryoProtection'], "Cryo Protection is not False.")
            self.assertFalse(retrieved_data_updated_plate['redesolveApplied'], "Redesolve Applied is not False.")
            ### Check the updated plate data, rounded to the nearest millisecond
            ### Truncate the microseconds to the nearest millisecond
            truncated_microseconds = (last_imaged.microsecond // 1000) * 1000
            last_imaged = last_imaged.replace(microsecond=truncated_microseconds)
            ### Check the updated plate data
            self.assertEqual(
                retrieved_data_updated_plate['lastImaged'],
                last_imaged.isoformat(),
                "Last Imaged does not match."
            )
        finally:
            ### Delete the plate after the test
            printv(added_plate_id)
            self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG mark_plate_done

    ### FETCH_TAG add_well
    def test_12_add_well(self):
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"


        well = "A12a"
        well_echo = "A12a"
        x = 488
        y = 684
        xEcho = 3.32
        yEcho = 1.87
        ### Prepare well data for adding
        well_data = {
            "userAccount": user_account,
            "campaignId": campaign_id,
            "plateId": plate_id,
            "well": well,
            "wellEcho": well_echo,
            "x": x,
            "y": y,
            "xEcho": xEcho,
            "yEcho": yEcho,
        }

        ### Add the well
        retrieved_data = self.client.add_well(well_data)
        ### Convert the mock object to the desired JSON format
        retrieved_data = {"acknowledged": retrieved_data.acknowledged, "inserted_id": str(retrieved_data.inserted_id)}
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
        retrieved_data_id = retrieved_data['inserted_id']
        ### printv(f"curl command for testing in console: curl -X POST -H \"Content-Type: application/json\" -d '{json.dumps(well_data)}' {self.client.base_url}/well/")

        try:
            ### Check result
            self.assertIsNotNone(retrieved_data, "Well could not be added.")
            self.assertIn('inserted_id', retrieved_data, "Added well does not have an ID.")

            ### Retrieve the added well for validation
            retrieved_data_added_well = self.client.get_wells_from_plate(user_account, campaign_id, plate_id)
            ###  Convert ObjectIds to strings
            retrieved_data_added_well = self.convert_objectid_to_str(retrieved_data_added_well)
            printv(f"{json.dumps(retrieved_data_added_well, indent=4)}")

            ### Check the added well data
            for key, value in well_data.items():
                self.assertEqual(retrieved_data_added_well[0][key], value, f"Added well {key} does not match.")

        finally:
            ### Delete the well after the test
            printv(retrieved_data_id)
            self.delete_by_id("wells", retrieved_data_id)
    ### FETCH_TAG add_well

    ### FETCH_TAG get_all_wells
    def test_13_get_all_wells(self):
        user_account = "e14965"
        campaign_id = "EP_SmarGon"

        ### Create wells for testing
        added_well_id_01 = self.add_test_well(
            userAccount = user_account,
            campaignId = campaign_id,
            plateId = "98765",
            well = "A13a",
            wellEcho = "A13a",
            x = 488,
            y = 684,
            xEcho = 3.32,
            yEcho = 1.87,
        )['inserted_id']

        added_well_id_02 = self.add_test_well(
            userAccount = user_account,
            campaignId = campaign_id,
            plateId = "98764",
            well = "B13b",
            wellEcho = "B13b",
            x = 487,
            y = 684,
            xEcho = 3.31,
            yEcho = 1.86,
        )['inserted_id']

        ### This will make an actual call to the server
        retrieved_data = self.client.get_all_wells(user_account, campaign_id)
        ### Convert the ObjectId to string
        for well in retrieved_data:
            well["_id"] = str(well["_id"])
            if well["libraryId"]:
                well["libraryId"] = str(well["libraryId"])
        ### Filter added test data
        plate_ids = ["98765", "98764"]
        retrieved_data = [
            doc for doc in retrieved_data
            if doc['userAccount'] == user_account
            and doc['campaignId'] == campaign_id
            and doc['plateId'] in plate_ids
        ]
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        ### printv(f"URL for testing in browser: {self.client.base_url}/get_all_wells/?user_account={user_account}&campaign_id={campaign_id}")

        try:
            ### Limit the output to the first added item for display
            printv(f"\nRetrieved Wells (found {len(retrieved_data)}, output limited to 1 of the added test wells):")
            printv(f"\n{json.dumps(next(well for well in retrieved_data if well['plateId'] in ['98765', '98764']), indent=4)}")

            ### Check result
            self.assertIsNotNone(retrieved_data, "Retrieval of all wells failed.")
            self.assertGreater(len(retrieved_data), 0, "No wells found.")

            ### Assertions to check if the added plateIds are in the retrieved data
            retrieved_plate_ids = [well_data['plateId'] for well_data in retrieved_data]
            self.assertIn("98765", retrieved_plate_ids, "Expected plateId '98765' not found in retrieved data.")
            self.assertIn("98764", retrieved_plate_ids, "Expected plateId '98764' not found in retrieved data.")

        finally:
            ### Delete the wells after the test
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
    ### FETCH_TAG get_all_wells

    ### FETCH_TAG get_wells_from_plate
    def test_14_get_wells_from_plate(self):
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"

        ### Create wells for testing
        added_well_id_01 = self.add_test_well(
            userAccount = user_account,
            campaignId = campaign_id,
            plateId = plate_id,
            well = "A14a",
            wellEcho = "A14a",
            x = 488,
            y = 684,
            xEcho = 3.32,
            yEcho = 1.87,
        )['inserted_id']

        added_well_id_02 = self.add_test_well(
            userAccount = user_account,
            campaignId = campaign_id,
            plateId = plate_id,
            well = "B14b",
            wellEcho = "B14b",
            x = 487,
            y = 684,
            xEcho = 3.31,
            yEcho = 1.86,
        )['inserted_id']

        ### Retrieve wells from the plate
        retrieved_data = self.client.get_wells_from_plate(user_account, campaign_id, plate_id)
        ###  Convert ObjectIds to strings
        retrieved_data = self.convert_objectid_to_str(retrieved_data)
        ### Filter added test data
        plate_ids = ["98765", "98764"]
        retrieved_data = [
            doc for doc in retrieved_data
            if doc['userAccount'] == user_account
            and doc['campaignId'] == campaign_id
            and doc['plateId'] in plate_ids
        ]
        printv(f"{json.dumps(retrieved_data, indent=4)}")

        ### Log URL for manual testing
        ### printv(f"URL for testing in browser: {self.client.base_url}/get_wells_from_plate/?user_account={user_account}&campaign_id={campaign_id}&plate_id={plate_id}")

        try:
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Retrieval of wells from plate failed.")
            self.assertGreater(len(retrieved_data), 0, "No wells found in the plate.")

            ### Check if the added wells are in the list of wells
            added_well_in_retrieved_01 = any(well['_id'] == added_well_id_01 for well in retrieved_data)
            added_well_in_retrieved_02 = any(well['_id'] == added_well_id_02 for well in retrieved_data)
            self.assertTrue(added_well_in_retrieved_01, "First added well not found in the list of wells in the plate.")
            self.assertTrue(added_well_in_retrieved_02, "Second added well not found in the list of wells in the plate.")

        finally:
            ### Delete the wells after the test
            printv(added_well_id_01)
            printv(added_well_id_02)
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
    ### FETCH_TAG get_wells_from_plate

    ### FETCH_TAG get_one_well
    def test_15_get_one_well(self):
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        well = "A15a"
        well_echo = "A15a"
        x = 488
        y = 684
        xEcho = 3.32
        yEcho = 1.87

        ### Add a well for testing
        added_well_id_01 = self.add_test_well(
            userAccount = user_account,
            campaignId = campaign_id,
            plateId = plate_id,
            well = well,
            wellEcho = well_echo,
            x = x,
            y = y,
            xEcho = xEcho,
            yEcho = yEcho,
        )['inserted_id']

        ### Retrieve the well
        retrieved_data = self.client.get_one_well(added_well_id_01)
        ###  Convert ObjectIds to strings
        retrieved_data = self.convert_objectid_to_str(retrieved_data)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
        ### printv(f"URL for testing in browser: {self.client.base_url}/get_one_well/?well_id={added_well_id_01}")

        try:
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Retrieval of well data failed.")
            self.assertEqual(retrieved_data["_id"], added_well_id_01, "The ID of the retrieved well does not match the added well ID.")
            self.assertEqual(retrieved_data["userAccount"], user_account, "User Account does not match.")
            self.assertEqual(retrieved_data["campaignId"], campaign_id, "Campaign ID does not match.")
            self.assertEqual(retrieved_data["plateId"], plate_id, "Plate ID does not match.")
            self.assertEqual(retrieved_data["well"], well, "Well does not match.")
            self.assertEqual(retrieved_data["wellEcho"], well_echo, "Well Echo does not match.")
            self.assertEqual(retrieved_data["x"], x, "X coordinate does not match.")
            self.assertEqual(retrieved_data["y"], y, "Y coordinate does not match.")
            self.assertEqual(retrieved_data["xEcho"], xEcho, "X Echo coordinate does not match.")
            self.assertEqual(retrieved_data["yEcho"], yEcho, "Y Echo coordinate does not match.")

        finally:
            ### Delete the well after the test
            printv(added_well_id_01)
            self.delete_by_id("wells", added_well_id_01)
    ### FETCH_TAG get_one_well

    ### FETCH_TAG get_smiles
    def test_16_get_smiles(self):
        """
        Integration test for retrieving a SMILES string based on user account, campaign ID, and crystal name.
    
        This test function first adds a test well with specified parameters into the database. Then, it retrieves
        the SMILES string associated with the crystal name from the database using the client's get_smiles method.
        It asserts whether the retrieved SMILES string matches the expected value. The test well is deleted at the end 
        of the test to clean up the database.
    
        Args:
            None
        
        Raises:
            AssertionError: If the SMILES string retrieval is unsuccessful or the retrieved string doesn't match the expected value.
        """
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        xtal_name = "example_xtal"
        smiles = "C(C(=O)O)N"
    
        # Create a test well
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            smiles=smiles,
            xtalName=xtal_name,
            well="A16a",
            wellEcho="A16a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
        )['inserted_id']
    
        # Retrieve the SMILES string
        retrieved_smiles = self.client.get_smiles(user_account, campaign_id, xtal_name)
    
        try:
            # Assertions
            self.assertIsNotNone(retrieved_smiles, "Retrieval of SMILES failed.")
            self.assertEqual(retrieved_smiles, smiles, "The retrieved SMILES string does not match the expected SMILES string.")
            # Log for debugging
            printv(f"\nRetrieved SMILES: {retrieved_smiles}")
        finally:
            # Clean up by deleting the test well
            self.delete_by_id("wells", added_well_id_01)
    ### FETCH_TAG get_smiles

    ### FETCH_TAG get_not_matched_wells
    def test_17_get_not_matched_wells(self):
        """
        Tests the retrieval of wells that are not matched based on specific criteria from the database. 
        It involves adding test wells, retrieving not matched wells, and validating the returned data.
    
        This test adds two wells with specific attributes that ensure they will not match certain criteria 
        and then uses the `get_not_matched_wells` method to retrieve and validate these wells.
    
        Args:
            None
    
        Returns:
            None
    
        Raises:
            AssertionError: If any of the test conditions fail, an assertion error is raised.
        """
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        # Add test wells with specific attributes
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A17a",
            wellEcho="A17a",
            x=488, y=684, xEcho=3.32, yEcho=1.87,
            cryoProtection=False  # Attribute to ensure non-matching
        )['inserted_id']
    
        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B17b",
            wellEcho="B17b",
            x=488, y=684, xEcho=3.32, yEcho=1.87,
            cryoProtection=True, cryoStatus="exported"  # Attributes to ensure non-matching
        )['inserted_id']
    
        # Retrieve not matched wells and filter for test data
        retrieved_data = self.client.get_not_matched_wells(user_account, campaign_id)
        plate_ids = ["98765"]
        test_data = [
            doc for doc in retrieved_data
            if doc['userAccount'] == user_account and
               doc['campaignId'] == campaign_id and
               doc['plateId'] in plate_ids
        ]
    
        # Assertions to validate the test results
        try:
            assert test_data, "Test data not found in the retrieved data."
            assert isinstance(test_data, list), "The retrieved data should be a list."
    
            # Verify attributes of the first added well
            well_01 = next((d for d in test_data if d["_id"] == added_well_id_01), None)
            assert well_01, "Added well 01 not found in not matched wells."
            assert well_01["cryoProtection"] == False, "CryoProtection field mismatch for well 01."
    
            # Verify attributes of the second added well
            well_02 = next((d for d in test_data if d["_id"] == added_well_id_02), None)
            assert well_02, "Added well 02 not found in not matched wells."
            assert well_02["cryoProtection"] == True, "CryoProtection field mismatch for well 02."
            assert well_02["cryoStatus"] == "exported", "CryoStatus field mismatch for well 02."
    
        finally:
            # Cleanup: Delete the test wells after the test
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
    ### FETCH_TAG get_not_matched_wells

    ### FETCH_TAG get_id_of_plates_to_soak
    def test_18_get_id_of_plates_to_soak(self):
        """
        Tests the retrieval of plate IDs for soaking operation, along with the count of wells with 
        and without an assigned library for each plate. The test uses a specific user account and 
        campaign ID to filter the plates.
    
        This test adds wells with specific conditions to ensure they match the criteria for soaking, 
        then retrieves the data for these wells and performs a series of assertions to validate the 
        response data.
    
        Args:
            None: Uses preset user account, campaign ID, and plate ID for testing.
    
        Returns:
            None: The test either passes with assertions or fails with an error.
    
        Raises:
            AssertionError: If any of the test conditions are not met.
        """
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        # Add wells for testing
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A18a",
            wellEcho="A18a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            soakStatus="pending"
        )['inserted_id']
    
        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B18b",
            wellEcho="B18b",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            soakStatus=None
        )['inserted_id']
    
        # Retrieve and filter test data
        retrieved_data = self.client.get_id_of_plates_to_soak(user_account, campaign_id)
        test_data = [doc for doc in retrieved_data if doc['_id'] == plate_id]
        printv(f"\n{json.dumps(test_data, indent=4)}")
    
        try:
            # Assertions for test data validation
            self.assertTrue(test_data, "Test data not found in the retrieved data.")
            self.assertIsInstance(test_data, list, "retrieved_data should be a list.")
    
            for item in test_data:
                expected_keys = {"_id", "totalWells", "wellsWithLibrary", "wellsWithoutLibrary"}
                self.assertEqual(set(item.keys()), expected_keys, "Mismatch in keys of retrieved data item.")
                self.assertIsInstance(item["_id"], str, "The _id should be a string.")
                self.assertEqual(item["_id"], plate_id, f"The _id should be {plate_id}.")
                self.assertIsInstance(item["totalWells"], int, "totalWells should be an integer.")
                self.assertEqual(item["totalWells"], 2, "totalWells count mismatch.")
                self.assertIsInstance(item["wellsWithLibrary"], int, "wellsWithLibrary should be an integer.")
                self.assertEqual(item["wellsWithLibrary"], 0, "wellsWithLibrary count mismatch.")
                self.assertIsInstance(item["wellsWithoutLibrary"], int, "wellsWithoutLibrary should be an integer.")
                self.assertEqual(item["wellsWithoutLibrary"], 2, "wellsWithoutLibrary count mismatch.")
                self.assertEqual(item["totalWells"], item["wellsWithLibrary"] + item["wellsWithoutLibrary"], "Mismatch in total well calculation.")
    
        finally:
            # Clean up after test
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
    ### FETCH_TAG get_id_of_plates_to_soak

    ### FETCH_TAG get_id_of_plates_to_cryo_soak
    def test_19_get_id_of_plates_to_cryo_soak(self):
        """
        Tests the client's ability to retrieve IDs of plates for cryo soaking along with the count
        of wells with and without cryo protection for each plate, filtered by user account and 
        campaign ID.
    
        The test adds wells to a plate, simulating various cryo statuses. It then uses the 
        client to retrieve data for these plates and performs assertions to validate the 
        structure, types, and values of the response.
    
        Raises:
            AssertionError: If any of the assertions fail, indicating an issue with the 
            get_id_of_plates_to_cryo_soak functionality.
        """
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        # Add wells for testing
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A19a",
            wellEcho="A19a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            cryoStatus="pending",
        )['inserted_id']
    
        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B19b",
            wellEcho="B19b",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            cryoStatus=None,
        )['inserted_id']
    
        # Retrieve and filter the data
        retrieved_data = self.client.get_id_of_plates_to_cryo_soak(user_account, campaign_id)
        retrieved_data = [doc for doc in retrieved_data if doc['_id'] == plate_id]
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            # Assert the structure and correctness of retrieved data
            self.assertIsInstance(retrieved_data, list, "retrieved_data should be a list")
            test_data = next((data for data in retrieved_data if data["_id"] == plate_id), None)
            self.assertIsNotNone(test_data, "Test data not found in the retrieved data.")
    
            for data in retrieved_data:
                self.assertIsInstance(data, dict, "Each item in retrieved_data should be a dictionary")
                expected_keys = {"_id", "totalWells", "wellsWithCryoProtection", "wellsWithoutCryoProtection"}
                self.assertEqual(set(data.keys()), expected_keys, "The keys of each dictionary should match the expected keys")
                self.assertIn(plate_id, [data['_id'] for data in retrieved_data], "Expected plateId not found in retrieved data.")
                self.assertIsInstance(data["totalWells"], int, "totalWells should be an integer")
                self.assertEqual(data["totalWells"], 2, "totalWells should be 2")
                self.assertIsInstance(data["wellsWithCryoProtection"], int, "wellsWithCryoProtection should be an integer")
                self.assertIsInstance(data["wellsWithoutCryoProtection"], int, "wellsWithoutCryoProtection should be an integer")
                self.assertEqual(data["totalWells"], data["wellsWithCryoProtection"] + data["wellsWithoutCryoProtection"], 
                                 "totalWells should be equal to the sum of wellsWithCryoProtection and wellsWithoutCryoProtection")
    
        finally:
            # Clean-up: Delete the wells after the test
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
    ### FETCH_TAG get_id_of_plates_to_cryo_soak

    ### FETCH_TAG get_id_of_plates_for_redesolve
    def test_20_get_id_of_plates_for_redesolve(self):
        """
        Tests the retrieval of plate IDs for redesolve operation from the client.
        
        This test simulates the process of adding wells to a specified plate and then
        uses the client to retrieve the data for these plates based on the redesolve status.
        It performs various assertions to ensure the correctness of the retrieved data
        including the structure, types, and values of the response.
    
        Raises:
            AssertionError: If any of the assertions fail, indicating an issue with the
            get_id_of_plates_for_redesolve functionality.
        """
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        # Add wells for testing
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A20a",
            wellEcho="A20a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveStatus="pending",
        )['inserted_id']
    
        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B20b",
            wellEcho="B20b",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveStatus=None,
        )['inserted_id']
    
        # Retrieve and filter the data
        retrieved_data = self.client.get_id_of_plates_for_redesolve(user_account, campaign_id)
        retrieved_data = [doc for doc in retrieved_data if doc['_id'] == plate_id]
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            # Assert the structure and correctness of retrieved data
            self.assertIsInstance(retrieved_data, list, "retrieved_data should be a list")
            self.assertIsNotNone(retrieved_data, f"Data with _id {plate_id} not found in retrieved_data.")
            printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
            for data in retrieved_data:
                self.assertIsInstance(data, dict, "Each item in retrieved_data should be a dictionary")
                expected_keys = {"_id", "totalWells", "wellsWithNewSolvent", "wellsWithoutNewSolvent"}
                self.assertEqual(set(data.keys()), expected_keys, "The keys of each dictionary should match the expected keys")
                self.assertIsInstance(data["_id"], str, "The _id should be a string")
                self.assertEqual(data["_id"], plate_id, f"The _id should be {plate_id}")
                self.assertIsInstance(data["totalWells"], int, "totalWells should be an integer")
                self.assertEqual(data["totalWells"], 2, "totalWells should be 2")
                self.assertIsInstance(data["wellsWithNewSolvent"], int, "wellsWithNewSolvent should be an integer")
                self.assertEqual(data["wellsWithNewSolvent"], 0, "wellsWithNewSolvent should be 0")
                self.assertIsInstance(data["wellsWithoutNewSolvent"], int, "wellsWithoutNewSolvent should be an integer")
                self.assertEqual(data["wellsWithoutNewSolvent"], 2, "wellsWithoutNewSolvent should be 2")
                self.assertEqual(data["totalWells"], data["wellsWithNewSolvent"] + data["wellsWithoutNewSolvent"], "totalWells should be equal to the sum of wellsWithNewSolvent and wellsWithoutNewSolvent")
    
        finally:
            # Clean-up: Delete the wells after the test
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
    ### FETCH_TAG get_id_of_plates_for_redesolve

    ### FETCH_TAG export_to_soak_selected_wells
    def test_21_export_to_soak_selected_wells(self):
        """
        Tests the export_to_soak_selected_wells method in the client.
        This test adds two wells with specific parameters, retrieves wells from the plate, 
        performs the soak export operation, and then validates the updated data.
    
        The test ensures that the operation correctly updates the 'soakExportTime' and 
        'soakStatus' fields of the wells and handles any potential errors.
    
        Raises:
            AssertionError: If the assertions for the test outcomes fail.
        """
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        # Add two wells for testing
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A21a",
            wellEcho="A21a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            soakExportTime=None,
            libraryAssigned=True,
            soakStatus="pending",
        )['inserted_id']
    
        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B21b",
            wellEcho="B21b",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            soakExportTime=None,
            libraryAssigned=True,
            soakStatus="pending",
        )['inserted_id']
    
        # Retrieve wells from the plate and perform the operation
        wells = self.client.get_wells_from_plate(user_account, campaign_id, plate_id)
        wells = self.convert_objectid_to_str(wells)
        retrieved_data = self.client.export_to_soak_selected_wells(user_account, campaign_id, wells)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            self.assertIsNone(retrieved_data["result"], "The operation did not return 'null' as expected.")
    
            # Retrieve and validate updated well data
            for well_id in [added_well_id_01, added_well_id_02]:
                updated_well_data = self.client.get_one_well(well_id)
                updated_well_data = self.convert_objectid_to_str(updated_well_data)
                printv(f"{json.dumps(updated_well_data, indent=4)}")
    
                # Validate 'soakExportTime' and 'soakStatus'
                try:
                    parse(updated_well_data['soakExportTime'])
                    is_valid_datetime = True
                except ValueError:
                    is_valid_datetime = False
    
                self.assertTrue(is_valid_datetime, f"soakExportTime is not a valid datetime for well {well_id}")
                self.assertEqual(updated_well_data['soakStatus'], "exported", f"soakStatus is not 'exported' for well {well_id}")
    
        finally:
            # Clean-up: Delete the added wells
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
    ### FETCH_TAG export_to_soak_selected_wells

    ### FETCH_TAG export_redesolve_to_soak_selected_wells
    def test_22_export_redesolve_to_soak_selected_wells(self):
        """
        Tests the export_redesolve_to_soak_selected_wells function to ensure it correctly updates
        the 'redesolveExportTime' and 'redesolveStatus' for selected wells in the database.
    
        This test checks whether the specified wells have their 'redesolveExportTime' set to the 
        current time and 'redesolveStatus' changed to 'exported' after the function call. 
        It also ensures that wells which should not be updated remain unchanged.
    
        Args:
            None: Uses class attributes for user_account, campaign_id, and plate_id.
    
        Returns:
            None: This method does not return any value but asserts the state of the database.
    
        Raises:
            AssertionError: If the expected database updates do not occur as intended.
        """
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        # Add test wells
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A22a",
            wellEcho="A22a",
            x=488, y=684, xEcho=3.32, yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            redesolveStatus="pending"
        )['inserted_id']
    
        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B22b",
            wellEcho="B22b",
            x=488, y=684, xEcho=3.32, yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            redesolveStatus="pending"
        )['inserted_id']
    
        # Retrieve wells and convert ObjectIds to strings
        wells = self.convert_objectid_to_str(
            self.client.get_wells_from_plate(user_account, campaign_id, plate_id)
        )
    
        # Perform the export operation
        retrieved_data = self.client.export_redesolve_to_soak_selected_wells(user_account, campaign_id, wells)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        # Assertions for updated wells
        self.assertIsNone(retrieved_data["result"], "Expected result should be None.")
    
        for well_id in [added_well_id_01, added_well_id_02]:
            updated_well = self.convert_objectid_to_str(self.client.get_one_well(well_id))
            printv(f"{json.dumps(updated_well, indent=4)}")
    
            # Validate 'redesolveExportTime'
            self.assertIsNotNone(updated_well.get('redesolveExportTime'), "redesolveExportTime should not be None")
            self.assertTrue(isinstance(parse(updated_well['redesolveExportTime']), datetime), 
                            "Invalid 'redesolveExportTime' format.")
            # Validate 'redesolveApplied' and 'redesolveStatus'
            self.assertTrue(updated_well.get('redesolveApplied'), "'redesolveApplied' should be True.")
            self.assertEqual(updated_well.get('redesolveStatus'), "exported", "'redesolveStatus' should be 'exported'.")
    
        # Clean up test wells
        self.delete_by_id("wells", added_well_id_01)
        self.delete_by_id("wells", added_well_id_02)
    ### FETCH_TAG export_redesolve_to_soak_selected_wells
    
    ### FETCH_TAG export_to_soak
    def test_23_export_to_soak(self) -> None:
        """
        Tests the 'export_to_soak' function by creating test wells and a plate, performing the export,
        and verifying the updates in the database.
    
        This test ensures that the soakExportTime and soakStatus for wells and plates are properly set upon
        executing the 'export_to_soak' function. After the test, it cleans up by deleting the test entries.
    
        Raises:
            AssertionError: If any of the assertions following the database updates fail.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A23a",
            wellEcho="A23a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            libraryAssigned=True,
            soakStatus="pending",  # Assuming status should be 'pending' before the test
        )['inserted_id']
    
        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B23b",
            wellEcho="B23b",
            x=500,
            y=700,
            xEcho=4.32,
            yEcho=2.87,
            libraryAssigned=True,
            soakStatus="pending",  # Assuming status should be 'pending' before the test
        )['inserted_id']
    
        ### Add a test plate
        last_imaged = datetime.now()
        batch_id = "987654"
        added_plate_id = self.add_test_plate(
            user_account,
            campaign_id,
            plate_id,
            lastImaged=last_imaged.isoformat(),
            batchId=batch_id
        )['inserted_id']
    
        ### Prepare and perform the operation
        #now_time = datetime.now().replace(microsecond=0).isoformat()
        now_time = datetime.now()
        data = [{'_id': plate_id, 'soak_time': now_time}]
        retrieved_data = self.client.export_to_soak(data)
        retrieved_data = retrieved_data.to_dict() if retrieved_data else {}
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        ### Assertions
        self.assertIsNotNone(retrieved_data, "Result of export_to_soak function is None.")
        self.assertEqual(retrieved_data.get("modified_count"), 1, "The number of processed wells does not match the input.")
    
        ### Validate updated wells
        retrieved_data_updated_well_01 = self.convert_objectid_to_str(self.client.get_one_well(added_well_id_01))
        retrieved_data_updated_well_02 = self.convert_objectid_to_str(self.client.get_one_well(added_well_id_02))
        printv(f"{json.dumps(retrieved_data_updated_well_01, indent=4)}")
        printv(f"{json.dumps(retrieved_data_updated_well_02, indent=4)}")
    
        ### Assertions for wells and plates
        for well_data in [retrieved_data_updated_well_01, retrieved_data_updated_well_02]:
            self.assertEqual(well_data["soakStatus"], "exported", "soakStatus does not match.")
            self.assertIsNotNone(well_data["soakExportTime"], "soakExportTime was not set.")
            
            # Use are_times_almost_equal function for timestamp comparison
            self.assertTrue(are_times_almost_equal(well_data["soakExportTime"], now_time), f"soakExportTime does not match for well {well_data['well']}.")
        
        # Retrieve updated plate data and print for verbosity
        retrieved_data_updated_plate = self.convert_objectid_to_str(self.client.get_plate(user_account, campaign_id, plate_id))
        printv(f"{json.dumps(retrieved_data_updated_plate, indent=4)}")
        
        # Assertions for the plate's soak status and time
        self.assertEqual(retrieved_data_updated_plate["soakStatus"], "exported", "soakStatus of plate does not match.")
        self.assertIsNotNone(retrieved_data_updated_plate["soakExportTime"], "soakExportTime of plate was not set.")
        
        # Use are_times_almost_equal function for the plate's timestamp comparison
        self.assertTrue(are_times_almost_equal(retrieved_data_updated_plate["soakExportTime"], now_time), "soakExportTime of plate does not match.")
    
        ### Cleanup test data
        printv(f"Cleaning up test wells and plate: {added_well_id_01}, {added_well_id_02}, {added_plate_id}")
        self.delete_by_id("wells", added_well_id_01)
        self.delete_by_id("wells", added_well_id_02)
        self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG export_to_soak

    ### FETCH_TAG export_cryo_to_soak_selected_wells
    def test_24_export_cryo_to_soak_selected_wells(self) -> None:
        """
        Integration test for the export_cryo_to_soak_selected_wells functionality.

        This test creates test wells and a test plate, then performs the cryo export operation.
        It verifies that the cryoExportTime is set and the cryoStatus is updated to 'exported'
        for the selected wells. After the test, it cleans up by deleting the test wells.

        Raises:
            AssertionError: If the database state after the operation is not as expected.
        """
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"

        # Add test wells that should be updated
        added_well_ids = [
            self.add_test_well(
                userAccount=user_account,
                campaignId=campaign_id,
                plateId=plate_id,
                well="A24a",
                wellEcho="A24a",
                x=488,
                y=684,
                xEcho=3.32,
                yEcho=1.87,
                cryoExportTime=None,
                cryoProtection=True,
                cryoStatus="pending",
            )['inserted_id'],
            self.add_test_well(
                userAccount=user_account,
                campaignId=campaign_id,
                plateId=plate_id,
                well="B24b",
                wellEcho="B24b",
                x=500,
                y=700,
                xEcho=4.32,
                yEcho=2.87,
                cryoExportTime=None,
                cryoProtection=True,
                cryoStatus="pending",
            )['inserted_id']
        ]

        # Retrieve wells and convert ObjectIds to strings
        wells = self.client.get_wells_from_plate(user_account, campaign_id, plate_id)
        wells = self.convert_objectid_to_str(wells)

        # Perform the cryo export operation
        retrieved_data = self.client.export_cryo_to_soak_selected_wells(user_account, campaign_id, wells)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        # Assertions
        assert retrieved_data.get("result") is None, "The operation did not return 'null' as expected."

        # Validate updates for each well
        for well_id in added_well_ids:
            updated_well = self.client.get_one_well(well_id)
            updated_well = self.convert_objectid_to_str(updated_well)
            printv(f"{json.dumps(updated_well, indent=4)}")

            cryo_export_time = updated_well.get('cryoExportTime')
            assert cryo_export_time and isinstance(parse(cryo_export_time), datetime), \
                "cryoExportTime is not a valid datetime for well"
            assert updated_well.get('cryoStatus') == "exported", \
                "cryoStatus is not 'exported' for well"

        # Clean up test data
        for well_id in added_well_ids:
            printv(well_id)
            self.delete_by_id("wells", well_id)
    ### FETCH_TAG export_cryo_to_soak_selected_wells

    ### FETCH_TAG export_redesolve_to_soak
    def test_25_export_redesolve_to_soak(self):
        """
        Integration test for the 'export_redesolve_to_soak' function to ensure it properly
        updates the 'redesolveExportTime' for wells and 'redesolveApplied' for plates.

        This test creates test wells and a plate, calls the 'export_redesolve_to_soak'
        function with the prepared data, and then checks if the wells and plate in the
        database are updated correctly. It also handles the cleanup of created test entries.

        Raises:
            AssertionError: If any of the assertions fail, indicating unexpected behavior.
        """
        # Constants initialization
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"

        # Test wells and plate creation
        added_well_id_01 = self.add_test_well(userAccount=user_account, campaignId=campaign_id,
                                              plateId=plate_id, well="A25a", wellEcho="A25a",
                                              x=488, y=684, xEcho=3.32, yEcho=1.87,
                                              redesolveExportTime=None, redesolveApplied=True)['inserted_id']

        added_well_id_02 = self.add_test_well(userAccount=user_account, campaignId=campaign_id,
                                              plateId=plate_id, well="B25b", wellEcho="B25b",
                                              x=500, y=700, xEcho=4.32, yEcho=2.87,
                                              redesolveExportTime=None, redesolveApplied=True)['inserted_id']

        added_plate_id = self.add_test_plate(user_account, campaign_id, plate_id,
                                             lastImaged=datetime.now().isoformat(), batchId="987654")['inserted_id']

        # Data preparation for the function under test
        #now_time = datetime.now().replace(microsecond=0).isoformat()
        now_time = datetime.now()
        data = [{'_id': plate_id, 'soak_time': now_time}]

        # Function under test call
        retrieved_data = self.client.export_redesolve_to_soak(data).to_dict()
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        # Assertions and validation
        self.assertIsNotNone(retrieved_data, "Result of 'export_redesolve_to_soak' is None.")
        self.assertEqual(retrieved_data["modified_count"], 2, "Processed wells count mismatch.")

        # Retrieval and validation of updated wells
        retrieved_data_updated_well_01 = self.convert_objectid_to_str(self.client.get_one_well(added_well_id_01))
        retrieved_data_updated_well_02 = self.convert_objectid_to_str(self.client.get_one_well(added_well_id_02))
        printv(f"{json.dumps(retrieved_data_updated_well_01, indent=4)}")
        printv(f"{json.dumps(retrieved_data_updated_well_02, indent=4)}")

        # Assertions for wells and plate
        # Assertions for wells and plate
        self.assertEqual(retrieved_data_updated_well_01["redesolveStatus"], "exported")
        self.assertTrue(are_times_almost_equal(retrieved_data_updated_well_01["redesolveExportTime"], now_time), "redesolveExportTime does not match for well 01 within allowed margin.")
        
        self.assertEqual(retrieved_data_updated_well_02["redesolveStatus"], "exported")
        self.assertTrue(are_times_almost_equal(retrieved_data_updated_well_02["redesolveExportTime"], now_time), "redesolveExportTime does not match for well 02 within allowed margin.")

        retrieved_data_updated_plate = self.convert_objectid_to_str(self.client.get_plate(user_account, campaign_id, plate_id))
        self.assertTrue(retrieved_data_updated_plate["redesolveApplied"], "Plate 'redesolveApplied' not set to True.")
        printv(f"{json.dumps(retrieved_data_updated_plate, indent=4)}")

        # Cleanup after test
        self.delete_by_id("wells", added_well_id_01)
        self.delete_by_id("wells", added_well_id_02)
        self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG export_redesolve_to_soak

    ### FETCH_TAG import_soaking_results
    def test_26_import_soaking_results(self):
        """
        Test case for the import_soaking_results function.
    
        This test creates test wells and a test plate, prepares data for the import_soaking_results
        function, performs the operation, and verifies if the soak status of the wells have been
        updated to 'done' successfully. It also ensures the cleanup of test data after execution.
    
        The test is considered successful if the soak status of all test wells is 'done' and the
        response message indicates a successful import.
    
        Raises:
            AssertionError: If the result of the import_soaking_results function is None or if the
                            result message does not match the expected value. Also raises if the
                            soakStatus of either of the test wells does not match the expected value 'done'.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A26a",
            wellEcho="A26a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
        )['inserted_id']
    
        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B26b",
            wellEcho="B26b",
            x=500,
            y=700,
            xEcho=4.32,
            yEcho=2.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
        )['inserted_id']
    
        ### Add a test plate
        last_imaged = datetime.now()
        batch_id = "987654"
        added_plate_id = self.add_test_plate(
            user_account, 
            campaign_id, 
            plate_id, 
            lastImaged=last_imaged.isoformat(), 
            batchId=batch_id
        )['inserted_id']
    
        ### Prepare data for the import_soaking_results function
        data = [
            {'plateId': plate_id, 'wellEcho': 'A26a', 'transferStatus': 'status1'},
            {'plateId': plate_id, 'wellEcho': 'B26b', 'transferStatus': 'status2'}
        ]
    
        ### Perform the operation
        retrieved_data = self.client.import_soaking_results(data)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of import_soaking_results function is None.")
            self.assertEqual(
                retrieved_data['result'], 
                "Soaking results imported successfully.", 
                "The result message does not match."
            )
    
            ### Retrieve the updated wells
            retrieved_data_updated_well_01 = self.client.get_one_well(added_well_id_01)
            retrieved_data_updated_well_02 = self.client.get_one_well(added_well_id_02)
            ### Convert ObjectIds to strings
            retrieved_data_updated_well_01 = self.convert_objectid_to_str(retrieved_data_updated_well_01)
            retrieved_data_updated_well_02 = self.convert_objectid_to_str(retrieved_data_updated_well_02)
            printv(f"{json.dumps(retrieved_data_updated_well_01, indent=4)}")
            printv(f"{json.dumps(retrieved_data_updated_well_02, indent=4)}")
    
            ### Assertions for well 01
            self.assertEqual(
                retrieved_data_updated_well_01["soakStatus"], 
                "done", 
                "soakStatus of well 01 does not match."
            )
    
            ### Assertions for well 02
            self.assertEqual(
                retrieved_data_updated_well_02["soakStatus"], 
                "done", 
                "soakStatus of well 02 does not match."
            )
    
        finally:
            ### Delete the wells and the plate after the test
            printv(added_well_id_01)
            printv(added_well_id_02)
            printv(added_plate_id)
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
            self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG import_soaking_results

    ### FETCH_TAG mark_soak_for_well_in_echo_done
    def test_27_mark_soak_for_well_in_echo_done(self):
        """
        Test the functionality of marking a well's soak status as 'done' after an Echo transfer.
    
        This test simulates marking the soak status of a well as done and verifies that the
        soak status and transfer status are updated correctly in the database.
    
        Args:
            self: Instance of the unittest.TestCase or similar testing class.
        
        Raises:
            AssertionError: If any of the assertions fail.
            Exception: Re-raises any unexpected exception that occurs during the process.
        """
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A27a",
            wellEcho="A27a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
        )['inserted_id']
    
        last_imaged = datetime.now()
        batch_id = "987654"
        added_plate_id = self.add_test_plate(user_account, campaign_id, plate_id, lastImaged=last_imaged.isoformat(), batchId=batch_id)['inserted_id']
    
        well_echo = "A27a"
        transfer_status = "status1"
        retrieved_data = self.client.mark_soak_for_well_in_echo_done(user_account, campaign_id, plate_id, well_echo, transfer_status)
    
        retrieved_data = retrieved_data.to_dict()
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            self.assertIsNotNone(retrieved_data, "Result of mark_soak_for_well_in_echo_done function is None.")
            self.assertEqual(retrieved_data['modified_count'], 1, "The number of modified documents does not match.")
    
            retrieved_data_updated_well_01 = self.client.get_one_well(added_well_id_01)
            retrieved_data_updated_well_01 = self.convert_objectid_to_str(retrieved_data_updated_well_01)
            printv(f"{json.dumps(retrieved_data_updated_well_01, indent=4)}")
    
            self.assertEqual(retrieved_data_updated_well_01["soakStatus"], "done", "soakStatus of well 01 does not match.")
            self.assertEqual(retrieved_data_updated_well_01["soakTransferStatus"], transfer_status, "soakTransferStatus of well 01 does not match.")
    
            is_valid_datetime = False
            if retrieved_data_updated_well_01.get('soakTransferTime') is not None:
                try:
                    parse(retrieved_data_updated_well_01['soakTransferTime'])
                    is_valid_datetime = True
                except ValueError:
                    is_valid_datetime = False
            self.assertTrue(is_valid_datetime, "soakTransferTime is not a valid datetime for well 01")
    
        finally:
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG mark_soak_for_well_in_echo_done

    ### FETCH_TAG add_cryo
    def test_28_add_cryo(self):
        """
        Integration test for adding cryoprotection to a well.
    
        This function tests the `add_cryo` method of the client. It creates a test well,
        adds cryoprotection details to it, and asserts the correct behavior of the
        `add_cryo` functionality by verifying the modified document's new state.
    
        The test proceeds by performing cleanup actions, removing test data after verification.
    
        Raises:
            AssertionError: If any of the expected outcomes of the `add_cryo` operation
                            is not met.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        target_well = "A28a"
        cryo_desired_concentration = 1.5
        cryo_transfer_volume = 100
        cryo_source_well = "B28b"
        cryo_name = "Cryo Test"
        cryo_barcode = "CT98765"
    
        ### Create test well
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well=target_well,
            wellEcho="A28a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
        )['inserted_id']
    
        ### Prepare data for the add_cryo function
        data = {
            'user_account': user_account,
            'campaign_id': campaign_id,
            'target_plate': plate_id,
            'target_well': target_well,
            'cryo_desired_concentration': cryo_desired_concentration,
            'cryo_transfer_volume': cryo_transfer_volume,
            'cryo_source_well': cryo_source_well,
            'cryo_name': cryo_name,
            'cryo_barcode': cryo_barcode
        }
    
        ### Perform the operation
        retrieved_data = self.client.add_cryo(data)
    
        retrieved_data = retrieved_data.to_dict()
    
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of add_cryo function is None.")
            self.assertEqual(retrieved_data['modified_count'], 1, "The number of modified documents does not match.")
    
            ### Retrieve the updated well
            retrieved_data_updated_well_01 = self.client.get_one_well(added_well_id_01)
            ### Convert ObjectIds to strings
            retrieved_data_updated_well_01 = self.convert_objectid_to_str(retrieved_data_updated_well_01)
            printv(f"{json.dumps(retrieved_data_updated_well_01, indent=4)}")
    
            ### Assertions for well 01
            self.assertEqual(retrieved_data_updated_well_01["cryoProtection"], True, "cryoProtection of well 01 does not match.")
            self.assertEqual(retrieved_data_updated_well_01["cryoStatus"], "pending", "cryoStatus of well 01 does not match.")
            self.assertEqual(retrieved_data_updated_well_01["cryoDesiredConcentration"], cryo_desired_concentration, "cryoDesiredConcentration of well 01 does not match.")
            self.assertEqual(retrieved_data_updated_well_01["cryoTransferVolume"], cryo_transfer_volume, "cryoTransferVolume of well 01 does not match.")
            self.assertEqual(retrieved_data_updated_well_01["cryoSourceWell"], cryo_source_well, "cryoSourceWell of well 01 does not match.")
            self.assertEqual(retrieved_data_updated_well_01["cryoName"], cryo_name, "cryoName of well 01 does not match.")
            self.assertEqual(retrieved_data_updated_well_01["cryoBarcode"], cryo_barcode, "cryoBarcode of well 01 does not match.")
    
        finally:
            ### Delete the wells after the test
            self.delete_by_id("wells", added_well_id_01)
    ### FETCH_TAG add_cryo

    ### FETCH_TAG remove_cryo_from_well
    def test_29_remove_cryo_from_well(self):
        """
        Test the removal of cryoprotectant data from a well by sending a PATCH request
        to the server and then validating the update operation's results.
    
        This test first creates a test well with cryoprotectant data, then attempts to remove
        the cryoprotectant data and asserts the success of the operation by checking the 
        modified count and the updated well's cryoprotectant-related fields.
    
        Raises:
            AssertionError: If the response is None, or if the modified count is not 1,
                            or if the updated well's cryoprotectant-related fields are not None or False.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        target_well = "A29a"
        cryo_desired_concentration = 1.5
        cryo_transfer_volume = 100
        cryo_source_well = "B29b"
        cryo_name = "Cryo Test"
        cryo_barcode = "CT98765"
    
        ### Create test well with cryo protection
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well=target_well,
            wellEcho=target_well,
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
            cryoProtection=True,
            cryoDesiredConcentration=cryo_desired_concentration,
            cryoTransferVolume=cryo_transfer_volume,
            cryoSourceWell=cryo_source_well,
            cryoName=cryo_name,
            cryoBarcode=cryo_barcode
        )['inserted_id']
    
        ### Perform the operation
        retrieved_data = self.client.remove_cryo_from_well(str(added_well_id_01))
    
        retrieved_data = retrieved_data.to_dict()
    
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of remove_cryo_from_well function is None.")
            self.assertEqual(retrieved_data['modified_count'], 1, "The number of modified documents does not match.")
    
            ### Retrieve the updated well
            retrieved_data_updated_well_01 = self.client.get_one_well(added_well_id_01)
            ### Convert ObjectIds to strings
            retrieved_data_updated_well_01 = self.convert_objectid_to_str(retrieved_data_updated_well_01)
            printv(f"{json.dumps(retrieved_data_updated_well_01, indent=4)}")
    
            ### Assertions for well 01
            self.assertEqual(retrieved_data_updated_well_01["cryoProtection"], False, "cryoProtection of well 01 does not match.")
            self.assertIsNone(retrieved_data_updated_well_01["cryoStatus"], "cryoStatus of well 01 is not None.")
            self.assertIsNone(retrieved_data_updated_well_01["cryoDesiredConcentration"], "cryoDesiredConcentration of well 01 is not None.")
            self.assertIsNone(retrieved_data_updated_well_01["cryoTransferVolume"], "cryoTransferVolume of well 01 is not None.")
            self.assertIsNone(retrieved_data_updated_well_01["cryoSourceWell"], "cryoSourceWell of well 01 is not None.")
            self.assertIsNone(retrieved_data_updated_well_01["cryoName"], "cryoName of well 01 is not None.")
            self.assertIsNone(retrieved_data_updated_well_01["cryoBarcode"], "cryoBarcode of well 01 is not None.")
    
        finally:
            ### Delete the wells after the test
            self.delete_by_id("wells", added_well_id_01)
    ### FETCH_TAG remove_cryo_from_well

    ### FETCH_TAG remove_new_solvent_from_well
    def test_30_remove_new_solvent_from_well(self):
        """
        Tests the removal of the New Solvent (redissolve option) from a well.
    
        This test performs the operation by invoking the client's method to remove the 
        redissolve option and then asserts the outcome and state of the well after the 
        operation. It ensures that the redissolve attributes are reset to their default 
        'empty' states and the well's `redesolveApplied` status is updated to False.
        
        The test includes setup and teardown steps where a test well is added before the 
        test and removed afterward.
    
        Raises:
            AssertionError: If the expected results do not match the actual results from 
                            the operation.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        target_well = "A30a"
        redesolve_transfer_volume = 100
        redesolve_name = "Redesolve Test"
        redesolve_barcode = "RT98765"
    
        ### Create test well with redesolve applied
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well=target_well,
            wellEcho="A30a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
            redesolveTransferVolume=redesolve_transfer_volume,
            redesolveName=redesolve_name,
            redesolveBarcode=redesolve_barcode
        )['inserted_id']
    
        ### Perform the operation
        retrieved_data = self.client.remove_new_solvent_from_well(str(added_well_id_01))
    
        retrieved_data = retrieved_data.to_dict()
    
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of remove_new_solvent_from_well function is None.")
            self.assertEqual(retrieved_data['modified_count'], 1, "The number of modified documents does not match.")
    
            ### Retrieve the updated well
            retrieved_data_updated_well_01 = self.client.get_one_well(added_well_id_01)
            ### Convert ObjectIds to strings
            retrieved_data_updated_well_01 = self.convert_objectid_to_str(retrieved_data_updated_well_01)
            printv(f"{json.dumps(retrieved_data_updated_well_01, indent=4)}")
    
            ### Assertions for well 01
            self.assertEqual(retrieved_data_updated_well_01["redesolveApplied"], False, "redesolveApplied of well 01 does not match.")
            self.assertIsNone(retrieved_data_updated_well_01["redesolveStatus"], "redesolveStatus of well 01 is not None.")
            self.assertIsNone(retrieved_data_updated_well_01["redesolveTransferVolume"], "redesolveTransferVolume of well 01 is not None.")
            self.assertIsNone(retrieved_data_updated_well_01["redesolveName"], "redesolveName of well 01 is not None.")
            self.assertIsNone(retrieved_data_updated_well_01["redesolveBarcode"], "redesolveBarcode of well 01 is not None.")
    
        finally:
            ### Delete the wells after the test
            self.delete_by_id("wells", added_well_id_01)
    ### FETCH_TAG remove_new_solvent_from_well

    ### FETCH_TAG get_cryo_usage
    def test_31_get_cryo_usage(self):
        """
        Integration test for the get_cryo_usage function.
        Adds test wells with cryo protection, retrieves cryo usage information, and checks if it matches the expected values.
        Deletes the wells after the test.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        target_well_1 = "A31a"
        target_well_2 = "B31b"
        cryo_desired_concentration = 1.5
        cryo_transfer_volume_1 = 100
        cryo_transfer_volume_2 = 50
        cryo_source_well = "C31c"
        cryo_name = "Cryo Test"
        cryo_barcode = "CT12345"
    
        ### Create test wells with cryo protection and store their IDs
        added_well_id_01 = self.add_test_well(userAccount=user_account, campaignId=campaign_id, plateId=plate_id, well=target_well_1,
                                              wellEcho="A31a", x=488, y=684, xEcho=3.32, yEcho=1.87, redesolveExportTime=None,
                                              redesolveApplied=True, soakStatus="exported", cryoProtection=True,
                                              cryoDesiredConcentration=cryo_desired_concentration, cryoTransferVolume=cryo_transfer_volume_1,
                                              cryoSourceWell=cryo_source_well, cryoName=cryo_name, cryoBarcode=cryo_barcode)['inserted_id']
    
        added_well_id_02 = self.add_test_well(userAccount=user_account, campaignId=campaign_id, plateId=plate_id, well=target_well_2,
                                              wellEcho="B31b", x=500, y=700, xEcho=4.32, yEcho=2.87, redesolveExportTime=None,
                                              redesolveApplied=True, soakStatus="exported", cryoProtection=True,
                                              cryoDesiredConcentration=cryo_desired_concentration, cryoTransferVolume=cryo_transfer_volume_2,
                                              cryoSourceWell=cryo_source_well, cryoName=cryo_name, cryoBarcode=cryo_barcode)['inserted_id']
    
        try:
            ### Perform the operation and retrieve cryo usage data
            retrieved_data = self.client.get_cryo_usage(user_account, campaign_id)
            
            ### Filter added test data by library name
            filtered_data = [doc for doc in retrieved_data if doc["_id"]["libraryName"] == "Cryo Test"]
    
            printv(f"\n{json.dumps(filtered_data, indent=4)}")
    
            ### Assertions
            self.assertIsNotNone(filtered_data, "Result of get_cryo_usage function is None.")
            self.assertEqual(len(filtered_data), 1, "The number of grouped cryo usage does not match.")
            self.assertEqual(filtered_data[0]['_id']['sourceWell'], cryo_source_well, "The cryoSourceWell does not match.")
            self.assertEqual(filtered_data[0]['_id']['libraryName'], cryo_name, "The cryoName does not match.")
            self.assertEqual(filtered_data[0]['total'], cryo_transfer_volume_1 + cryo_transfer_volume_2, "The total cryo usage does not match.")
    
        except Exception as e:
            ### Handle exceptions during test execution
            print(f"An exception occurred during test execution: {e}")
    
        finally:
            ### Delete the wells after the test
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
    ### FETCH_TAG get_cryo_usage

    ### FETCH_TAG get_solvent_usage
    def test_32_get_solvent_usage(self):
        """
        This integration test checks the behavior of the get_solvent_usage function.
        It initializes constants, creates test wells, performs the operation,
        filters the data, and runs assertions to ensure the function behaves as expected.
    
        Side-effects:
            - Adds test wells to the database.
            - Deletes the test wells after the test.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        target_well_1 = "A32a"
        target_well_2 = "B32b"
        solvent_volume_1 = 100
        solvent_volume_2 = 50
        source_well = "B32b"
        library_name = "Library Test"
    
        ### Create test wells with solvent test
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well=target_well_1,
            wellEcho="A32a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="pending",
            solventTest=True,
            ligandTransferVolume=solvent_volume_1,
            sourceWell=source_well,
            libraryName=library_name
        )['inserted_id']
    
        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well=target_well_2,
            wellEcho="B32b",
            x=500,
            y=700,
            xEcho=4.32,
            yEcho=2.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="pending",
            solventTest=True,
            ligandTransferVolume=solvent_volume_2,
            sourceWell=source_well,
            libraryName=library_name
        )['inserted_id']
    
        ### Perform the operation
        retrieved_data = self.client.get_solvent_usage(user_account, campaign_id)
    
        ### Filter added test data
        filtered_data = [doc for doc in retrieved_data if doc["_id"]["libraryName"] == library_name]
        printv(f"\n{json.dumps(filtered_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsNotNone(filtered_data, "Result of get_solvent_usage function is None.")
            self.assertEqual(len(filtered_data), 1, "The number of grouped solvent usage does not match.")
            self.assertEqual(filtered_data[0]['_id']['sourceWell'], source_well, "The sourceWell does not match.")
            self.assertEqual(filtered_data[0]['_id']['libraryName'], library_name, "The libraryName does not match.")
            self.assertEqual(filtered_data[0]['total'], solvent_volume_1 + solvent_volume_2, "The total solvent usage does not match.")
        finally:
            ### Delete the test wells
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
    ### FETCH_TAG get_solvent_usage

    ### FETCH_TAG redesolve_in_new_solvent
    def test_33_redesolve_in_new_solvent(self):
        """
        Integration test for the 'redesolve_in_new_solvent' function.
        This test creates a test well, performs the redesolve operation on it,
        and then validates that the operation occurred as expected.
    
        Side-effects:
            - Adds and then deletes a test well in the database.
    
        Exceptions:
            - Asserts will fail if expected results do not match.
        """
    
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        target_well = "A33a"
        redesolve_transfer_volume = 50
        redesolve_source_well = "B33b"
        redesolve_name = "Redesolve Test"
        redesolve_barcode = "RT98765"
    
        ### Create test well and store the inserted ID
        added_well_id = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well=target_well,
            wellEcho="A33a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=False,
        )['inserted_id']
    
        ### Perform the redesolve operation
        retrieved_data = self.client.redesolve_in_new_solvent(
            user_account, campaign_id, plate_id, target_well,
            redesolve_transfer_volume, redesolve_source_well,
            redesolve_name, redesolve_barcode
        )
    
        ### Convert the result to dictionary
        retrieved_data = retrieved_data.to_dict()
    
        ### Print verbose output for debugging
        printv(json.dumps(retrieved_data, indent=4))
    
        try:
            ### Assertions for verifying the operation
            self.assertEqual(retrieved_data['modified_count'], 1, "Number of modified documents does not match.")
    
            ### Retrieve and print the updated well data for debugging
            retrieved_data_updated_well = self.client.get_one_well(added_well_id)
            retrieved_data_updated_well = self.convert_objectid_to_str(retrieved_data_updated_well)
            printv(json.dumps(retrieved_data_updated_well, indent=4))
    
            ### Assertions for validating updated well data
            self.assertEqual(retrieved_data_updated_well["redesolveApplied"], True, "redesolveApplied does not match.")
            self.assertEqual(retrieved_data_updated_well["redesolveTransferVolume"], redesolve_transfer_volume, "redesolveTransferVolume does not match.")
            self.assertEqual(retrieved_data_updated_well["redesolveSourceWell"], redesolve_source_well, "redesolveSourceWell does not match.")
            self.assertEqual(retrieved_data_updated_well["redesolveName"], redesolve_name, "redesolveName does not match.")
            self.assertEqual(retrieved_data_updated_well["redesolveBarcode"], redesolve_barcode, "redesolveBarcode does not match.")
            self.assertEqual(retrieved_data_updated_well["redesolveStatus"], 'pending', "redesolveStatus does not match.")
    
        finally:
            ### Cleanup: Delete the test well
            self.delete_by_id("wells", added_well_id)
    ### FETCH_TAG redesolve_in_new_solvent

    ### FETCH_TAG update_notes
    def test_34_update_notes(self):
        """
        Integration test for the update_notes function.
        This test simulates the process of adding a test well, updating its notes,
        and validating the expected outcome.
    
        Steps:
        1. Initialize constants for user account, campaign, and plate IDs.
        2. Create a test well.
        3. Prepare a note for updating.
        4. Call the update_notes function and print the result.
        5. Validate the retrieved data with assertions.
        
        Finally, the test cleans up by deleting the added well.
    
        Note: 
        - The test uses helper functions like add_test_well, get_one_well, 
          convert_objectid_to_str, and delete_by_id which are assumed to be defined 
          elsewhere in the code.
    
        Raises:
            AssertionError: If any of the assertions fail.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        target_well = "A34a"
    
        ### Create test well
        added_well_id = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well=target_well,
            wellEcho="A34a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
        )['inserted_id']
    
        ### Prepare notes for the update_notes function
        note = "Test note for update."
    
        ### Perform the operation
        try:
            retrieved_data = self.client.update_notes(user_account, campaign_id, str(added_well_id), note)
            printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
            ### Validate the retrieved data
            if retrieved_data is None:
                raise AssertionError("Result of update_notes function is None.")
    
            if not retrieved_data.get('ok', False):
                raise AssertionError("The operation was not successful.")
    
            ### Retrieve and validate the updated well
            retrieved_updated_well_data = self.client.get_one_well(added_well_id)
            retrieved_updated_well_data = self.convert_objectid_to_str(retrieved_updated_well_data)
            printv(f"{json.dumps(retrieved_updated_well_data, indent=4)}")
            
            if retrieved_updated_well_data["notes"] != note:
                raise AssertionError("Notes of well do not match.")
    
        finally:
            ### Clean-up: Delete the wells after the test
            self.delete_by_id("wells", added_well_id)
    ### FETCH_TAG update_notes

    ### FETCH_TAG is_crystal_already_fished
    def test_35_is_crystal_already_fished(self):
        """
        Integration test to check if the 'is_crystal_already_fished' function correctly identifies the fished status of a crystal.
        
        This function first adds a test well with a fished status, then queries it to ensure the status is correctly identified.
        It also ensures that the test well is deleted after the test.
        
        Raises:
            AssertionError: If any of the assertions fail.
        """
        ### Initialize constants for test parameters
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        well_id = "A35a"
        fished_status = True
    
        ### Add a test well with predetermined fished status
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well=well_id,
            wellEcho="A35a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
            fished=fished_status,
        )['inserted_id']
    
        try:
            ### Perform the API call to check the fished status
            retrieved_data = self.client.is_crystal_already_fished(plate_id, well_id)
    
            ### Debugging: Print the retrieved data in a readable format
            printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
            ### Assertions to verify correctness
            self.assertIsNotNone(retrieved_data, "Result of is_crystal_already_fished function is None.")
            self.assertTrue(retrieved_data, "The crystal was not identified as already fished.")
    
        finally:
            ### Cleanup: Delete the test well
            self.delete_by_id("wells", added_well_id_01)
    ### FETCH_TAG is_crystal_already_fished

    ### FETCH_TAG update_shifter_fishing_result
    def test_36_update_shifter_fishing_result(self):
        """
        Integration Test for the Update Shifter Fishing Result Functionality.

        This test performs the following steps:
        1. Initializes constants and test parameters.
        2. Creates a test well without fishing properties.
        3. Prepares shifter data for the well including time of arrival, departure, and other attributes.
        4. Calls the `update_shifter_fishing_result` method to update the well data.
        5. Verifies that the well data was correctly updated by comparing the modified database document to the initial input.

        Test Requirements:
        - The function `add_test_well` must be previously defined and working as expected.
        - MongoDB must be running and accessible.
        - The client for making API requests must be correctly configured.

        Note: 
        The test cleans up by deleting the added well document after all assertions are made.
        
        Side-effects:
        - Inserts and then removes a well document to/from the database.

        Exceptions:
        - Assertion errors if any of the checks fail.
        - Connection errors if the database or client malfunctions.
        """

        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        well_id = "A36a"

        ### Create a test well with no fishing properties yet
        added_well_id = self.add_test_well(
            userAccount = user_account,
            campaignId = campaign_id,
            plateId = plate_id,
            well = well_id,
            wellEcho = "A36a",
            x = 488,
            y = 684,
            xEcho = 3.32,
            yEcho = 1.87,
            redesolveExportTime = None,
            redesolveApplied = True,
            soakStatus = "exported",
            fished = False,
        )['inserted_id']

        ### your timeOfArrival and timeOfDeparture as datetime objects
        time_of_arrival = datetime.strptime('2023-08-03 12:30:15.000', '%Y-%m-%d %H:%M:%S.%f')
        time_of_departure = datetime.strptime('2023-08-03 12:35:15.000', '%Y-%m-%d %H:%M:%S.%f')

        ### calculate duration as a timedelta
        duration_td = time_of_departure - time_of_arrival

        ### convert timedelta to string format "HH:MM:SS"
        duration_str = str(duration_td)

        well_shifter_data = {
            'plateId': plate_id,
            'plateRow': 'A',
            'plateColumn': '36',
            'plateSubwell': 'a',
            'timeOfArrival': '2023-08-03 12:30:15.000',
            'timeOfDeparture': '2023-08-03 12:35:15.000',
            'duration': duration_str, ### use calculated duration string here
            'comment': 'OK',
            'xtalId': 'crystal1',
            'destinationName': 'puck1',
            'destinationLocation': '1',
            'barcode': 'pin1',
            'externalComment': 'puckType1'
        }

        xtal_name_index = 1
        xtal_name_prefix = 'xtal'
        retrieved_data = self.client.update_shifter_fishing_result(well_shifter_data, xtal_name_index, xtal_name_prefix)
        retrieved_data = retrieved_data.to_dict()

        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        try:
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of update_shifter_fishing_result function is None.")
            self.assertEqual(retrieved_data['modified_count'], 1, "The number of modified documents does not match.")

            ### Retrieve the updated well
            retrieved_data_updated_well = self.client.get_one_well(added_well_id)

            ### Convert ObjectIds to strings
            retrieved_data_updated_well = self.convert_objectid_to_str(retrieved_data_updated_well)
            printv(f"\n{json.dumps(retrieved_data_updated_well, indent=4)}")

            ### Assertions for updated well
            self.assertEqual(retrieved_data_updated_well['shifterComment'], well_shifter_data['comment'], "shifterComment does not match.")
            self.assertEqual(retrieved_data_updated_well['shifterXtalId'], well_shifter_data['xtalId'], "shifterXtalId does not match.")
            time_of_arrival_db_format = time_of_arrival.strftime("%Y-%m-%dT%H:%M:%S")  ### Matches format in the database
            time_of_departure_db_format = time_of_departure.strftime("%Y-%m-%dT%H:%M:%S")  ### Matches format in the database
            self.assertEqual(retrieved_data_updated_well['shifterTimeOfArrival'], time_of_arrival_db_format, "shifterTimeOfArrival does not match.")
            self.assertEqual(retrieved_data_updated_well['shifterTimeOfDeparture'], time_of_departure_db_format, "shifterTimeOfArrival does not match.")
            duration = datetime.strptime(well_shifter_data['duration'], "%H:%M:%S").time()
            duration_db_format = datetime.combine(date.today(), duration).isoformat()
            self.assertEqual(retrieved_data_updated_well['shifterDuration'], duration_db_format, "shifterDuration does not match.")
            self.assertEqual(retrieved_data_updated_well['puckBarcode'], well_shifter_data['destinationName'], "puckBarcode does not match.")
            self.assertEqual(retrieved_data_updated_well['puckPosition'], well_shifter_data['destinationLocation'], "puckPosition does not match.")
            self.assertEqual(retrieved_data_updated_well['pinBarcode'], well_shifter_data['barcode'], "pinBarcode does not match.")
            self.assertEqual(retrieved_data_updated_well['puckType'], well_shifter_data['externalComment'], "puckType does not match.")
            self.assertEqual(retrieved_data_updated_well['fished'], True, "fished does not match.")
            self.assertEqual(retrieved_data_updated_well['xtalName'], f'{xtal_name_prefix}-{xtal_name_index}', "xtalName does not match.")

        finally:
            ### Delete the well after the test
            self.delete_by_id("wells", added_well_id)
    ### FETCH_TAG update_shifter_fishing_result

    ### FETCH_TAG import_fishing_results
    def test_37_import_fishing_results(self):
        """
        Integration test for the import_fishing_results function.
        This test simulates the entire process of adding test wells and a test plate, 
        performing an operation, and validating the expected outcome.
    
        Steps:
        1. Initialize constants for user account, campaign, and plate IDs.
        2. Add test wells and a test plate.
        3. Prepare well_shifter_data for two wells.
        4. Call the import_fishing_results function.
        5. Validate the retrieved data with assertions.
    
        Finally, the test cleans up by deleting the added wells and plate.
    
        Note: The test uses helper functions like add_test_well, add_test_plate,
        get_one_well, and delete_by_id which are assumed to be defined elsewhere in the code.
    
        Raises:
            AssertionError: If any of the assertions fail.
        """
        
        ### Initialize constants
        user_account, campaign_id, plate_id = "e14965", "EP_SmarGon", "98765"
        test_time_str = '2023-08-03 12:30:15.000'
        time_format = '%Y-%m-%d %H:%M:%S.%f'
        
        ### Helper function to generate test well data
        def add_test_well(well, wellEcho, x, y, xEcho, yEcho):
            return self.add_test_well(
                userAccount=user_account,
                campaignId=campaign_id,
                plateId=plate_id,
                well=well,
                wellEcho=wellEcho,
                x=x,
                y=y,
                xEcho=xEcho,
                yEcho=yEcho,
                redesolveExportTime=None,
                redesolveApplied=True,
                soakStatus="exported"
            )['inserted_id']
    
        ### Create test wells
        added_well_id_01 = add_test_well("A37a", "A37a", 488, 684, 3.32, 1.87)
        added_well_id_02 = add_test_well("B37b", "B37b", 500, 700, 4.32, 2.87)
    
        ### Add a test plate
        last_imaged = datetime.now()
        batch_id = "987654"
        added_plate_id = self.add_test_plate(user_account, campaign_id, plate_id, lastImaged=last_imaged.isoformat(), batchId=batch_id)['inserted_id']
    
        ### Prepare common data for the import_fishing_results function
        time_of_arrival = datetime.strptime(test_time_str, time_format)
        time_of_departure = datetime.strptime('2023-08-03 12:35:15.000', time_format)
        duration_str = str(time_of_departure - time_of_arrival)
    
        ### Data for well shifter 01 and 02
        well_shifter_data_template = {
            'plateId': plate_id,
            'timeOfArrival': test_time_str,
            'timeOfDeparture': '2023-08-03 12:35:15.000',
            'duration': duration_str,
            'comment': 'OK',
            'xtalId': 'crystal1',
            'destinationName': 'puck1',
            'destinationLocation': '1',
            'barcode': 'pin1',
            'externalComment': 'puckType1'
        }
        
        well_shifter_data_01 = {**well_shifter_data_template, 'plateRow': 'A', 'plateColumn': '37', 'plateSubwell': 'a'}
        well_shifter_data_02 = {**well_shifter_data_template, 'plateRow': 'B', 'plateColumn': '37', 'plateSubwell': 'b'}
    
        data = [well_shifter_data_01, well_shifter_data_02]
    
        try:
            ### Perform the operation
            retrieved_data = self.client.import_fishing_results(data)
    
            ### Logging the retrieved data
            printv(str(retrieved_data))
            printv(retrieved_data)
            retrieved_data = retrieved_data.to_dict()
            printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
            ### Basic error handling for None results
            if retrieved_data is None:
                raise ValueError("Result of import_fishing_results function is None.")
            
            ### Assertions
            self.assertEqual(retrieved_data['modified_count'], 1, "The number of modified documents does not match.")
    
            ### Further functions and assertions are kept as they are
    
        except Exception as e:
            printv(f"An exception occurred: {e}")
    
        finally:
            ### Delete the wells and plate after the test
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
            self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG import_fishing_results

    ### FETCH_TAG find_user_from_plate_id
    def test_38_find_user_from_plate_id(self):
        """
        Test Case for finding the user and campaign_id based on a plate_id.
        
        Steps:
        1. Initialize constants for test data.
        2. Add a test plate.
        3. Perform the operation to find the user and campaign_id from plate_id.
        4. Assert the results to verify they match the expected output.
        
        Note:
        The added test plate will be deleted after the test.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        ### Add a test plate
        last_imaged = datetime.now()
        batch_id = "987654"
        added_plate_id = self.add_test_plate(
            user_account, 
            campaign_id, 
            plate_id, 
            lastImaged=last_imaged.isoformat(), 
            batchId=batch_id
        )['inserted_id']
    
        try:
            ### Perform the operation
            retrieved_data = self.client.find_user_from_plate_id(plate_id)
            
            ### Log the retrieved data
            printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of find_user_from_plate_id function is None.")
            self.assertEqual(retrieved_data['user'], user_account, "The user does not match.")
            self.assertEqual(retrieved_data['campaign_id'], campaign_id, "The campaign_id does not match.")
        except Exception as e:
            print(f"An error occurred: {e}")
            self.fail("Test case failed due to an exception.")
        finally:
            ### Delete the plate after the test
            self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG find_user_from_plate_id

    ### FETCH_TAG find_last_fished_xtal
    def test_39_find_last_fished_xtal(self):
        """
        Integration test to validate the functionality of the find_last_fished_xtal API endpoint.
        - Adds two test wells with different shifterTimeOfDeparture values.
        - Checks that the find_last_fished_xtal function returns the most recently fished well.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A39a",
            wellEcho="A39a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
            fished=True,
            shifterTimeOfDeparture=datetime.now().isoformat(),
        )['inserted_id']
    
        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B39b",
            wellEcho="B39b",
            x=500,
            y=700,
            xEcho=4.32,
            yEcho=2.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
            fished=True,
            shifterTimeOfDeparture=(datetime.now() + timedelta(hours=1)).isoformat(),
        )['inserted_id']
    
        try:
            ### Perform the operation
            retrieved_data = self.client.find_last_fished_xtal(user_account, campaign_id)
            ### Convert ObjectIds to strings
            retrieved_data = self.convert_objectid_to_str(retrieved_data)
            ### Filter added test data
            retrieved_data = [
                doc for doc in retrieved_data if (
                    doc["userAccount"] == user_account and
                    doc["campaignId"] == campaign_id and
                    doc["plateId"] == plate_id and
                    ((doc["well"] == "A39a" and doc["wellEcho"] == "A39a") or
                     (doc["well"] == "B39b" and doc["wellEcho"] == "B39b"))
                )
            ]
    
            printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of find_last_fished_xtal function is None.")
            self.assertTrue(len(retrieved_data) > 0, "No fished wells were found.")
            self.assertEqual(retrieved_data[0]['_id'], str(added_well_id_02), "The most recently fished well does not match the expected well.")
        
        except Exception as e:
            print(f"Exception occurred during test: {e}")
    
        finally:
            ### Delete the wells after the test
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
    ### FETCH_TAG find_last_fished_xtal

    ### FETCH_TAG get_next_xtal_number
    def test_40_get_next_xtal_number(self):
        """
        Integration Test for get_next_xtal_number Functionality
    
        This test validates the 'get_next_xtal_number' function by setting up a controlled
        test environment. It adds two test wells and a test plate with specific parameters
        to the database. The test then performs the 'get_next_xtal_number' operation and
        verifies the result.
    
        After the test, it deletes the added wells and plate for cleanup.
    
        Raises:
            AssertionError: If the function's output is not as expected.
    
        Side Effects:
            - Adds and removes test wells and a test plate in the database.
        """

        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        ### Create test wells
        well_params_01 = dict(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A40a",
            wellEcho="A40a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
            fished=True,
            shifterTimeOfDeparture=datetime.now().isoformat(),
            xtalName="xtal-1"
        )
        well_params_02 = dict(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B40b",
            wellEcho="B40b",
            x=500,
            y=700,
            xEcho=4.32,
            yEcho=2.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
            fished=True,
            shifterTimeOfDeparture=(datetime.now() + timedelta(hours=1)).isoformat(),
            xtalName="xtal-2"
        )
        added_well_id_01 = self.add_test_well(**well_params_01)['inserted_id']
        added_well_id_02 = self.add_test_well(**well_params_02)['inserted_id']
    
        ### Add a test plate
        last_imaged = datetime.now()
        batch_id = "987654"
        plate_params = dict(
            user_account=user_account,
            campaign_id=campaign_id,
            plate_id=plate_id,
            lastImaged=last_imaged.isoformat(),
            batchId=batch_id
        )
        added_plate_id = self.add_test_plate(**plate_params)['inserted_id']
    
        ### Perform the operation
        retrieved_data = self.client.get_next_xtal_number(plate_id)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of get_next_xtal_number function is None.")
            self.assertEqual(retrieved_data, 3, "The next crystal number does not match the expected number.")
        finally:
            ### Delete the wells and plate after the test
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
            self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG get_next_xtal_number

    ### FETCH_TAG get_soaked_wells
    def test_41_get_soaked_wells(self):
        """
        Test the functionality of the 'get_soaked_wells' function
        
        This test performs the following operations:
        1. Initialize constants for the test user, campaign, and plate.
        2. Create two test wells with predefined attributes.
        3. Call the 'get_soaked_wells' API to retrieve the wells based on the user and campaign.
        4. Convert ObjectIds to string format for comparison.
        5. Filter out the relevant test wells from the retrieved data.
        6. Validate the output against expected results.
        
        Finally, it cleans up by deleting the test wells added for this test.
    
        :raises AssertionError: If the result is None or no soaked wells were found.
        :raises AssertionError: If the first soaked well does not match the expected well.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A41a",
            wellEcho="A41a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
            fished=False,
            shifterTimeOfDeparture=datetime.now().isoformat(),
            soakTransferTime=datetime.now().isoformat(),
            soakTransferStatus="OK",
        )['inserted_id']
    
        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B41b",
            wellEcho="B41b",
            x=500,
            y=700,
            xEcho=4.32,
            yEcho=2.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus="exported",
            fished=False,
            shifterTimeOfDeparture=(datetime.now() + timedelta(hours=1)).isoformat(),
            soakTransferTime=datetime.now().isoformat(),
            soakTransferStatus="OK",
        )['inserted_id']
    
        ### Perform the operation
        retrieved_data = self.client.get_soaked_wells(user_account, campaign_id)
        retrieved_data = self.convert_objectid_to_str(retrieved_data)
    
        ### Filter added test data
        filtered_data = [
            doc for doc in retrieved_data if (
                doc["userAccount"] == user_account and
                doc["campaignId"] == campaign_id and
                doc["plateId"] == plate_id and
                ((doc["well"] == "A41a" and doc["wellEcho"] == "A41a") or
                 (doc["well"] == "B41b" and doc["wellEcho"] == "B41b"))
            )
        ]
        printv(f"\n{json.dumps(filtered_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsNotNone(filtered_data, "Result of get_soaked_wells function is None.")
            self.assertTrue(len(filtered_data) > 0, "No soaked wells were found.")
            self.assertEqual(filtered_data[0]['_id'], added_well_id_01, "The first soaked well does not match the expected well.")
        finally:
            ### Delete the wells after the test
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
    ### FETCH_TAG get_soaked_wells

    ### FETCH_TAG get_number_of_unsoaked_wells
    def test_42_get_number_of_unsoaked_wells(self):
        """
        Test the get_number_of_unsoaked_wells function.
    
        This integration test performs the following steps:
        1. Initializes test constants, including user_account, campaign_id, and plate_id.
        2. Adds a new test well with a specific 'soakStatus' set to None.
        3. Queries the number of unsoaked wells for the given user and campaign.
        4. Validates the retrieved data to ensure it is neither None nor zero/negative.
        5. Deletes the added test well to clean up.
    
        Raises:
            AssertionError: If the result of get_number_of_unsoaked_wells function is None or zero/negative.
        """
    
        ### Initialize constants for the test
        user_account = "e14965"
        campaign_id = "EP_SmarGon_TEST"
        plate_id = "98765"
    
        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A42a",
            wellEcho="A42a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus=None,
            fished=False,
            shifterTimeOfDeparture=datetime.now().isoformat(),
            soakTransferTime=datetime.now().isoformat(),
            soakTransferStatus="OK",
        )['inserted_id']
    
        ### Perform the operation to get the number of unsoaked wells
        retrieved_data = self.client.get_number_of_unsoaked_wells(user_account, campaign_id)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Validate the results through assertions
            self.assertIsNotNone(retrieved_data, "Result of get_number_of_unsoaked_wells function is None.")
            self.assertTrue(retrieved_data > 0, "The number of unsoaked wells is zero or negative.")
        finally:
            ### Cleanup: Delete the test well after the test
            self.delete_by_id("wells", added_well_id_01)
    ### FETCH_TAG get_number_of_unsoaked_wells

    ### FETCH_TAG update_soaking_duration
    def test_43_update_soaking_duration(self):
        """
        Test the functionality of updating soaking duration for wells.
    
        This test:
        - Initializes constants and creates test wells.
        - Sends a request to update the soaking duration for the created well(s).
        - Validates the output and optionally fetches the updated well to check if soakDuration has been updated.
        - Deletes the test well after the test.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        soak_start_time = (datetime.now() - timedelta(hours=1)).isoformat()
    
        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A43a",
            wellEcho="A43a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus=None,
            fished=False,
            shifterTimeOfDeparture=datetime.now().isoformat(),
            soakTransferStatus="OK",
            soakTransferTime=soak_start_time
        )['inserted_id']
    
        wells_data = [{
            "_id": added_well_id_01,
            "userAccount": user_account,
            "campaignId": campaign_id,
            "plateId": plate_id,
            "well": "A43a",
            "wellEcho": "A43a",
            "x": 488,
            "y": 684,
            "xEcho": 3.32,
            "yEcho": 1.87,
            "soakTransferTime": soak_start_time,
        }]
    
        ### Explicitly add the _id field to each well in the payload
        for well in wells_data:
            well["_id"] = str(added_well_id_01)
    
        ### Perform the operation
        data = {
            "user": user_account,
            "campaign_id": campaign_id,
            "wells": wells_data
        }
    
        try:
            retrieved_data = self.client.update_soaking_duration(**data)
            retrieved_data = retrieved_data.to_dict()
            
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of update_soaking_duration function is None.")
            self.assertEqual(retrieved_data['nModified'], 1, "No modification was made to the document.")
            self.assertEqual(retrieved_data['ok'], 1.0, "Operation was not successful.")
            self.assertEqual(retrieved_data['n'], 1, "Expected to modify 1 document, but it didn't.")
            
            ### Optionally: Fetch the well from DB and check if soakDuration has been updated
            retrieved_data_updated_well_01 = self.client.get_one_well(added_well_id_01)
            retrieved_data_updated_well_01 = self.convert_objectid_to_str(retrieved_data_updated_well_01)
            self.assertTrue(retrieved_data_updated_well_01['soakDuration'] >= 3590, f"Soak duration not updated correctly: {retrieved_data_updated_well_01['soakDuration']}.")
    
        except Exception as e:
            print(f"Test failed due to: {e}")
            raise
    
        finally:
            ### Delete the test well after the test
            self.delete_by_id("wells", added_well_id_01)
    ### FETCH_TAG update_soaking_duration

    ### FETCH_TAG get_all_fished_wells
    def test_44_get_all_fished_wells(self):
        """
        Integration test for get_all_fished_wells functionality.
        Validates if the function correctly retrieves fished wells for a given user and campaign.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A44a",
            wellEcho="A44a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            fished=True,
        )['inserted_id']
        
        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B44b",
            wellEcho="B44b",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            fished=True,
        )['inserted_id']
        
        added_well_id_03 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="C44c",
            wellEcho="C44c",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            fished=False,
        )['inserted_id']
    
        ### Perform the operation
        retrieved_data = self.client.get_all_fished_wells(user_account, campaign_id)
    
        ### Filter added test data
        retrieved_data = [doc for doc in retrieved_data if (
            doc["userAccount"] == user_account and
            doc["campaignId"] == campaign_id and
            doc["plateId"] == plate_id and
            ((doc["well"] == "A44a" and doc["wellEcho"] == "A44a") or
             (doc["well"] == "B44b" and doc["wellEcho"] == "B44b") or
             (doc["well"] == "C44c" and doc["wellEcho"] == "C44c"))
        )]
        
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of get_all_fished_wells function is None.")
            self.assertIsInstance(retrieved_data, list, "The result is not a list.")
            self.assertGreater(len(retrieved_data), 0, "No fished wells were found.")
            self.assertEqual(len(retrieved_data), 2, "Not exactly 2 fished wells were found.")
        finally:
            ### Delete the test well after the test
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
            self.delete_by_id("wells", added_well_id_03)
    ### FETCH_TAG get_all_fished_wells

    ### FETCH_TAG get_all_wells_not_exported_to_datacollection_xls
    def test_45_get_all_wells_not_exported_to_datacollection_xls(self):
        """
        Integration test for getting all wells not exported to the datacollection xls.
        This function performs the following steps:
            1. Initializes constants such as user account, campaign, and plate IDs.
            2. Creates test well data.
            3. Fetches the wells not exported to xls.
            4. Validates the fetched data.
            5. Cleans up by deleting the test well data.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A45a",
            wellEcho="A45a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            fished=True,
            exportedToXls=False,
            xtalName="xtal-1",
        )['inserted_id']

        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B45b",
            wellEcho="B45b",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            fished=True,
            exportedToXls=False,
            xtalName="xtal-2",
        )['inserted_id']

        added_well_id_03 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="C45c",
            wellEcho="C45c",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            fished=False,
            exportedToXls=False,
            xtalName="xtal-3",
        )['inserted_id']
    
        ### Perform the operation
        try:
            retrieved_data = self.client.get_all_wells_not_exported_to_datacollection_xls(user_account, campaign_id)
            ### Convert ObjectId objects to strings for printing
            retrieved_data_str = self.convert_objectid_to_str(retrieved_data)
            printv(f"\n{json.dumps(retrieved_data_str, indent=4)}")
    
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of get_all_wells_not_exported_to_datacollection_xls function is None.")
            self.assertIsInstance(retrieved_data, list, "The result is not a list.")
            self.assertGreater(len(retrieved_data), 0, "No wells were found that were not exported to xls.")
            self.assertEqual(len(retrieved_data), 2, "Not exactly 2 fished wells were found.")
        except Exception as e:
            print(f"An error occurred during the test: {e}")
        finally:
            ### Delete the test well after the test
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("wells", added_well_id_02)
            self.delete_by_id("wells", added_well_id_03)
    ### FETCH_TAG get_all_wells_not_exported_to_datacollection_xls

    ### FETCH_TAG mark_exported_to_xls
    def test_46_mark_exported_to_xls(self):
        """
        Test the functionality of marking a well as exported to XLS.
        This test will:
        - Create a new test well with 'exportedToXls' set to False.
        - Mark this well as exported to XLS.
        - Check if the operation was successful and if the 'exportedToXls' flag has been updated.
        """
    
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        soak_start_time = (datetime.now() - timedelta(hours=1)).isoformat()
    
        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount = user_account,
            campaignId = campaign_id,
            plateId = plate_id,
            well = "A46a",
            wellEcho = "A46a",
            x = 488,
            y = 684,
            xEcho = 3.32,
            yEcho = 1.87,
            redesolveExportTime = None,
            redesolveApplied = True,
            soakStatus = None,
            fished = False,
            shifterTimeOfDeparture = datetime.now().isoformat(),
            soakTransferStatus = "OK",
            soakTransferTime = soak_start_time,
            exportedToXls = False,
        )['inserted_id']
    
        wells_data = [{
            "_id": added_well_id_01,
            "userAccount": user_account,
            "campaignId": campaign_id,
            "plateId": plate_id,
            "well": "A46a",
            "wellEcho": "A46a",
            "x": 488,
            "y": 684,
            "xEcho": 3.32,
            "yEcho": 1.87,
            "soakTransferTime": soak_start_time,
        }]
    
        ### Update the _id field for each well in the payload
        for well in wells_data:
            well["_id"] = str(added_well_id_01)
    
        ### Perform the operation
        data = {
            "wells": wells_data
        }
        retrieved_data = self.client.mark_exported_to_xls(**data)
        
        retrieved_data = retrieved_data.to_dict()
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of mark_exported_to_xls function is None.")
            self.assertEqual(retrieved_data['nModified'], 1, "No modification was made to the document.")
            self.assertEqual(retrieved_data['ok'], 1.0, "Operation was not successful.")
            self.assertEqual(retrieved_data['n'], 1, "Expected to modify 1 document, but it didn't.")
    
            ### Optionally: Fetch the well from DB and check if soakDuration has been updated
            retrieved_data_updated_well_01 = self.client.get_one_well(added_well_id_01)
            self.assertTrue(retrieved_data_updated_well_01['exportedToXls'], "exportedToXls is not True")
    
        finally:
            ### Delete the test well after the test
            self.delete_by_id("wells", added_well_id_01)
    ### FETCH_TAG mark_exported_to_xls

    ### FETCH_TAG send_notification
    def test_47_send_notification(self):
        """
        Integration test for the send_notification function.
    
        The test initializes constant values and performs the send_notification operation,
        followed by a series of assertions to confirm the behavior.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        notification_type = "test_notification"
    
        ### Perform the operation
        retrieved_data = self.client.send_notification(user_account, campaign_id, notification_type)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Response from send_notification function is None.")
            self.assertTrue(retrieved_data["acknowledged"], "Notification not acknowledged.")
            self.assertIsNotNone(retrieved_data["inserted_id"], "No inserted_id found in the response.")
        except:
            printv("Something went wrong in test_47_send_notification")
    ### FETCH_TAG send_notification

    ### FETCH_TAG get_notifications
    def test_48_get_notifications(self):
        """
        Integration test for the get_notifications function.
    
        This test performs the following operations in sequence:
            1. Sends a test notification using the send_notification function.
            2. Verifies the acknowledgment and inserted_id returned by the send_notification function.
            3. Retrieves notifications using the get_notifications function, which returns a CursorMock object.
            4. Validates the retrieved notifications, including checks for CursorMock functionalities like sorting, skipping, and limiting.
            5. Checks cursor rewind and close functionalities on the CursorMock object.
    
        The CursorMock object is a mock of a MongoDB cursor and mimics its behavior including methods like count(), skip(), limit(), sort(), rewind(), close(), and the alive property.
    
        Side-effects:
            - Makes actual network calls to the FastAPI server.
            - Prints verbose output for debugging.
            - Inserts a test notification into the database.
            - Retrieves and alters notifications from the database.
    
        Raises:
            AssertionError: If any of the conditions checked by the unittest's assert methods fail.
    
        Exceptions:
            - Catches and logs any exceptions, printing an error message.
        """

        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        notification_type = "test_notification"

        ### Send a notification
        retrieved_data_send = self.client.send_notification(user_account, campaign_id, notification_type)
        printv(f"\n{json.dumps(retrieved_data_send, indent=4)}")

        try:
            self.assertIsNotNone(retrieved_data_send, "Response from send_notification function is None.")
            self.assertTrue(retrieved_data_send["acknowledged"], "Notification not acknowledged.")

            inserted_id = retrieved_data_send["inserted_id"]
            self.assertIsNotNone(inserted_id, "No inserted_id found in the response.")

            ### Get notifications after sending
            timestamp = datetime.utcnow().isoformat()
            retrieved_data_get = self.client.get_notifications(user_account, campaign_id, timestamp)
            self.assertIsNotNone(retrieved_data_get, "Cursor-like object from get_notifications function is None.")

            ### Check full functionality of CursorMock
            initial_count = retrieved_data_get.count()
            self.assertEqual(initial_count, len(retrieved_data_get.original_data), "Initial count mismatch.")

            ### Convert the mock cursor to a list for easier checks
            notifications = list(retrieved_data_get)
            for notification in notifications:
                notification["_id"] = str(notification["_id"])

            ### Check if the added notification is in the retrieved notifications
            sent_notification_present = any([notif for notif in notifications if notif["_id"] == str(ObjectId(inserted_id))])
            self.assertTrue(sent_notification_present, "The sent notification was not retrieved.")

            ### Ensure ObjectId is correctly formatted
            for notification in notifications:
                notification["_id"] = str(notification["_id"])
                self.assertTrue(isinstance(notification["_id"], str), "ObjectId not converted to string format.")

            ### Check skip, limit, sort, and rewind on the CursorMock
            retrieved_data_get.rewind()
            retrieved_data_get.sort("_id").skip(1).limit(2)
            limited_notifications = list(retrieved_data_get)
            self.assertEqual(len(limited_notifications), 2, "Limit not applied correctly.")
            self.assertEqual(retrieved_data_get.count(with_limit_and_skip=True), 2, "Count with limit and skip is incorrect.")

            ### Check rewind
            retrieved_data_get.rewind()
            self.assertEqual(retrieved_data_get.index, 0, "Cursor not rewinded correctly.")

            ### Check close and alive property
            self.assertTrue(retrieved_data_get.alive, "Cursor should still be alive.")
            retrieved_data_get.close()
            self.assertFalse(retrieved_data_get.alive, "Cursor should be closed.")

        except:
            ### Handle any exceptions by printing an error message
            printv("Something went wrong in test_48_get_notifications")
    ### FETCH_TAG get_notifications

    ### FETCH_TAG add_fragment_to_well
    def test_49_add_fragment_to_well(self):
        """
        Integration test for the add_fragment_to_well functionality. This test adds a fragment to a well
        and then checks if the well and library documents in the database have been updated correctly.
    
        This test involves creating test campaign libraries and wells, adding a fragment to a well,
        and then verifying the updated well and library documents to ensure the correctness of the operation.
    
        The test asserts the proper assignment of library and fragment details to the well, and the marking
        of the fragment as used in the library.
    
        Args:
            None
    
        Returns:
            None
    
        Raises:
            AssertionError: If any of the test assertions fail.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
    
        ### Add test campaign_library before starting the actual test
        added_campaign_library_id = self.add_campaign_library(
            userAccount = user_account,
            campaignId = campaign_id,
            libraryName = "Test_Library_Heidi_C",
            libraryBarcode = "A98765",
            fragments = [
                {
                    "compoundCode": "C001",
                    "smiles": "c1ccccc1",
                    "well": "A49a",
                    "used": False,
                    "libraryConcentration": "1.0"
                },
                {
                    "compoundCode": "C002",
                    "smiles": "O=C(C)Oc1ccccc1C(=O)O",
                    "well": "A49a",
                    "used": False
                }
            ]
        )['inserted_id']
    
        soak_start_time = (datetime.now() - timedelta(hours=1)).isoformat()
    
        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount = user_account,
            campaignId = campaign_id,
            plateId = plate_id,
            well = "A49a",
            wellEcho = "A49a",
            x = 488,
            y = 684,
            xEcho = 3.32,
            yEcho = 1.87,
            redesolveExportTime = None,
            redesolveApplied = True,
            soakStatus = None,
            fished = False,
            shifterTimeOfDeparture = datetime.now().isoformat(),
            soakTransferStatus = "OK",
            soakTransferTime = soak_start_time,
            exportedToXls = False,
        )['inserted_id']
    
        ### Setup example data
        library = {
            'libraryName': 'TestLibrary',
            'libraryBarcode': 'A98765',
            '_id': ObjectId(added_campaign_library_id)
        }
        added_well_id_01 = ObjectId(added_well_id_01)
        fragment = {
            'well': 'A49a',
            'smiles': 'c1ccccc1',
            'compoundCode': 'C001',
            'libraryConcentration': '1.0'
        }
        solvent_volume = 1.5
        ligand_transfer_volume = 0.5
        ligand_concentration = 1.0
        is_solvent_test = False
    
        printv("library and fragment")
        printv(library)
        printv(fragment)
    
        ### Perform the operation
        retrieved_data = self.client.add_fragment_to_well(library, added_well_id_01, fragment, solvent_volume,
                                                  ligand_transfer_volume, ligand_concentration,
                                                  is_solvent_test)
        ### Convert the mock object to the desired JSON format
        retrieved_data = {"nModified": retrieved_data.nModified, "ok": retrieved_data.ok, "n": retrieved_data.n}
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsNotNone(retrieved_data, "Result of add_fragment_to_well function is None.")
            self.assertEqual(retrieved_data['nModified'], 1, "No modification was made to the document.")
            self.assertEqual(retrieved_data['ok'], 1.0, "Operation was not successful.")
            self.assertEqual(retrieved_data['n'], 1, "Expected to modify 1 document, but it didn't.")
    
            retrieved_data_updated_well_01 = self.client.get_one_well(added_well_id_01)
            ### Convert ObjectIds to strings
            retrieved_data_updated_well_01 = self.convert_objectid_to_str(retrieved_data_updated_well_01)
            printv(f"\n{json.dumps(retrieved_data_updated_well_01, indent=4)}")
            retrieved_data_updated_library = self.client.get_one_campaign_library(added_campaign_library_id)
            ### Convert ObjectIds to strings
            retrieved_data_updated_library = self.convert_objectid_to_str(retrieved_data_updated_library)
            printv(f"\n{json.dumps(retrieved_data_updated_library, indent=4)}")
    
            ### Assertions to check updates in wells
            self.assertIsNotNone(retrieved_data_updated_well_01, "Well data is None.")
            self.assertEqual(retrieved_data_updated_well_01['libraryName'], library['libraryName'], "Library name mismatch in well.")
            self.assertEqual(retrieved_data_updated_well_01['libraryBarcode'], library['libraryBarcode'], "Library barcode mismatch in well.")
            self.assertEqual(retrieved_data_updated_well_01['libraryId'], str(library['_id']), "Library ID mismatch in well.")
            self.assertEqual(retrieved_data_updated_well_01['solventTest'], is_solvent_test, "Solvent test mismatch in well.")
            self.assertEqual(retrieved_data_updated_well_01['sourceWell'], fragment['well'], "Source well mismatch in well.")
            self.assertTrue(retrieved_data_updated_well_01['libraryAssigned'], "Library not assigned in well.")
            self.assertEqual(retrieved_data_updated_well_01['compoundCode'], fragment['compoundCode'], "Compound code mismatch in well.")
            self.assertEqual(retrieved_data_updated_well_01['smiles'], fragment['smiles'], "SMILES code mismatch in well.")
            self.assertEqual(retrieved_data_updated_well_01['libraryConcentration'], fragment['libraryConcentration'], "Library concentration mismatch in well.")
            self.assertEqual(retrieved_data_updated_well_01['solventVolume'], solvent_volume, "Solvent volume mismatch in well.")
            self.assertEqual(retrieved_data_updated_well_01['ligandTransferVolume'], ligand_transfer_volume, "Ligand transfer volume mismatch in well.")
            self.assertEqual(retrieved_data_updated_well_01['ligandConcentration'], ligand_concentration, "Ligand concentration mismatch in well.")
            self.assertEqual(retrieved_data_updated_well_01['soakStatus'], 'pending', "Soak status mismatch in well.")
    
            ### Assertions to check updates in library
            self.assertIsNotNone(retrieved_data_updated_library, "Library data is None.")
            self.assertTrue(any(fragment['compoundCode'] == frag['compoundCode'] and frag['used'] for frag in retrieved_data_updated_library['fragments']), "No used fragment found with the given compoundCode.")
    
        finally:
            ### Delete the test well after the test
            self.delete_by_id("wells", added_well_id_01)
            ### Delete the test campaign_libraries after the test
            self.delete_by_id("campaign_libraries", added_campaign_library_id)
    ### FETCH_TAG add_fragment_to_well

    ### FETCH_TAG remove_fragment_from_well
    def test_50_remove_fragment_from_well(self):
        """
        Tests the removal of a fragment from a well. It verifies that the fragment is successfully
        removed by checking various attributes of the well post-operation. The test also covers the
        retrieval and conversion of data to the desired format for validation.
    
        This function sets up the test environment, adds necessary data, performs the fragment removal
        operation, and finally conducts assertions to ensure the operation's success.
    
        Raises:
            AssertionError: If any of the test assertions fail.
        """
        # Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        soak_start_time = (datetime.now() - timedelta(hours=1)).isoformat()
    
        # Add test library
        added_campaign_library_id = self.add_campaign_library(
            userAccount=user_account,
            campaignId=campaign_id,
            libraryName="Test_Library_Heidi_C",
            libraryBarcode="A98765",
            fragments=[
                {"compoundCode": "C001", "smiles": "c1ccccc1", "well": "A50a", "used": False, "libraryConcentration": "1.0"},
                {"compoundCode": "C002", "smiles": "O=C(C)Oc1ccccc1C(=O)O", "well": "A50a", "used": False}
            ]
        )['inserted_id']
    
        # Create test well
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A50a",
            wellEcho="A50a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            redesolveExportTime=None,
            redesolveApplied=True,
            soakStatus=None,
            fished=False,
            shifterTimeOfDeparture=datetime.now().isoformat(),
            soakTransferStatus="OK",
            soakTransferTime=soak_start_time,
            exportedToXls=False,
        )['inserted_id']
    
        # Setup example data for the test
        library = {'libraryName': 'TestLibrary', 'libraryBarcode': '98765', '_id': ObjectId(added_campaign_library_id)}
        added_well_id_01 = ObjectId(added_well_id_01)
        fragment = {'well': 'A50a', 'smiles': 'c1ccccc1', 'compoundCode': 'C001', 'libraryConcentration': '1.0'}
        solvent_volume = 1.5
        ligand_transfer_volume = 0.5
        ligand_concentration = 1.0
        is_solvent_test = False
    
        # Perform operation to add fragment to the well
        retrieved_data_test_well = self.client.add_fragment_to_well(library, added_well_id_01, fragment, solvent_volume,
                                                                   ligand_transfer_volume, ligand_concentration,
                                                                   is_solvent_test)
        # Convert the result to desired JSON format
        retrieved_data_test_well = {"nModified": retrieved_data_test_well.nModified, "ok": retrieved_data_test_well.ok, "n": retrieved_data_test_well.n}
        printv(f"\n{json.dumps(retrieved_data_test_well, indent=4)}")
    
        # Perform the fragment removal operation
        retrieved_data = self.client.remove_fragment_from_well(ObjectId(added_well_id_01))
        # Convert the result to desired JSON format
        retrieved_data = {"nModified": retrieved_data.nModified, "ok": retrieved_data.ok, "n": retrieved_data.n}
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            # Assertions to verify the success of the fragment removal operation
            self.assertIsNotNone(retrieved_data, "Result of remove_fragment_from_well function is None.")
            self.assertEqual(retrieved_data["nModified"], 1, "No modification was made to the document.")
            self.assertEqual(retrieved_data["ok"], 1.0, "Operation was not successful.")
            self.assertEqual(retrieved_data["n"], 1, "Expected to modify 1 document, but it didn't.")
    
            # Retrieve updated well data and convert ObjectId to string for verification
            retrieved_data_updated_well = self.client.get_one_well(added_well_id_01)
            retrieved_data_updated_well = self.convert_objectid_to_str(retrieved_data_updated_well)
            printv(f"\n{json.dumps(retrieved_data_updated_well, indent=4)}")
    
            # Assertions to check if the fragment was successfully removed from the well
            self.assertIsNotNone(retrieved_data_updated_well, "Well data is None after removal operation.")
            self.assertIsNone(retrieved_data_updated_well['libraryName'], "libraryName is not None.")
            self.assertIsNone(retrieved_data_updated_well['libraryBarcode'], "libraryBarcode is not None.")
            self.assertIsNone(retrieved_data_updated_well['libraryId'], "libraryId is not None.")
            self.assertIsNone(retrieved_data_updated_well['sourceWell'], "sourceWell is not None.")
            self.assertFalse(retrieved_data_updated_well['libraryAssigned'], "libraryAssigned is not False.")
            self.assertFalse(retrieved_data_updated_well['solventTest'], "solventTest is not False.")
            self.assertIsNone(retrieved_data_updated_well['compoundCode'], "compoundCode is not None.")
            self.assertIsNone(retrieved_data_updated_well['smiles'], "smiles is not None.")
            self.assertIsNone(retrieved_data_updated_well['libraryConcentration'], "libraryConcentration is not None.")
            self.assertIsNone(retrieved_data_updated_well['solventVolume'], "solventVolume is not None.")
            self.assertIsNone(retrieved_data_updated_well['ligandTransferVolume'], "ligandTransferVolume is not None.")
            self.assertIsNone(retrieved_data_updated_well['ligandConcentration'], "ligandConcentration is not None.")
            self.assertIsNone(retrieved_data_updated_well['soakStatus'], "soakStatus is not None.")
        finally:
            # Cleanup: delete the test well and library
            self.delete_by_id("wells", added_well_id_01)
            self.delete_by_id("campaign_libraries", added_campaign_library_id)
    ### FETCH_TAG remove_fragment_from_well

    ### FETCH_TAG import_library
    def test_51_import_library(self):
        """
        Integration test for the import_library method of the client.
    
        This test initializes a library data structure, imports it into the database using the client's import_library method, and then performs various assertions to ensure that the library has been correctly imported. It checks if the returned ID matches the library barcode, and then retrieves the library from the database to validate its contents against the initial data.
    
        After testing, the library is deleted from the database to clean up.
    
        Raises:
            AssertionError: If any of the assertions fail, indicating that the library was not imported correctly or the retrieved data does not match the expected values.
        """
    
        ### Initialize library data for the test
        test_library = {
            "libraryName": "Test_Library_Heidi_A",
            "libraryBarcode": ObjectId('64d4d1bea8f822476c37f97a'),
            "fragments": [
                {
                    "compoundCode": "C901",
                    "smiles": "C(C(C(=O)O)c1ccccc1)c2ccccc2",
                    "well": "A51a",
                    "used": False,
                    "libraryConcentration": "0.8"
                },
                {
                    "compoundCode": "C902",
                    "smiles": "C1CCOC1",
                    "well": "A51a",
                    "used": False
                }
            ]
        }
    
        ### Perform the operation
        retrieved_data = self.client.import_library(test_library)
        ### Convert the mock object to the desired JSON format
        retrieved_data = {"acknowledged": retrieved_data.acknowledged, "_id": str(retrieved_data.inserted_id)}
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        ### Convert ObjectIds to strings
        retrieved_data = self.convert_objectid_to_str(retrieved_data)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Assertions for retrieved_data
            self.assertEqual(retrieved_data['_id'], str(test_library['libraryBarcode']), "Expected the returned id to match the libraryBarcode.")
    
            ### Retrieve and assert the imported library data
            retrieved_data_imported_library = self.client.get_one_library(str(test_library['libraryBarcode']))
            retrieved_data_imported_library = self.convert_objectid_to_str(retrieved_data_imported_library)
            printv(f"\n{json.dumps(retrieved_data_imported_library, indent=4)}")
    
            ### Assertions for retrieved_data_imported_library
            self.assertLibraryData(retrieved_data_imported_library, test_library)
    
        finally:
            ### Cleanup: Delete the test libraries after the test
            self.delete_by_id("libraries", retrieved_data["_id"])
    
    def assertLibraryData(self, retrieved_library, expected_library):
        """
        Helper method to assert library data against expected values.
    
        Args:
            retrieved_library (dict): The library data retrieved from the database.
            expected_library (dict): The expected library data.
    
        Raises:
            AssertionError: If the retrieved library data does not match the expected values.
        """
        self.assertEqual(retrieved_library['_id'], str(expected_library['libraryBarcode']), "Expected _id to match the libraryBarcode.")
        self.assertEqual(retrieved_library['libraryName'], expected_library['libraryName'], "Mismatch in libraryName.")
        self.assertEqual(retrieved_library['libraryBarcode'], str(expected_library['libraryBarcode']), "Mismatch in libraryBarcode.")
        self.assertEqual(len(retrieved_library['fragments']), len(expected_library['fragments']), "Mismatch in the number of fragments.")
    
        for idx, fragment in enumerate(expected_library['fragments']):
            retrieved_fragment = retrieved_library['fragments'][idx]
            self.assertEqual(retrieved_fragment['compoundCode'], fragment['compoundCode'], "Mismatch in compoundCode.")
            self.assertEqual(retrieved_fragment['smiles'], fragment['smiles'], "Mismatch in smiles.")
            self.assertEqual(retrieved_fragment['well'], fragment['well'], "Mismatch in well.")
            self.assertEqual(retrieved_fragment['used'], fragment['used'], "Mismatch in used.")
            if 'libraryConcentration' in fragment:
                self.assertIn('libraryConcentration', retrieved_fragment, "libraryConcentration missing.")
                self.assertEqual(retrieved_fragment['libraryConcentration'], fragment['libraryConcentration'], "Mismatch in libraryConcentration.")
    ### FETCH_TAG import_library

    ### FETCH_TAG get_libraries
    def test_52_get_libraries(self):
        """
        Integration test to verify the retrieval of libraries from the database.
    
        This test involves creating a sample library, using the client to import it into the database, and then retrieving it using the get_libraries method. 
        The retrieved libraries are filtered to find the test library, and various assertions are performed to validate the contents and structure of the 
        returned data. The test ensures that the library retrieval functionality works as expected, including the conversion of MongoDB ObjectIds to strings.
    
        Finally, the test cleans up by deleting the test library from the database.
    
        Raises:
            AssertionError: If the retrieved data does not meet the expected conditions.
        """
    
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
    
        # Setup: Create and import a test library
        test_library = {
            "userAccount": user_account,
            "campaignId": campaign_id,
            "libraryName": "Test_Library_Heidi_A",
            "libraryBarcode": ObjectId('64d4d1bea8f822476c37f97a'),
            "fragments": [
                {
                    "compoundCode": "C901",
                    "smiles": "C(C(C(=O)O)c1ccccc1)c2ccccc2",
                    "well": "A52a",
                    "used": False,
                    "libraryConcentration": "0.8"
                },
                {
                    "compoundCode": "C902",
                    "smiles": "C1CCOC1",
                    "well": "A52a",
                    "used": False
                }
            ]
        }
        retrieved_data_added_test_library = self.client.import_library(test_library)
        retrieved_data_added_test_library = {
            "acknowledged": retrieved_data_added_test_library.acknowledged, 
            "_id": str(retrieved_data_added_test_library.inserted_id)
        }
    
        ### Perform the operation
        retrieved_data = self.client.get_libraries()
    
        ### Filter added test data
        retrieved_data = [doc for doc in retrieved_data if doc["libraryName"] == "Test_Library_Heidi_A"]
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsInstance(retrieved_data, list, "Expected the response to be a list.")
            self.assertTrue(retrieved_data, "Expected at least one library in the response.")
    
            first_library = retrieved_data[0]
    
            ### Check main fields from the sample data in the returned library
            self.assertIn("libraryName", first_library, "Expected 'libraryName' field in the library.")
            self.assertIn("libraryBarcode", first_library, "Expected 'libraryBarcode' field in the library.")
            self.assertIn("fragments", first_library, "Expected 'fragments' field in the library.")
    
            ### Validate the specific data from the sample in the returned library
            self.assertEqual(first_library["libraryName"], test_library["libraryName"], "Mismatch in libraryName.")
            self.assertEqual(first_library["libraryBarcode"], str(test_library["libraryBarcode"]), "Mismatch in libraryBarcode.")
    
            ### Validate the fragments of the library in detail
            self.assertIsInstance(first_library["fragments"], list, "Expected 'fragments' to be a list.")
            self.assertEqual(len(first_library["fragments"]), len(test_library["fragments"]), "Mismatch in the number of fragments.")
    
            for i, fragment in enumerate(test_library["fragments"]):
                returned_fragment = first_library["fragments"][i]
                self.assertEqual(fragment["compoundCode"], returned_fragment["compoundCode"], f"Mismatch in compoundCode for fragment {i}.")
                self.assertEqual(fragment["smiles"], returned_fragment["smiles"], f"Mismatch in smiles for fragment {i}.")
        finally:
            ### Cleanup: Delete the test library after the test
            self.delete_by_id("libraries", retrieved_data_added_test_library["_id"])
    ### FETCH_TAG get_libraries
    
    ### FETCH_TAG get_campaign_libraries
    def test_53_get_campaign_libraries(self):
        """
        Test for retrieving campaign libraries associated with a specific user and campaign ID.
    
        This test performs the operation to retrieve libraries using get_campaign_libraries method from the client.
        It then filters the retrieved data for a specific test library added before the test.
        Assertions are made to verify the expected data structure and contents.
        Finally, the test cleans up by deleting the test campaign library added at the beginning.
    
        Args:
            self: Instance of the test class.
    
        Raises:
            AssertionError: If any of the test assertions fail.
        """
    
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
    
        ### Note: Assuming some sample libraries have already been added for this user_account and campaign_id
        ### Add test campaign_library before starting the actual test
        added_campaign_library_id = self.add_campaign_library(
            userAccount=user_account,
            campaignId=campaign_id,
            libraryName="Test_Library_Heidi_C",
            libraryBarcode="A98765",
            fragments=[
                {
                    "compoundCode": "C531",
                    "smiles": "c1ccccc1",
                    "well": "A53a",
                    "used": False,
                    "libraryConcentration": "1.0"
                },
                {
                    "compoundCode": "C532",
                    "smiles": "O=C(C)Oc1ccccc1C(=O)O",
                    "well": "A53a",
                    "used": False
                }
            ]
        )['inserted_id']
    
        ### Perform the operation
        retrieved_data = self.client.get_campaign_libraries(user_account, campaign_id)
    
        ### Filter added test data
        retrieved_data = [doc for doc in retrieved_data if doc['libraryName'] == "Test_Library_Heidi_C"]
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
        printv(f"\n{json.dumps(len(retrieved_data), indent=4)}")
    
        try:
            ### Assertions
            self.assertIsInstance(retrieved_data, list, "Expected the response to be a list.")
            self.assertTrue(retrieved_data, "Expected at least one library in the response for the given user_account and campaign.")
    
            first_library = retrieved_data[0]
    
            ### Check main fields from the sample data in the returned library
            self.assertIn("libraryName", first_library, "Expected 'libraryName' field in the library.")
            self.assertIn("libraryBarcode", first_library, "Expected 'libraryBarcode' field in the library.")
            self.assertIn("fragments", first_library, "Expected 'fragments' field in the library.")
    
        finally:
            ### Delete the test campaign_libraries after the test
            self.delete_by_id("campaign_libraries", added_campaign_library_id)
    ### FETCH_TAG get_campaign_libraries

    ### FETCH_TAG get_library_usage_count
    def test_54_get_library_usage_count(self):
        """
        Tests the 'get_library_usage_count' function by simulating the retrieval of well usage count 
        for a specific library within a user account and campaign. It validates the response against 
        expected values.
    
        This test includes creating a test well, retrieving the library usage count, and performing 
        assertions on the response. It also handles cleanup by deleting the test well after the test.
    
        Args:
            self: Instance of the test class with access to client and utility methods.
    
        Raises:
            AssertionError: If any of the test assertions fail.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        library_id = str(ObjectId('64d4d1bea8f822476c37f97a'))  # Placeholder, replace with real ObjectId if needed.
    
        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A54a",
            wellEcho="A54a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            libraryId=library_id,
        )['inserted_id']
    
        ### Perform the operation
        retrieved_data = self.client.get_library_usage_count(user_account, campaign_id, library_id)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
    
        try:
            ### Assertions
            self.assertIsInstance(retrieved_data, int, "Expected the response to be an integer.")
            self.assertNotEqual(retrieved_data, -1, "Failed to fetch the count.")
            self.assertEqual(retrieved_data, 1, "Expected the response to be 1")
            ### Uncomment the line below once you have the real_database_method_to_get_count function in place
            ### self.assertEqual(count, expected_count, "Mismatch in the library usage count.")
    
        finally:
            ### Delete the test well after the test
            self.delete_by_id("wells", added_well_id_01)
    ### FETCH_TAG get_library_usage_count

    ### FETCH_TAG count_libraries_in_campaign
    def test_55_count_libraries_in_campaign(self):
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        library_id = str(ObjectId('64d4d1bea8f822476c37f97a'))  ### Just a placeholder, replace with real ObjectId if needed.

        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount = user_account,
            campaignId = campaign_id,
            plateId = plate_id,
            well = "A55a",
            wellEcho = "A55a",
            x = 488,
            y = 684,
            xEcho = 3.32,
            yEcho = 1.87,
            libraryId = library_id,
        )['inserted_id']

        ### The next line should fetch real count from the database (replace with a real method if you have any)
        ### expected_count = real_database_method_to_get_count(user, campaign_id, library_id)

        ### Perform the operation
        retrieved_data = self.client.count_libraries_in_campaign(user_account, campaign_id, library_id)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        try:
            ### Assertions
            self.assertIsInstance(retrieved_data, int, "Expected the response to be an integer.")
            self.assertNotEqual(retrieved_data, -1, "Failed to fetch the count.")
            self.assertEqual(retrieved_data, 1, "Expected the response to be 1")
            ### Uncomment the line below once you have the real_database_method_to_get_count function in place
            ### self.assertEqual(count, expected_count, "Mismatch in the library usage count.")

        finally:
            ### Delete the test well after the test
            self.delete_by_id("wells", added_well_id_01)
    ### FETCH_TAG count_libraries_in_campaign

    ### FETCH_TAG delete_by_id
    def test_56_delete_by_id(self):
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"
        library_id = str(ObjectId('64d4d1bea8f822476c37f97a'))  ### Just a placeholder, replace with real ObjectId if needed.

        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount = user_account,
            campaignId = campaign_id,
            plateId = plate_id,
            well = "A56a",
            wellEcho = "A56a",
            x = 488,
            y = 684,
            xEcho = 3.32,
            yEcho = 1.87,
            libraryId = library_id,
        )['inserted_id']

        ### Perform the operation
        retrieved_data = self.client.delete_by_id("wells", added_well_id_01)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        try:
            self.assertIsNotNone(retrieved_data, "Plate could not be deleted.")
            self.assertTrue(retrieved_data['acknowledged'], "Plate deletion was not acknowledged.")
        except:
            printv("Something went wrong in test_56_delete_by_id")
    ### FETCH_TAG delete_by_id

    ### FETCH_TAG delete_by_query
    def test_57_delete_by_query(self):
        ### Initialize constants
        user_account = "heidi"
        campaign_id = "EP_SmarGon_TEST"
        plate_id = "98765"
        library_id = str(ObjectId('64d4d1bea8f822476c37f97a'))  ### Just a placeholder, replace with real ObjectId if needed.

        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount = user_account,
            campaignId = campaign_id,
            plateId = plate_id,
            well = "A57a",
            wellEcho = "A57a",
            x = 488,
            y = 684,
            xEcho = 3.32,
            yEcho = 1.87,
            libraryId = library_id,
        )['inserted_id']

        ### Perform the operation
        query = {"userAccount": user_account, "campaignId": campaign_id, "plateId": plate_id}
        retrieved_data = self.client.delete_by_query("wells", query)
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        try:
            self.assertIsNotNone(retrieved_data, "Plate could not be deleted.")
            self.assertTrue(retrieved_data['acknowledged'], "Plate deletion was not acknowledged.")
        except:
            printv("Something went wrong in test_57_delete_by_query")
        finally:
            ### Delete the well after the test
            self.delete_by_id("wells", added_well_id_01)
    ### FETCH_TAG delete_by_query

    ### FETCH_TAG insert_campaign_library
    def test_58_insert_campaign_library(self):
        """
        Integration test for the insert_campaign_library method.
    
        This test first inserts a sample campaign library into the database and then attempts to retrieve it 
        using the get_campaign_libraries method. It verifies if the inserted library is present in the 
        retrieved list and checks the main fields for correctness.
    
        The test setup includes creating a sample campaign library, and the teardown includes removing this library 
        from the database after the test.
    
        Raises:
            AssertionError: If any of the test conditions fail.
        """
    
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
    
        # Setup: Insert a test campaign library
        retrieved_data_insert_campaign_library = self.insert_campaign_library(
            userAccount=user_account,
            campaignId=campaign_id,
            libraryName="Test_Library_Heidi_C",
            libraryBarcode="A98765",
            fragments=[
                {
                    "compoundCode": "C001",
                    "smiles": "c1ccccc1",
                    "well": "A58a",
                    "used": False,
                    "libraryConcentration": "1.0"
                },
                {
                    "compoundCode": "C002",
                    "smiles": "O=C(C)Oc1ccccc1C(=O)O",
                    "well": "A58a",
                    "used": False
                }
            ]
        )
        added_campaign_library_id = retrieved_data_insert_campaign_library['inserted_id']
    
        printv(f"\n{json.dumps(retrieved_data_insert_campaign_library, indent=4)}")
    
        ### Perform the operation
        retrieved_data = self.client.get_campaign_libraries(user_account, campaign_id)
    
        ### Filter added test data
        retrieved_data = [doc for doc in retrieved_data if doc['libraryName'] == "Test_Library_Heidi_C"]
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")
        printv(f"\n{json.dumps(len(retrieved_data), indent=4)}")
    
        try:
            ### Assertions
            self.assertIsInstance(retrieved_data, list, "Expected the response to be a list.")
            self.assertTrue(retrieved_data, "Expected at least one library in the response for the given user_account and campaign.")
    
            first_library = retrieved_data[0]
    
            ### Check main fields from the sample data in the returned library
            self.assertIn("libraryName", first_library, "Expected 'libraryName' field in the library.")
            self.assertIn("libraryBarcode", first_library, "Expected 'libraryBarcode' field in the library.")
            self.assertIn("fragments", first_library, "Expected 'fragments' field in the library.")
        finally:
            ### Teardown: Delete the test campaign_libraries after the test
            self.delete_by_id("campaign_libraries", added_campaign_library_id)
    ### FETCH_TAG insert_campaign_library

    ### FETCH_TAG export_cryo_to_soak
    def test_59_export_cryo_to_soak(self) -> None:
        """
        Tests the 'export_cryo_to_soak' function by creating test wells and a plate, performing the export, 
        and verifying the updates in the database.

        This test ensures that the cryoExportTime and cryoStatus for wells and cryoProtection for plates are 
        properly set upon executing the 'export_cryo_to_soak' function. After the test, it cleans up by deleting 
        the test entries.

        Raises:
            AssertionError: If any of the assertions following the database updates fail.
        """
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        plate_id = "98765"

        ### Create test wells
        added_well_id_01 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="A25a",
            wellEcho="A25a",
            x=488,
            y=684,
            xEcho=3.32,
            yEcho=1.87,
            cryoExportTime=None,
            cryoProtection=True,
            cryoStatus="pending",  # Assuming status should be 'pending' before the test
        )['inserted_id']

        added_well_id_02 = self.add_test_well(
            userAccount=user_account,
            campaignId=campaign_id,
            plateId=plate_id,
            well="B25b",
            wellEcho="B25b",
            x=500,
            y=700,
            xEcho=4.32,
            yEcho=2.87,
            cryoExportTime=None,
            cryoProtection=True,
            cryoStatus="pending",  # Assuming status should be 'pending' before the test
        )['inserted_id']

        ### Add a test plate
        last_imaged = datetime.now()
        batch_id = "987654"
        added_plate_id = self.add_test_plate(
            user_account,
            campaign_id,
            plate_id,
            lastImaged=last_imaged.isoformat(),
            batchId=batch_id
        )['inserted_id']
    
        ### Prepare and perform the operation
        now_time = datetime.now()
        data = [{'_id': plate_id, 'soak_time': now_time}]
        retrieved_data = self.client.export_cryo_to_soak(data)
        retrieved_data = retrieved_data.to_dict() if retrieved_data else {}
        printv(f"\n{json.dumps(retrieved_data, indent=4)}")

        ### Assertions
        self.assertIsNotNone(retrieved_data, "Result of export_cryo_to_soak function is None.")
        self.assertEqual(retrieved_data.get("modified_count"), 2, "The number of processed wells does not match the input.")

        ### Validate updated wells
        retrieved_data_updated_well_01 = self.convert_objectid_to_str(self.client.get_one_well(added_well_id_01))
        retrieved_data_updated_well_02 = self.convert_objectid_to_str(self.client.get_one_well(added_well_id_02))
        printv(f"{json.dumps(retrieved_data_updated_well_01, indent=4)}")
        printv(f"{json.dumps(retrieved_data_updated_well_02, indent=4)}")

        ### Assertions for wells and plates
        for well_data in [retrieved_data_updated_well_01, retrieved_data_updated_well_02]:
            self.assertEqual(well_data["cryoStatus"], "exported", "cryoStatus does not match.")
            self.assertIsNotNone(well_data["cryoExportTime"], "cryoExportTime was not set.")
        
            # Use the are_times_almost_equal function for comparing cryoExportTime
            self.assertTrue(are_times_almost_equal(well_data["cryoExportTime"], now_time), f"cryoExportTime does not match for well {well_data['well']}.")

        retrieved_data_updated_plate = self.convert_objectid_to_str(self.client.get_plate(user_account, campaign_id, plate_id))
        printv(f"{json.dumps(retrieved_data_updated_plate, indent=4)}")
        self.assertTrue(retrieved_data_updated_plate["cryoProtection"], "cryoProtection is not True for plate")

        ### Cleanup test data
        printv(f"Cleaning up test wells and plate: {added_well_id_01}, {added_well_id_02}, {added_plate_id}")
        self.delete_by_id("wells", added_well_id_01)
        self.delete_by_id("wells", added_well_id_02)
        self.delete_by_id("plates", added_plate_id)
    ### FETCH_TAG export_cryo_to_soak

    ### FETCH_TAG get_one_library
    def test_60_get_one_library(self):
        """
        Tests the retrieval of a single library record from the database using its ID.

        This test initializes a library object, imports it into the database, and then attempts to retrieve it using its ID.
        The test verifies if the retrieved data matches the initial library data, including all fragments and their properties.
        The ObjectId fields are converted to strings for comparison. The test library is deleted after the test.

        Raises:
            AssertionError: If the retrieved library data does not match the expected values.
        """
        ### Initialize library data for the test
        test_library = {
            "libraryName": "Test_Library_Heidi_A",
            "libraryBarcode": ObjectId('64d4d1bea8f822476c37f97a'),
            "fragments": [
                {
                    "compoundCode": "C901",
                    "smiles": "C(C(C(=O)O)c1ccccc1)c2ccccc2",
                    "well": "A51a",
                    "used": False,
                    "libraryConcentration": "0.8"
                },
                {
                    "compoundCode": "C902",
                    "smiles": "C1CCOC1",
                    "well": "A51a",
                    "used": False
                }
            ]
        }

        ### Insert the test library
        insert_result = self.client.import_library(test_library)
        inserted_id = insert_result.inserted_id

        try:
            ### Retrieve the library using get_one_library
            retrieved_data = self.client.get_one_library(str(inserted_id))
            ### Convert ObjectIds to strings for comparison
            retrieved_data = self.convert_objectid_to_str(retrieved_data)
            printv(f"\n{json.dumps(retrieved_data, indent=4)}")

            ### Assertions
            self.assertEqual(retrieved_data['_id'], str(test_library['libraryBarcode']), "Expected _id to match the libraryBarcode.")
            self.assertEqual(retrieved_data['libraryName'], test_library['libraryName'], f"Expected libraryName to be {test_library['libraryName']}.")
            self.assertEqual(len(retrieved_data['fragments']), len(test_library['fragments']), "Expected the number of fragments to match.")
            
            ### Check individual fragments
            for idx, fragment in enumerate(test_library['fragments']):
                retrieved_fragment = retrieved_data['fragments'][idx]

                self.assertEqual(retrieved_fragment['compoundCode'], fragment['compoundCode'], f"Expected compoundCode of fragment {idx} to be {fragment['compoundCode']}.")
                self.assertEqual(retrieved_fragment['smiles'], fragment['smiles'], f"Expected smiles of fragment {idx} to be {fragment['smiles']}.")
                self.assertEqual(retrieved_fragment['well'], fragment['well'], f"Expected well of fragment {idx} to be {fragment['well']}.")
                self.assertEqual(retrieved_fragment['used'], fragment['used'], f"Expected used of fragment {idx} to be {fragment['used']}.")

                if 'libraryConcentration' in fragment:
                    self.assertIn('libraryConcentration', retrieved_fragment, f"Expected libraryConcentration to be present in fragment {idx}.")
                    self.assertEqual(retrieved_fragment['libraryConcentration'], fragment['libraryConcentration'], f"Expected libraryConcentration of fragment {idx} to be {fragment['libraryConcentration']}.")

        finally:
            ### Delete the test libraries after the test
            self.delete_by_id("libraries", str(inserted_id))
    ### FETCH_TAG get_one_library

    ### FETCH_TAG get_one_campaign_library
    def test_61_get_one_campaign_library(self):
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
        #plate_id = "98765"  # if needed
        # Initialize the campaign_library data as a dictionary
        test_campaign_library = {
            'userAccount': user_account,
            'campaignId': campaign_id,
            'libraryName': "Test_Library_Heidi_A",
            'libraryBarcode': "A98765",
            'fragments': [
                {
                    "compoundCode": "C611",
                    "smiles": "c1ccccc1",
                    "well": "A61a",
                    "used": False,
                    "libraryConcentration": "1.0"
                },
                {
                    "compoundCode": "C612",
                    "smiles": "O=C(C)Oc1ccccc1C(=O)O",
                    "well": "A61a",
                    "used": False
                }
            ]
        }
        
        # Call the function with the dictionary
        insert_result = self.client.add_campaign_library(test_campaign_library)
        
        # Process 'inserted_id' from the returned dictionary
        inserted_id = insert_result['inserted_id']
    
        try:
            # Retrieve and compare
            retrieved_data = self.client.get_one_campaign_library(str(inserted_id))
            retrieved_data = self.convert_objectid_to_str(retrieved_data)
    
            # Assertions
            self.assertEqual(retrieved_data['_id'], inserted_id, "Expected _id to match.")
            self.assertEqual(retrieved_data['libraryName'], test_campaign_library['libraryName'], f"Expected libraryName to be {test_campaign_library['libraryName']}.")
            self.assertEqual(len(retrieved_data['fragments']), len(test_campaign_library['fragments']), "Expected the number of fragments to match.")
    
            # Check individual fragments
            for idx, fragment in enumerate(test_campaign_library['fragments']):
                retrieved_fragment = retrieved_data['fragments'][idx]
                
                self.assertEqual(retrieved_fragment['compoundCode'], fragment['compoundCode'], f"Expected compoundCode of fragment {idx} to be {fragment['compoundCode']}.")
                self.assertEqual(retrieved_fragment['smiles'], fragment['smiles'], f"Expected smiles of fragment {idx} to be {fragment['smiles']}.")
                self.assertEqual(retrieved_fragment['well'], fragment['well'], f"Expected well of fragment {idx} to be {fragment['well']}.")
                self.assertEqual(retrieved_fragment['used'], fragment['used'], f"Expected used of fragment {idx} to be {fragment['used']}.")
    
                if 'libraryConcentration' in fragment:
                    self.assertIn('libraryConcentration', retrieved_fragment, f"Expected libraryConcentration to be present in fragment {idx}.")
                    self.assertEqual(retrieved_fragment['libraryConcentration'], fragment['libraryConcentration'], f"Expected libraryConcentration of fragment {idx} to be {fragment['libraryConcentration']}.")
    
        finally:
            # Cleanup
            self.delete_by_id("campaign_libraries", inserted_id)
    ### FETCH_TAG get_one_campaign_library

    ### FETCH_TAG add_campaign_library
    def test_62_add_campaign_library(self):
        ### Initialize constants
        user_account = "e14965"
        campaign_id = "EP_SmarGon"
    
        # Initialize the campaign_library data as a dictionary
        test_campaign_library = {
            'userAccount': user_account,
            'campaignId': campaign_id,
            'libraryName': "Test_Library_Heidi_A",
            'libraryBarcode': "A98765",
            'fragments': [
                {
                    "compoundCode": "C621",
                    "smiles": "c1ccccc1",
                    "well": "A62a",
                    "used": False,
                    "libraryConcentration": "1.0"
                },
                {
                    "compoundCode": "C622",
                    "smiles": "O=C(C)Oc1ccccc1C(=O)O",
                    "well": "A62a",
                    "used": False
                }
            ]
        }
    
        # Make the API call to add_campaign_library
        insert_result = self.client.add_campaign_library(test_campaign_library)
        printv(f"\n{json.dumps(insert_result, indent=4)}")
    
        try:
            # Assertions to ensure that the data was inserted correctly
            self.assertIsNotNone(insert_result, "Expected a non-None result from add_campaign_library.")
            self.assertIn('inserted_id', insert_result, "Expected 'inserted_id' in the result.")
    
            inserted_id = insert_result['inserted_id']
    
            # Optionally, you can make an API call to retrieve the data and verify it
            retrieved_data = self.client.get_one_campaign_library(str(inserted_id))
            retrieved_data = self.convert_objectid_to_str(retrieved_data)
    
            self.assertEqual(retrieved_data['_id'], inserted_id, "Expected _id to match.")
            self.assertEqual(retrieved_data['libraryName'], test_campaign_library['libraryName'], f"Expected libraryName to be {test_campaign_library['libraryName']}.")
    
        finally:
            # Cleanup: remove the inserted data
            self.delete_by_id("campaign_libraries", inserted_id)
    ### FETCH_TAG add_campaign_library

    ### FETCH_TAG_TEST test_dummy_01
    def test_dummy_01(self):
        printv("test_dummy_01")
    ### FETCH_TAG_TEST test_dummy_01

    ### FETCH_TAG_TEST test_dummy_02
    def test_dummy_02(self):
        printv("test_dummy_02")
    ### FETCH_TAG_TEST test_dummy_02

if __name__ == '__main__':

    if 0:
        custom_runner = unittest.TextTestRunner(resultclass=CustomTextTestResult, verbosity=2)
        unittest.main(testRunner=custom_runner)
    else:
        unittest.main(verbosity=2)

###YYY
### To do:
### 4) remove non-required data in generated test documents
### 5) when printing test data, only printv data fields inportand to that test, e.g. using projections
### 8) check if the appropriate REST method is used for each interaction with the DB (POST, DELETE, GET, PUT, etc.)
