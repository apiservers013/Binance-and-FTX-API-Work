# Number of threads running simultaneously is controlled with the variable maxthreads :)

import glob
import operator
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta

import ftx
import pandas
import pandas as pd
import requests

import_to_database = False  # only works with maxthreads = 1 (will be if import_to_database = True) or for one (of very few) symbol (filter symbols in the main_thread
delete_db_at_startup = True  # delete previously created db file(s)
create_one_db_file_per_symbol = True
max_block_of_5000_download = 1  # set to -1 for unlimited blocks (all data history)
log_data_history_to_files = False  # This option is for logging data history to one file per symbol (eg. scan_ETH_USD.txt)
# log_scan_results_to_files = True  # This option if for logging the scan results to one file per symbol (at the bottom of eg. scan_ETH_USD.txt)
maxthreads = 1000

if import_to_database and not create_one_db_file_per_symbol:
    maxthreads = 1
    print("maxthread forced to " + str(maxthreads) + " because of import_to_database is active")


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

if import_to_database:
    if delete_db_at_startup:
        for fg in glob.glob("data_history.db"):
            os.remove(fg)

for fg in glob.glob("data_history_*.db"):
    os.remove(fg)

stop_thread = False

evol_results = {}
asset_last_price = {}

df_btc = pandas.DataFrame()  # todo : change the df_btc name with df_ref_symbol


def execute_code(symbol):
    global log_data_history_to_files, df_btc
    # print("scan one : " + symbol)

    resolution = 60 * 60 * 1  # set the resolution of one japanese candlestick here
    timeframe = "M1"  # used for inserting into SQLITE database

    symbol_filename = "scan_" + str.replace(symbol, "-", "_").replace("/", "_") + ".txt"

    unixtime_endtime = time.time()
    converted_endtime = datetime.utcfromtimestamp(unixtime_endtime)
    # print("current unix time = " + str(unixtime_endtime))
    # print("converted_endtime = " + str(converted_endtime))
    tosubtract = resolution * 5000  # 60 * 60 * 1 * 5000
    # print("to substract in seconds = " + str(tosubtract))
    newunixtime_starttime = unixtime_endtime - tosubtract
    converted_starttime = datetime.utcfromtimestamp(newunixtime_starttime)
    # print("new unix time = " + str(newunixtime_starttime))
    # print("new converted_starttime = " + str(converted_starttime))

    data = []

    end_of_data_reached = False

    current_block_of_5000_download = 0
    max_block_of_5000_download_reached = False

    force_start_time_of_data_to_download = False
    forced_end_time = datetime.now().timestamp()
    forced_start_time = (datetime.now() - timedelta(days=60)).timestamp()

    while not end_of_data_reached and not max_block_of_5000_download_reached:

        if not force_start_time_of_data_to_download:
            downloaded_data = ftx_client.get_historical_data(
                market_name=symbol,
                resolution=resolution,
                limit=1000000,
                start_time=newunixtime_starttime,
                end_time=unixtime_endtime)
        else:
            downloaded_data = ftx_client.get_historical_data(
                market_name=symbol,
                resolution=resolution,
                limit=1000000,
                start_time=forced_start_time,
                end_time=forced_end_time)

        converted_endtime = datetime.utcfromtimestamp(unixtime_endtime)
        converted_starttime = datetime.utcfromtimestamp(newunixtime_starttime)

        # print(symbol + " : downloaded_data size = " + str(len(downloaded_data)) + " from " + str(converted_starttime) + " to " + str(converted_endtime))
        data.extend(downloaded_data)

        unixtime_endtime = newunixtime_starttime
        newunixtime_starttime = newunixtime_starttime - tosubtract

        if len(downloaded_data) == 0:
            print(symbol + " : end of data from server reached")
            end_of_data_reached = True

        if max_block_of_5000_download != -1:
            current_block_of_5000_download += 1
            if current_block_of_5000_download >= max_block_of_5000_download:
                # print(symbol + " : max number of block of 5000 reached")
                max_block_of_5000_download_reached = True

        if force_start_time_of_data_to_download:
            end_of_data_reached = True  # doit être calculé car il faut voir si la plage de dates forcée dépasse les blocs de 5000 données
            print("Stopping downloading because start time and end time were forced")

    df = pd.DataFrame(data)
    df = df.sort_values(by='startTime')
    df = df.iloc[::-1]

    if symbol == "BTC/USD":
        df_btc = df

    # log_to_results(str(df['close'].iloc[0]))
    # log_to_results(str(df['close'].iloc[1]))
    evol = 100 * (df['close'].iloc[0] - df['close'].iloc[1]) / (df['close'].iloc[1])
    evol_results[symbol] = evol
    asset_last_price[symbol] = df['close'].iloc[0]

    nb_candlesticks_to_test = 15
    nb_correlated = 0

    for i in range(1, nb_candlesticks_to_test + 1):

        obtc = df_btc["open"].iloc[i]
        hbtc = df_btc["high"].iloc[i]
        lbtc = df_btc["low"].iloc[i]
        cbtc = df_btc["close"].iloc[i]

        try:
            o = df["open"].iloc[i]
            h = df["high"].iloc[i]
            l = df["low"].iloc[i]
            c = df["close"].iloc[i]
        except IndexError:
            print(symbol + " exception")
            continue

        if cbtc > obtc and c > o:
            nb_correlated += 1

        if cbtc < obtc and c < o:
            nb_correlated += 1

    if nb_correlated == nb_candlesticks_to_test:
        log_to_results(symbol + " is correlated to btc on " + str(nb_correlated) + " japanese candlesticks")


# maxthreads = 5
threadLimiter = threading.BoundedSemaphore(maxthreads)


def scan_one(symbol):
    threadLimiter.acquire()
    try:
        execute_code(symbol)
    finally:
        threadLimiter.release()


threads = []


def main_thread(name):
    global ftx_client, list_results, results_count, num_req, stop_thread

    # print(str(datetime.now()) + " All threads starting.")
    # log_to_results(str(datetime.now()) + " All threads starting.")

    markets = requests.get('https://ftx.com/api/markets').json()
    df = pd.DataFrame(markets['result'])
    df.set_index('name')

    ref_symbol = "BTC/USD"
    z = threading.Thread(target=scan_one, args=(ref_symbol,))
    z.start()
    z.join()

    for index, row in df.iterrows():
        symbol = row['name']
        # symbol_type = row['type']
        vol = row['volumeUsd24h']
        change24h = row['change24h']
        change1h = row['change1h']

        if symbol == ref_symbol:
            continue

        # if not change1h > 0:
        #     continue

        # filter for specific symbols here
        # if not symbol == "FTM/USD":
        #     continue

        # if not symbol.endswith("/USD"):
        #     continue

        try:
            t = threading.Thread(target=scan_one, args=(symbol,))
            threads.append(t)
            t.start()
        except requests.exceptions.ConnectionError:
            continue

    for tt in threads:
        tt.join()

    # print(str(datetime.now()) + " All threads finished.")
    # log_to_results(str(datetime.now()) + " All threads finished.")

    sorted_d = sorted(evol_results.items(), key=operator.itemgetter(1), reverse=True)
    for line in sorted_d:
        print(line[0], line[1], "%", "last price =", str(asset_last_price[line[0]]))
        log_to_results(line[0] + " " + str(round(line[1], 4)) + "% last price = " + ("{:10.8f}".format(asset_last_price[line[0]])))

    # time.sleep(1)
    print("end of processing")


x = threading.Thread(target=main_thread, args=(1,))
x.start()
