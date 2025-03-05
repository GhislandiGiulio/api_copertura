import requests
from requests.auth import HTTPBasicAuth
import dotenv
import os
from pandas import json_normalize
import ssl
from urllib3 import PoolManager
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

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

dotenv.load_dotenv()

USERNAME = os.environ["API_USERNAME"]
PASSWORD = os.environ["API_PASSWORD"]

BASE_URL = "https://reseller.twt.it/api/xdsl/toponomastica"

def __get_city_egon(city_name):
    """Retrieve the Egon code for a city."""
    try:
        response = session.get(f"{BASE_URL}/GetCities?query={city_name}", auth=HTTPBasicAuth(USERNAME, PASSWORD))
    except Exception as e:
        print(e)
        return None
    
    if response.status_code == 200 and response.json()["Body"] != []:
        return response.json()["Body"][0]["IdCity"]  # Get first matching city ID
    return None

def __get_address_egon(city_egon, address):
    """Retrieve the Egon code for an address in a given city."""
    try:
        response = session.get(f"{BASE_URL}/GetAddressesByCity?query={address}&cityId={city_egon}", auth=HTTPBasicAuth(USERNAME, PASSWORD))
    except Exception as e:
        print(e)
        return None
    
    if response.status_code == 200 and response.json()["Body"] != []:
        return response.json()["Body"][0]["CodiceEgon"]
    return None

def __get_headers(city, province, street, address, number):
    """Retrieve headers for a specific address."""
    try:
        response = session.get(
            f"{BASE_URL}/GetHeaders?city={city}&province={province}&street={street}&address={address}&number={number}",
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
        )
    except Exception as e:
        print(e)
        return None
    
    if response.status_code == 200 and response.json()["Body"] != None:
        header_ids = [elem["IdHeader"] for elem in response.json()["Body"]]
        main_egon = response.json()["Body"][0]["CodiceEgon"]
        return header_ids, main_egon
    return None

def __get_coverage(headers_id, city_egon, address_egon, main_egon, street_number):
    """Retrieve coverage details for an address."""
    url = (
        f"{BASE_URL}/GetCoverageServices?HeadersId={headers_id}&CityEgon={city_egon}"
        f"&AddressEgon={address_egon}&MainEgon={main_egon}&StreetNumber={street_number}&Rule=1"
    )
    try:
        response = session.get(url, auth=HTTPBasicAuth(USERNAME, PASSWORD))
    except Exception as e:
        print(e)
        return None
    
    if response.status_code == 200 and response.json()["Body"] is not None:
        return response.json()
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

def search(city_name, address, street, province, number):
    
    city_egon = __get_city_egon(city_name)
    if not city_egon:
        print("No Egon code found for the city.")
        return

    address_egon = __get_address_egon(city_egon, address)
    if not address_egon:
        print("No Egon code found for the address.")
        return

    headers = __get_headers(city_name, province, street, address, number)
    if not headers:
        print("No headers found for the address.")
        return
    
    header_ids, main_egon = headers

    coverage = __get_coverage(header_ids, city_egon, address_egon, main_egon, number)

    availability_reports_json = __extract_reports(coverage)
    
    if availability_reports_json == []:
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