import requests
from requests.auth import HTTPBasicAuth
import os
from pandas import json_normalize
import ssl
from urllib3 import PoolManager
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import certifi
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class TLSAdapter(HTTPAdapter):
    """Custom adapter to force TLS 1.2 and lower security level."""
    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context or create_urllib3_context()
        self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2  # Force TLS 1.2
        self.ssl_context.set_ciphers("DEFAULT@SECLEVEL=1")  # Lower security level
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)

# Create a session and mount the adapter
session = requests.Session()
session.mount("https://", TLSAdapter())

USERNAME = os.environ["API_USERNAME"]
PASSWORD = os.environ["API_PASSWORD"]

BASE_URL = "https://reseller.twt.it/api/xdsl/toponomastica"

def __get_city_egon_and_province(city_name):
    """Retrieve the Egon code for a city."""
    logger.info(f"Getting Egon code for city: {city_name}")
    
    try:
        response = session.get(f"{BASE_URL}/GetCities?query={city_name}", auth=HTTPBasicAuth(USERNAME, PASSWORD), verify=certifi.where())
    except Exception as e:
        logger.error(f"Error fetching city Egon code: {e}")
        return None
    
    if response.status_code == 200 and response.json()["Body"] != []:
    
        logging.info(f"Found city EGON for {city_name}")
        return response.json()["Body"][0]["IdCity"], response.json()["Body"][0]["Province"]
    
    logger.warning(f"No city found for {city_name}, error {response.status_code}")
    return None

def __get_address_egon(city_egon, address):
    """Retrieve the Egon code for an address in a given city."""
    logger.info(f"Getting Egon code for address: {address}")
    
    try:
        response = session.get(f"{BASE_URL}/GetAddressesByCity?query={address}&cityId={city_egon}", auth=HTTPBasicAuth(USERNAME, PASSWORD), verify=certifi.where())
    except Exception as e:
        logger.error(f"Error fetching address Egon code: {e}")
        return None
    
    if response.status_code == 200 and response.json()["Body"] != []:
        
        logging.info(f"Found address EGON for {address}")
        return response.json()["Body"][0]["CodiceEgon"]
    
    logger.warning(f"No address found for {address} in city with Egon code {city_egon}")
    return None

def __get_headers(city, province, address, number):
    """Retrieve headers for a specific address."""
    logger.info(f"Getting headers for address: {address}")
    
    try:
        response = session.get(
            f"{BASE_URL}/GetHeaders?city={city}&province={province}&address={address}&number={number}",
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            verify=certifi.where()
        )
    except Exception as e:
        logger.error(f"Error fetching headers for {address}: {e}")
        return None
    
    if response.status_code == 200 and response.json()["Body"] != None:
        header_ids = [elem["IdHeader"] for elem in response.json()["Body"]]
        main_egon = response.json()["Body"][0]["CodiceEgon"]
        
        return header_ids, main_egon
    logger.warning(f"No headers found for address {address}")
    return None

def __get_coverage(headers_id, city_egon, address_egon, main_egon, street_number):
    """Retrieve coverage details for an address."""
    url = (
        f"{BASE_URL}/GetCoverageServices?HeadersId={headers_id}&CityEgon={city_egon}"
        f"&AddressEgon={address_egon}&MainEgon={main_egon}&StreetNumber={street_number}&Rule=1"
    )
    try:
        response = session.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD), verify=certifi.where())
    except Exception as e:
        logger.error(f"Error fetching coverage for address {address_egon}: {e}")
        return None
    
    if response.status_code == 200 and response.json()["Body"] is not None:

        return response.json()

    logger.warning(f"No coverage data for address {address_egon}")
    return None


def __extract_reports(coverage_data):
    return coverage_data['Body']['AvailabilityReports']

def __extract_provider(provider_list):
    if isinstance(provider_list, list) and provider_list:
        first_provider = provider_list[0]  # Check first provider
        if isinstance(first_provider, dict) and "CoverageDetails" in first_provider:
            coverage_details = first_provider["CoverageDetails"]
            if isinstance(coverage_details, list) and coverage_details:
                return coverage_details[0].get("Description", None)
    return None  # Return None if any part is missing

def search(city_name, address, number):
    
    logging.info("Starting search for city: %s, address: %s, number: %s", city_name, address, number)
    
    city_egon, province = __get_city_egon_and_province(city_name)
    if not city_egon:
        logger.warning("No Egon code found for the city.")
        return

    address_egon = __get_address_egon(city_egon, address)
    if not address_egon:
        logger.warning("No Egon code found for the address.")
        return

    headers = __get_headers(city_name, province, address, number)
    if not headers:
        logger.warning("No headers found for the address.")
        return
    
    header_ids, main_egon = headers

    coverage = __get_coverage(header_ids, city_egon, address_egon, main_egon, number)

    availability_reports_json = __extract_reports(coverage)
    
    if availability_reports_json == []:
        logger.info(f"No availability reports for {address}")
        return
    
    # Normalize the JSON data
    availability_reports_table = json_normalize(availability_reports_json)
    
    # remove any useless column
    selected_columns = ["MaxSpeed", "ServiceDescription", "FiberRange", "StatusCoverage"]
    
    availability_reports_table = availability_reports_table[selected_columns]
    
    availability_reports_table = availability_reports_table.rename(columns={
        "MaxSpeed": "Velocità Massima",
        "ServiceDescription": "Tipo di Servizio",
        "FiberRange": "Fascia",
        "StatusCoverage": "Stato"
    })
    
    availability_reports_table["Fascia"] = availability_reports_table["Fascia"].fillna("Sconosciuto")
    
    availability_reports_table["Stato"] = availability_reports_table["Stato"].map({
        True: "Attivo",
        False: "Non attivo"
    }).fillna("Sconosciuto")
    
    # extract provider name
    return availability_reports_table
