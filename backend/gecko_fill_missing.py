from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects 

import time
import pandas as pd
import json
import os
from dotenv import load_dotenv 

from utils.cmc_utils import *
from utils.db_utils import *

from psycopg2.extras import execute_values

load_dotenv()
gc_api_key = os.getenv('GECKO_API') 
cmc_api_key = os.getenv('CMC_API')  

def pull_coin_list_ranking(api_key):
    url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc"
    headers = {
    "accept": "application/json",
    "x-cg-pro-api-key": gc_api_key
    }

    session = Session()
    session.headers.update(headers)

    try:
      response = session.get(url)
      data = response.json()
      return data
    except (ConnectionError, Timeout, TooManyRedirects) as e:
      print(e)
      return -1
    
def pull_coin_mapping_gecko(api_key):
    url = "https://api.coingecko.com/api/v3/coins/list"
    headers = {
    "accept": "application/json",
    "x-cg-pro-api-key": gc_api_key
    }

    session = Session()
    session.headers.update(headers)

    try:
      response = session.get(url)
      data = response.json()
      return data
    except (ConnectionError, Timeout, TooManyRedirects) as e:
      print(e)
      return -1
    
'''Get top coin by mc'''
data = pull_coin_list_ranking(gc_api_key)
with open('./data/gecko_raw_data/mapping/top_symbol_by_mc.json', 'w') as file:
    json.dump(data, file, indent=4)



'''Get Id Symbol Mapping'''
data = pull_coin_mapping_gecko(gc_api_key)
with open('./data/gecko_raw_data/mapping/symbol_map.json', 'w') as file:
    json.dump(data, file, indent=4)

'''check what else to download'''
# Find current Binance data and Top 200 CMC coins. Download what we don't have.
  
with open('./data/gecko_raw_data/mapping/symbol_map.json', 'r') as file:
    mapping = json.load(file)

symbol_to_id = {item['symbol'].upper(): item['id'] for item in mapping}
id_to_symbol = {item['id']: item['symbol'].upper() for item in mapping}

bn_checkpoint = './data/checkpoints/binance_checkpoint.json'
with open(bn_checkpoint, 'r') as file:
    bn_downloaded_symbols = json.load(file)

bn_downloaded_symbols = [symbol.replace('USDT', '') for symbol in bn_downloaded_symbols]

data = pull_coin_list(200, cmc_api_key)
_, all_top_symbols= coin_list_json_to_array(data)

# cleaning
symbol_to_download = [symbol for symbol in all_top_symbols if symbol not in bn_downloaded_symbols]
symbol_to_download = [symbol for symbol in symbol_to_download if symbol not in ['USDT', "USDC", "NFT"]]
ids_to_download = [symbol_to_id[symbol.upper()] for symbol in symbol_to_download if symbol.upper() in symbol_to_id]

'''DOWNLOAD DATA'''
import requests
for id in ids_to_download:
    time.sleep(2) # limited api 
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{id}/market_chart?vs_currency=usd&days=360"

        headers = {"accept": "application/json",
                   "x-cg-pro-api-key": gc_api_key}

        response = requests.get(url, headers=headers)
        data = response.json()
        symbol = id_to_symbol[id]
        with open(f'./data/gecko_raw_data/{symbol}.json', 'w') as file:
          json.dump(data, file, indent=4)
        print(f'downloaded {symbol}.json')
    except (Exception) as e:
      print(f"fail download {symbol}: {e}")
      continue


# '''INSERT TO SQL DATABASE'''
# load_dotenv(override=True)
# DB_USERNAME = os.getenv('RDS_USERNAME') 
# DB_PASSWORD = os.getenv('RDS_PASSWORD') 
# DB_HOST = os.getenv('RDS_ENDPOINT') 
# DB_NAME = 'financial_data'

# conn = connect_to_db(DB_NAME, DB_HOST, DB_USERNAME, DB_PASSWORD)
    
# alt_json_folder = './data/gecko_raw_data'
# for filename in os.listdir(alt_json_folder):
#     if filename.endswith('.json'):
#         file_path = os.path.join(alt_json_folder, filename)
#         cursor = conn.cursor()
#         try:
#             with open(file_path, 'r') as file:
#                 data = json.load(file)
#                 symbol = os.path.splitext(os.path.basename(file_path))[0]
#                 symbol = symbol+'USDT'
#                 extracted_data = []
#                 for entry in data["prices"]:
#                     timestamp = entry[0]
#                     price = entry[1]
#                     # Convert timestamp to a readable date format
#                     date = pd.to_datetime(entry[0], unit='ms').strftime('%Y-%m-%d')
#                     # Append the transformed data to the list
#                     extracted_data.append([symbol, date, -1,-1,-1,price,-1])
#                 extracted_data = extracted_data[:-1]
                
#                 # Insert data into the database
#                 insert_query = """
#                 INSERT INTO coin_historical_price (symbol, date, open, high, low, close, volume)
#                 VALUES %s
#                 ON CONFLICT (symbol, date)
#                 DO UPDATE SET
#                     open = EXCLUDED.open,
#                     high = EXCLUDED.high,
#                     low = EXCLUDED.low,
#                     close = EXCLUDED.close,
#                     volume = EXCLUDED.volume
#                 """
#                 execute_values(cursor, insert_query, extracted_data)
#                 conn.commit()
#                 print(f'Inserted {symbol} historical price')
#         except Exception as e:
#             print(f"Failed to insert data from {filename}: {e}")
#             conn.rollback()
#         finally:
#             cursor.close()

    