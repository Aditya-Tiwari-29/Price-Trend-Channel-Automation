from __future__ import print_function
import gate_api
from gate_api.exceptions import ApiException, GateApiException
from datetime import datetime
import time
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from matplotlib import pyplot

##read input.txt file which is the test file
file = open("input.txt",'r')
test = int(file.readline())  ## typecast str to int
bc = int(file.readline())    ## no. of threshold candles
print("Number of test cases:", test)
print("Channel Length: ", bc)


##function to return currency, interval, start date and end date in suitable format 
## for gate io api

def tickers(s):
    currency = s[0] + "_USDT"
    interval = s[1].strip()
    s[2] = s[2].strip()
    s[3] = s[3].strip()
    p = s[2].split("/")
    if(int(p[0])<10):
        p[0] = "0" + p[0]     
    if(int(p[1])<10):
        p[1] = "0" + p[1] 
    time_s = datetime.fromisoformat(p[2]+"-"+p[0]+"-"+p[1]+" 00:00:00")
    q = s[3].split("/")
    if(int(q[0])<10):
        q[0] = "0" + q[0]  
    if(int(q[1])<10):
        q[1] = "0" + q[1] 
    time_e = datetime.fromisoformat(q[2]+"-"+q[0]+"-"+q[1]+" 00:00:00")
    start = int(time.mktime(time_s.timetuple()))
    end = int(time.mktime(time_e.timetuple()))
    return currency,interval,start,end
    
##returns crypto open, high, low and close proces of the timestamps of the currency in a list
def get_crypto_data(currency,interval,start,end):
    
    # Defining the host is optional and defaults to https://api.gateio.ws/api/v4
    # See configuration.py for a list of all supported configuration parameters.
    configuration = gate_api.Configuration(
        host = "https://api.gateio.ws/api/v4"
    )
    api_client = gate_api.ApiClient(configuration)
    # Create an instance of the API class
    api_instance = gate_api.SpotApi(api_client)
    currency_pair = currency # str | Currency pair
    limit = 100 # int | Maximum recent data points to return. `limit` is conflicted with `from` and `to`. If either `from` or `to` is specified, request will be rejected. (optional) (default to 100)
    _from = start # int | Start time of candlesticks, formatted in Unix timestamp in seconds. Default to`to - 100 * interval` if not specified (optional)
    to = end # int | End time of candlesticks, formatted in Unix timestamp in seconds. Default to current time (optional)
    interval = interval # str | Interval time between data points (optional) (default to '30m')

    try:
        # Market candlesticks
        api_response = api_instance.list_candlesticks(currency_pair, limit=limit, _from=_from, to=to, interval=interval)
        return api_response
    except GateApiException as ex:
        print("Gate api exception, label: %s, message: %s\n" % (ex.label, ex.message))
    except ApiException as e:
        print("Exception when calling SpotApi->list_candlesticks: %s\n" % e)

for t in range(test):
    ## read the currecny
    line = file.readline().strip()    
    line = line.split(",")
    print(line)
    
    ## get currency in processed form for gate io api
    currency,interval,start,end = tickers(line)
    api_response = get_crypto_data(currency,interval,start,end)
    print(len(api_response))
    
    ## pandas dataframe for better and convinient analysis
    df = pd.DataFrame(api_response,columns = ['timestamp','volume','open','high','low','close'])
    columns = ['timestamp','open','high','low','close','volume']
    df = df.reindex(columns = columns)
    
    ## conversion to numeric type from str type
    df['timestamp'] = pd.to_datetime(df['timestamp'],unit = 's')
    df['open'] = pd.to_numeric(df['open'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['close'] = pd.to_numeric(df['close'])
    df['volume'] = pd.to_numeric(df['volume'])
    print(df.head())
    
    ## plot the candlesticks
    fig = go.Figure(data = [go.Candlestick(x=df.index,
                open = df['open'],
                high = df['high'],
                low  = df['low'],
                close = df['close'])])
    fig.show()
    
    
    backcandles = bc   ## candles that we want to channel back from a candleid 
    brange = int(bc*0.2)      ## dynamic , the user can input any range 
    wind = 5         ## dynamic , the user can input any window range

    candleid = 400      ## we can test for different values of candleid to get different channels in different intervals
    
    ## we can play with the values of backcandles, brange, wind and candleid to get different channels 
    ## and choose which suits best according to the data and range and threshold no. of channels , etc
    
    ## optimal number of backcandles for best possible channel in an interval
    optbackcandles = backcandles
    sldiff = 1000     ## slope difference between twi lines , should be initialized large  
    sldist = 10000    ## distance between the to lines, should be initialized large  
    
    ## optimized algorithm to find lines that are parallel and cover most candles inside them for a smooth channel
    for r1 in range(backcandles-brange,backcandles+brange):
        maxim = np.array([])     ## stores maximum high in a given window
        minim = np.array([])      ## stores minimum low in a given window
        xxmin = np.array([])      ## stores INDEX OF minimum low in a given window
        xxmax = np.array([])      ## stores INDEX OF maximum high in a given window
        
        ## iterate through windows and get the minim and maxim with their indexes and append to the lists
        
        for i in range(candleid-r1,candleid+1,wind):
            minim = np.append(minim,df.low.iloc[i:i+wind].min())
            xxmin = np.append(xxmin,df.low.iloc[i:i+wind].idxmin())
            
        for i in range(candleid-r1,candleid+1,wind):
            maxim = np.append(maxim,df.high.iloc[i:i+wind].max())
            xxmax = np.append(xxmax,df.high.iloc[i:i+wind].idxmax())
            
        ## fit a best fit linear polynomial throgh the points of maxim and minim
        slmin,intercmin = np.polyfit(xxmin,minim,1)
        slmax,intercmax = np.polyfit(xxmax,maxim,1)
        
        ## distance between the two lines
        dist = (slmax*candleid + intercmax)-(slmin*candleid + intercmin)
        
        ## updation of variables for optimization 
        if(dist<sldist):
            sldist = dist
            optbackcandles = r1
            slminopt = slmin
            slmaxopt = slmax
            intercminopt = intercmin 
            intercmaxopt = intercmax
            maximopt = maxim.copy()
            minimopt = minim.copy()
            xxminopt = xxmin.copy()
            xxmaxopt = xxmax.copy()

    print("optimised channel length(value will be near the threshold): " ,optbackcandles)
    
    ## plot the candlestics part where we wanted the channel
    dfpl = df[candleid-wind-optbackcandles-backcandles:candleid+optbackcandles]  
    fig = go.Figure(data=[go.Candlestick(x=dfpl.index,
                    open=dfpl['open'],
                    high=dfpl['high'],
                    low=dfpl['low'],
                    close=dfpl['close'])])
    ## update  intercept so that the line goes through the lowest low
    ## and highest high in the range , so that candlesticks are included indide the 
    ## two lines
    adjintercmax = (df.high.iloc[xxmaxopt] - slmaxopt*xxmaxopt).max()
    adjintercmin = (df.low.iloc[xxminopt] - slminopt*xxminopt).min()    

    print("slope min= ",slminopt)
    print("intercept min = ",adjintercmin)
    print("slope max = ",slmaxopt)
    print("intercept max = ",adjintercmax)
    print(" ")


    ## add the two lines to the plot
    fig.add_trace(go.Scatter(x=xxminopt, y=slminopt*xxminopt + adjintercmin, mode='lines', name='min slope'))
    fig.add_trace(go.Scatter(x=xxmaxopt, y=slmaxopt*xxmaxopt + adjintercmax, mode='lines', name='max slope'))
    fig.show()
    