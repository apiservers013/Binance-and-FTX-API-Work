import glob, os
from datetime import datetime
from datetime import timedelta

import ftx
import pandas as pd
import requests
import threading
import time
import ta
import math
import operator

import urllib3


def log_to_results(str_to_log):
    fr = open("results.txt", "a")
    fr.write(str_to_log + "\n")
    fr.close()


def log_to_errors(str_to_log):
    fr = open("errors.txt", "a")
    fr.write(str_to_log + "\n")
    fr.close()


def log_to_trades(str_to_log):
    fr = open("trades.txt", "a")
    fr.write(str_to_log + "\n")
    fr.close()


def log_to_evol(str_to_log):
    fr = open("evol.txt", "a")
    fr.write(str_to_log + "\n")
    fr.close()


def log_to_debug(str_to_log):
    fr = open("debug.txt", "a")
    fr.write(str_to_log + "\n")
    fr.close()


def log_to_file(str_file, str_to_log):
    fr = open(str_file, "a")
    fr.write(str_to_log + "\n")
    fr.close()


# import numpy as npfrom binance.client import Client

ftx_client = ftx.FtxClient(
    api_key='',
    api_secret='',
    subaccount_name=''
)

# result = client.get_balances()
# print(result)

if os.path.exists("results.txt"):
    os.remove("results.txt")

if os.path.exists("errors.txt"):
    os.remove("errors.txt")

if os.path.exists("trades.txt"):
    os.remove("trades.txt")

if os.path.exists("evol.txt"):
    os.remove("evol.txt")

for fg in glob.glob("CS_*.txt"):
    os.remove(fg)

for fg in glob.glob("scan_*.txt"):
    os.remove(fg)

for fg in glob.glob("debug.txt"):
    os.remove(fg)

list_results = []
results_count = 0

stop_thread = False

dic_evol = {}
dic_timestamp = {}
dic_last_price = {}
num_req = 0

best_hourly_evol = []
best_minute_evol = []


def scan_one(symbol):
    global num_req
    # print("scan one : " + symbol)

    resolution = 60 * 60 * 24  # set the resolution of one japanese candlestick here
    nb_candlesticks = 5000  # 24 * 5  # set the number of backward japanese candlesticks to retrieve from FTX api
    delta_time = resolution * nb_candlesticks

    nb_iterations = int(nb_candlesticks / 5000)
    reste = nb_candlesticks % 5000
    print("nb iterations = " + str(nb_iterations))
    print("reste = " + str(reste))
    print(str(nb_candlesticks) + " modulo 5000 = " + str(nb_candlesticks % 5000))

    # while not stop_thread:
    list_results.clear()

    unixtime_endtime = time.time()
    converted_endtime = datetime.utcfromtimestamp(unixtime_endtime)
    print("current unix time = " + str(unixtime_endtime))
    print("converted_endtime = " + str(converted_endtime))
    tosubtract = 60 * 60 * 24 * 5000
    print("to substract in seconds = " + str(tosubtract))
    newunixtime_starttime = unixtime_endtime - tosubtract
    converted_starttime = datetime.utcfromtimestamp(newunixtime_starttime)
    print("new unix time = " + str(newunixtime_starttime))
    print("new converted_endtime = " + str(converted_starttime))

    data = []

    data2 = ftx_client.get_historical_data(
        market_name=symbol,
        resolution=resolution,
        limit=1000000,
        start_time=newunixtime_starttime,
        end_time=unixtime_endtime)

    data.extend(data2)

    data.sort(key=lambda x: pd.to_datetime(x['startTime']))

    symbol_filename = "scan_" + str.replace(symbol, "-", "_").replace("/", "_") + ".txt"
    for oneline in data:
        log_to_file(symbol_filename, str(oneline))

    dframe = pd.DataFrame(data)

    dframe.reindex(index=dframe.index[::-1])


threads = []


def main_thread(name):
    global ftx_client, list_results, results_count, num_req, stop_thread

    # while not stop_thread:

    markets = requests.get('https://ftx.com/api/markets').json()
    df = pd.DataFrame(markets['result'])
    df.set_index('name')

    for index, row in df.iterrows():
        symbol = row['name']
        symbol_type = row['type']

        # filter for specific symbols here
        # if not symbol == "ETH/USD":
        #     continue

        try:
            t = threading.Thread(target=scan_one, args=(symbol,))
            threads.append(t)
            t.start()
        except requests.exceptions.ConnectionError:
            continue

    for tt in threads:
        tt.join()

    print(str(datetime.now()) + " All threads started.")
    log_to_results(str(datetime.now()) + " All threads started.")

    print(str(datetime.now()) + " All threads finished.")
    log_to_results(str(datetime.now()) + " All threads finished.")

    time.sleep(1)

    stop_thread = True


x = threading.Thread(target=main_thread, args=(1,))
x.start()
