# -*- coding: utf-8 -*-
"""
Created on Sun Feb 11 08:47:17 2018

@author: sonng
"""
from finance_util import symbol_to_path, get_info_stock, symbol_to_path_ssi
import numpy as np
import pandas as pd
import talib
import datetime



def ninja_trading(ticker, start, end, realtime = False, source = "cp68"):
       
    if source == "ssi":
        file_path = symbol_to_path_ssi(ticker)
        df = pd.read_csv(file_path, index_col ="DATE", parse_dates = True,  dayfirst=True,
                     usecols = ["DATE", "OPEN","CLOSE","HIGHEST","LOWEST","TOTAL VOLUMN"], na_values = "nan")
        df = df.rename(columns = {'DATE': 'Date', "OPEN": 'Open', 'HIGHEST': 'High',
                                  'LOWEST': 'Low','CLOSE' : 'Close', 'TOTAL VOLUMN': 'Volume'})
    else:
        file_path = symbol_to_path(ticker)
        df = pd.read_csv(file_path, index_col ="<DTYYYYMMDD>", parse_dates = True, 
                     usecols = ["<DTYYYYMMDD>", "<OpenFixed>","<HighFixed>","<LowFixed>","<CloseFixed>","<Volume>"], na_values = "nan")
        df = df.rename(columns = {'<DTYYYYMMDD>': 'Date', "<OpenFixed>": 'Open', '<HighFixed>': 'High',
                                  '<LowFixed>': 'Low','<CloseFixed>' : 'Close', '<Volume>': 'Volume'})
      
    # columns order for backtrader type
    columnsOrder=["Open","High","Low","Close", "Volume", "OpenInterest"]
    # change the index by new index
    df = df.reindex(columns = columnsOrder)  
    # change date index to increasing order
    df = df.sort_index()   
    # take a part of dataframe
    df = df.loc[start:end]
    
    if realtime:
        actual_price = get_info_stock(ticker)
        today = datetime.datetime.today()
        next_date = today
        df.loc[next_date] = ({ 'Open' : actual_price['Open'].iloc[-1],
                        'High' : actual_price['High'].iloc[-1], 
                        'Low' : actual_price['Low'].iloc[-1],
                        'Close' : actual_price['Close'].iloc[-1],
                        'Volume' : actual_price['Volume'].iloc[-1],
                        'OpenInterest': np.nan})
    
    df['R'] = (df['High'] - df['Low']) + 0.04
    df['Target_SELL'] = df['R']*3 + df['Close']
    df['Target_STOPLOSS'] = - df['R']*3 + df['Close']
    
    df['EMA3'] = pd.Series(pd.Series.ewm(df['Close'], span = 3, min_periods = 3-1).mean()) 
    df['EMA6'] = pd.Series(pd.Series.ewm(df['Close'], span = 6, min_periods = 6-1).mean()) 
    df['EMA18'] = pd.Series(pd.Series.ewm(df['Close'], span = 18,  min_periods = 18-1).mean()) 
    df['EMA50'] = pd.Series(pd.Series.ewm(df['Close'], span = 50,  min_periods = 50-1).mean()) 
    df['EMA100'] = pd.Series(pd.Series.ewm(df['Close'], span = 100,  min_periods = 100-1).mean())
    df['EMA200'] = pd.Series(pd.Series.ewm(df['Close'], span = 200,  min_periods = 200-1).mean())
    
#    macd, signal, hist = talib.MACD(df['Close'].values, fastperiod=12, slowperiod= 26, signalperiod=9)
#    MACD = pd.Series(macd,  index = df.index, name = 'MACD_12_26')     
#    #Signal line 9 EMA of EMA12- EMA26
#    MACDsign = pd.Series(signal,  index = df.index, name = 'MACDSign9')  
#    # Histo = diff from (EMA12-EMA26) - EMA9(EMA12- EMA26)
#    MACDdiff = pd.Series(hist,  index = df.index, name = 'MACDDiff')
    df['MFI'] = talib.MFI(df['High'].values, df['Low'].values,df['Close'].values, df['Volume'].values.astype(np.float64), timeperiod=14)
    
    n_fast = 12
    n_slow = 26
    nema = 9
    df['MACD_12_26'], df['MACDSign9'], df['MACDDiff'] = compute_MACD(df, n_fast, n_slow, nema)
          
    df['18_LONG']= (swing_high(df) & check_crossover(df, high = 'Close', low = 'EMA18'))    
#    & (df['Close'] > df['EMA18']) & (df['C_1d'] > df['EMA18_1d']) & (df['C_2d'] < df['EMA18_2d']))
    
    df['18_SHORT']= (swing_low(df)  & check_crossover(df, high = 'EMA18', low = 'Close')) 
#    & (df['Close'] < df['EMA18']) & (df['C_1d'] < df['EMA18_1d']) & (df['C_2d'] > df['EMA18_2d']))
       
    df['3_18_LONG']= (swing_high(df)  & check_crossover(df, high = 'EMA3', low = 'EMA18'))
#    & (df['EMA3'] > df['EMA18']) & (df['EMA3_1d'] > df['EMA18_1d']) & (df['EMA3_2d'] < df['EMA18_2d']))    
    
    df['3_18_SHORT']= (swing_low(df) & check_crossover(df, high = 'EMA18', low = 'EMA3'))
#    & (df['EMA3'] < df['EMA18']) & (df['EMA3_1d'] < df['EMA18_1d']) & (df['EMA3_2d'] > df['EMA18_2d']))    
    
    df['3_6_LONG']= (swing_high(df) & check_crossover(df, high = 'EMA3', low = 'EMA6'))
#    & (df['EMA3'] > df['EMA6']) & (df['EMA3_1d'] > df['EMA6_1d']) & (df['EMA3_2d'] < df['EMA6_2d']))
    
    df['3_6_SHORT']= (swing_low(df) & check_crossover(df, high = 'EMA6', low = 'EMA3'))
#    & (df['EMA3'] < df['EMA6']) & (df['EMA3_1d'] < df['EMA6_1d']) & (df['EMA3_2d'] > df['EMA6_2d']))    
    
    df['6_18_LONG']= (swing_high(df) & check_crossover(df, high = 'EMA6', low = 'EMA18'))
#    & (df['EMA6'] > df['EMA18']) & (df['EMA6_1d'] > df['EMA18_1d']) & (df['EMA6_2d'] < df['EMA18_2d']))
    
    df['6_18_SHORT']= (swing_low(df) & check_crossover(df, high = 'EMA18', low = 'EMA6'))
#    & (df['EMA6'] < df['EMA18']) & (df['EMA6_1d'] < df['EMA18_1d']) & (df['EMA6_2d'] > df['EMA18_2d']))        
    
    df['3_50_LONG']= (swing_high(df) & check_crossover(df, high = 'EMA3', low = 'EMA50'))
#    & (df['EMA3'] > df['EMA50']) & (df['EMA3_1d'] > df['EMA50_1d']) & (df['EMA3_2d'] < df['EMA50_2d']))
    
    df['3_50_SHORT']= (swing_low(df) & check_crossover(df, high = 'EMA50', low = 'EMA3'))
#    & (df['EMA3'] < df['EMA50']) & (df['EMA3_1d'] < df['EMA50_1d']) & (df['EMA3_2d'] > df['EMA50_2d']))
    
    df['6_50_LONG']= (swing_high(df) & check_crossover(df, high = 'EMA6', low = 'EMA50'))
#    & (df['EMA6'] > df['EMA50']) & (df['EMA6_1d'] > df['EMA50_1d']) & (df['EMA6_2d'] < df['EMA50_2d']))
  
    df['6_50_SHORT']= (swing_low(df)  & check_crossover(df, high = 'EMA50', low = 'EMA6'))
#    & (df['EMA6'] < df['EMA50']) & (df['EMA6_1d'] < df['EMA50_1d']) & (df['EMA6_2d'] > df['EMA50_2d']))
    
    df['18_50_LONG']= (swing_high(df) & check_crossover(df, high = 'EMA18', low = 'EMA50'))
#    & (df['EMA18'] > df['EMA50']) & (df['EMA18_1d'] > df['EMA50_1d']) & (df['EMA18_2d'] < df['EMA50_2d']))
    
    df['18_50_SHORT']= (swing_low(df) & check_crossover(df, high = 'EMA50', low = 'EMA18'))
#    & (df['EMA18'] < df['EMA50']) & (df['EMA18_1d'] < df['EMA50_1d']) & (df['EMA18_2d'] > df['EMA50_2d']))

    df['3_6_18_LONG']= (swing_high(df) & check_crossover(df, high = 'EMA3', low = 'EMA6')
        & check_crossover(df, high = 'Close', low = 'EMA18'))
#    
#    & (df['EMA3'] > df['EMA6']) & (df['EMA3_1d'] > df['EMA6_1d']) & (df['EMA3_2d'] < df['EMA6_2d'])
#    & (df['Close'] > df['EMA18']) & (df['C_1d'] > df['EMA18_1d']) & (df['C_2d'] < df['EMA18_2d']))
    
    df['3_6_18_SHORT']= (swing_low(df) & check_crossover(df, high = 'EMA6', low = 'EMA3')
        & check_crossover(df, high = 'EMA18', low = 'Close'))
#    & (df['EMA3'] < df['EMA6']) & (df['EMA3_1d'] < df['EMA6_1d']) & (df['EMA3_2d'] > df['EMA6_2d'])
#    & (df['Close'] < df['EMA18']) & (df['C_1d'] < df['EMA18_1d']) & (df['C_2d'] > df['EMA18_2d']))
    
    df['MACD_SIGNAL_LONG']= (swing_high(df) & check_crossover(df, high = 'MACD_12_26', low = 'MACDSign9'))
#    & (df['MACD_12_26'] > df['MACDSign9']) & (df['MACD_12_26_1d'] > df['MACDSign9_1d'])
#    & (df['MACD_12_26_2d'] < df['MACDSign9_2d']))
    
    df['MACD_SIGNAL_SHORT']= (swing_low(df) & check_crossover(df, high = 'MACDSign9', low = 'MACD_12_26'))
#    & (df['MACD_12_26'] < df['MACDSign9']) & (df['MACD_12_26_1d'] < df['MACDSign9_1d'])
#    & (df['MACD_12_26_2d'] > df['MACDSign9_2d']))
        
    
    df['MACD_ZERO_LONG']= (swing_high(df) & check_over_zero(df, column = 'MACD_12_26'))
#    & (df['MACD_12_26'] > 0) & (df['MACD_12_26_1d'] > 0) & (df['MACD_12_26_2d'] < 0))
    
    df['MACD_ZERO_SHORT']= (swing_low(df) & check_below_zero(df, column = 'MACD_12_26'))
#    & (df['MACD_12_26'] < 0) & (df['MACD_12_26_1d'] < 0) & (df['MACD_12_26_2d'] > 0))
    
    # CONTEXTUAL RISK
    df['EMA_UP'] = ((df['EMA18'] > df['EMA50']) & (df['EMA50'] > df['EMA100']) & (df['EMA100'] > df['EMA200']))
    df['EMA_DOWN'] = ((df['EMA18'] < df['EMA50']) & (df['EMA50'] < df['EMA100']) & (df['EMA100'] < df['EMA200']))
    # MOMENTUM
    df['MACD_UP'] = ((df['MACD_12_26'] > df['MACDSign9']))
    df['MACD_DOWN'] = ((df['MACD_12_26'] < df['MACDSign9']))
    
    
    df['L18'] = (df['18_LONG'] & df['MACD_UP'])
    df['L3_18'] = (df['3_18_LONG'] & df['MACD_UP'])
    df['L3_6'] = (df['3_6_LONG'] &  df['MACD_UP'])
    df['L6_18'] = (df['6_18_LONG'] &  df['MACD_UP'])
    df['L3_50'] = (df['3_50_LONG'] & df['MACD_UP'])
    df['L6_50'] = (df['6_50_LONG'] &  df['MACD_UP'])
    df['L18_50'] = (df['18_50_LONG'] &  df['MACD_UP'])
    df['L3_6_18'] = (df['3_6_18_LONG'] &  df['MACD_UP'])    
    df['L_MACD_SIGNAL']=  (df['MACD_SIGNAL_LONG'] &  df['MACD_UP'])
    df['L_MACD_ZERO']=  (df['MACD_ZERO_LONG'] &   df['MACD_UP'])
    
    
    df['S18'] = (df['18_SHORT'] &  df['MACD_DOWN'])
    df['S3_18'] = (df['3_18_SHORT'] & df['MACD_DOWN'])
    df['S3_6'] = (df['3_6_SHORT'] &  df['MACD_DOWN'])
    df['S6_18'] = (df['6_18_SHORT'] &  df['MACD_DOWN'])
    df['S3_50'] = (df['3_50_SHORT'] &  df['MACD_DOWN'])
    df['S6_50'] = (df['6_50_SHORT'] & df['MACD_DOWN'])
    df['S18_50'] = (df['18_50_SHORT'] &  df['MACD_DOWN'])
    df['S3_6_18'] = (df['3_6_18_SHORT'] &  df['MACD_DOWN'])    
    df['S_MACD_SIGNAL']=  (df['MACD_SIGNAL_SHORT'] &  df['MACD_DOWN'])
    df['S_MACD_ZERO']=  (df['MACD_ZERO_SHORT'] &  df['MACD_DOWN'])
    
    # 3 days checking: SH + 2 pullbacks
    hm_days = 5
    for i in range(1,hm_days+1):
        if (df['L18'].iloc[-i] | df['L3_18'].iloc[-i] | df['L3_6'].iloc[-i] 
            | df['L6_18'].iloc[-i] | df['L3_50'].iloc[-i]
            | df['L6_50'].iloc[-i] | df['L18_50'].iloc[-i] | df['L3_6_18'].iloc[-i] 
            | df['L_MACD_SIGNAL'].iloc[-i]
            | df['L_MACD_ZERO'].iloc[-i]):
            print(" Time for ninja trading ", str(i), " days before ", df.iloc[-i].name ,  ticker)
#            print(" Price at that day : ", df.iloc[-i][0:4])

            
    for i in range(1,hm_days+1):
     if ((df['L18'].iloc[-i] & check_bounce(df, ind = i, nema = 18))
        | (df['L3_18'].iloc[-i] & check_bounce(df, ind = i, nema = 18))
        | (df['L3_6'].iloc[-i] & check_bounce(df, ind = i, nema = 6))
        | (df['L6_18'].iloc[-i] & check_bounce(df, ind = i, nema = 18))
        | (df['L3_50'].iloc[-i] & check_bounce(df, ind = i, nema = 50))
        | (df['L6_50'].iloc[-i] & check_bounce(df, ind = i, nema = 50))
        | (df['L18_50'].iloc[-i] & check_bounce(df, ind = i, nema = 50))
        | (df['L3_6_18'].iloc[-i] & check_bounce(df, ind = i, nema = 18))):
            print(" Advanced ninja trading ", str(i), " days before ", df.iloc[-i].name ,  ticker)
       
    df['Signal'] = 1*(df['L18'] | df['L3_18'] | df['L3_6'] | df['L6_18'] | df['L3_50'] | df['L6_50'] | df['L18_50'] |  df['L3_6_18'] | df['L_MACD_SIGNAL'] | df['L_MACD_ZERO'])  +\
     -1*(df['S18'] | df['S3_18'] | df['S3_6'] | df['S6_18'] | df['S3_50'] | df['S6_50'] | df['S18_50'] |  df['S3_6_18'] | df['S_MACD_SIGNAL'] | df['S_MACD_ZERO']) 
    
    return df

   

def swing_high(df):
    return ((df['High'] < df['High'].shift(1)) & (df['High'].shift(1) > df['High'].shift(2)))
def swing_low(df):
    return ((df['Low'] > df['Low'].shift(1)) & (df['Low'].shift(1) < df['Low'].shift(2)))

def check_bounce(df, ind = 5, nema = 18):    
    return ((df['Open'].iloc[-ind] > df['EMA{}'.format(nema)].iloc[-ind]) 
               & (df['Close'].iloc[-ind] > df['EMA{}'.format(nema)].iloc[-ind])
               &  (df['Low'].iloc[-ind] < df['EMA{}'.format(nema)].iloc[-ind]))
    
def check_crossover(df, high = 'Close', low = 'EMA18'):
#    ((df['Close'] > df['EMA18']) & (df['C_1d'] > df['EMA18_1d']) & (df['C_2d'] < df['EMA18_2d']))
    return ((df[high] > df[low]) & (df[high].shift(1) > df[low].shift(1)) & (df[high].shift(2) < df[low].shift(2)))

def check_over_zero(df, column = 'MACD_12_26'):
    return ((df[column] > 0) & (df[column].shift(1) > 0) & (df[column].shift(2) < 0))   
    
def check_below_zero(df, column = 'MACD_12_26'):
    return ((df[column] < 0) & (df[column].shift(1) < 0) & (df[column].shift(2) > 0)) 


def hedgefund_trading(ticker, start, end, realtime = False, source = "cp68"):
       
    if source == "ssi":
        file_path = symbol_to_path_ssi(ticker)
        df = pd.read_csv(file_path, index_col ="DATE", parse_dates = True,  dayfirst=True,
                     usecols = ["DATE", "OPEN","CLOSE","HIGHEST","LOWEST","TOTAL VOLUMN"], na_values = "nan")
        df = df.rename(columns = {'DATE': 'Date', "OPEN": 'Open', 'HIGHEST': 'High',
                                  'LOWEST': 'Low','CLOSE' : 'Close', 'TOTAL VOLUMN': 'Volume'})
    else:
        file_path = symbol_to_path(ticker)
        df = pd.read_csv(file_path, index_col ="<DTYYYYMMDD>", parse_dates = True, 
                     usecols = ["<DTYYYYMMDD>", "<OpenFixed>","<HighFixed>","<LowFixed>","<CloseFixed>","<Volume>"], na_values = "nan")
        df = df.rename(columns = {'<DTYYYYMMDD>': 'Date', "<OpenFixed>": 'Open', '<HighFixed>': 'High',
                                  '<LowFixed>': 'Low','<CloseFixed>' : 'Close', '<Volume>': 'Volume'})
    
    # columns order for backtrader type
    columnsOrder=["Open","High","Low","Close", "Volume", "OpenInterest"]
    # change the index by new index
    df = df.reindex(columns = columnsOrder)  
    # change date index to increasing order
    df = df.sort_index()   
    # take a part of dataframe
    df = df.loc[start:end]
    
    if realtime:
        actual_price = get_info_stock(ticker)
        today = datetime.datetime.today()
        next_date = today
        df.loc[next_date] = ({ 'Open' : actual_price['Open'].iloc[-1],
                        'High' : actual_price['High'].iloc[-1], 
                        'Low' : actual_price['Low'].iloc[-1],
                        'Close' : actual_price['Close'].iloc[-1],
                        'Volume' : actual_price['Volume'].iloc[-1],
                        'OpenInterest': np.nan})
#        df = df.rename(columns = {'index': '<DTYYYYMMDD>'})
#    return df
    
    df['EMA18'] = pd.Series(pd.Series.ewm(df['Close'], span = 18,  min_periods = 18-1).mean()) 
    
    n_fast = 3
    n_slow = 6
    nema = 20
    df['MACD_3_6'], df['MACDSign20'], df['MACDDiff3620'] =  compute_MACD(df, n_fast, n_slow, nema)
       
        
    n_fast = 50
    n_slow = 100
    nema = 9 
    df['MACD_50_100'], df['MACDSign9'], df['MACDDiff501009'] = compute_MACD(df, n_fast, n_slow, nema)
    
    n_fast = 12
    n_slow = 26
    nema = 9
    df['MACD_12_26'], df['MACDSign9_1226'], df['MACDDiff12260'] =  compute_MACD(df, n_fast, n_slow, nema)
       

    # TREND TREND LONG
    df['TT_LONG']= ((df['Close'] > df['EMA18']) 
    & (df['MACD_3_6'] < df['MACDSign20']) & (df['MACD_3_6'] <0) & (df['MACDSign20'] > 0) 
    & (df['MACD_50_100'] > df['MACDSign9']) & (df['MACD_50_100'] > 0))
    # TREND TREND SHORT
    df['TT_SHORT']= ((df['Close'] < df['EMA18']) 
    & (df['MACD_3_6'] > df['MACDSign20']) & (df['MACD_3_6'] > 0) & (df['MACDSign20'] < 0) 
    & (df['MACD_50_100'] < df['MACDSign9']) & (df['MACD_50_100'] < 0))
   
    # TREND COUNTER TREND LONG
    df['TCT_LONG']= ((df['Close'] > df['EMA18']) 
    & (df['MACD_3_6'] < df['MACDSign20']) & (df['MACD_3_6'] <0) & (df['MACDSign20'] > 0) 
    & (df['MACD_50_100'] > df['MACDSign9']) & (df['MACD_50_100'] < 0)) 
    
    # TREND COUNTER TREND SHORT
    df['TCT_SHORT']= ((df['Close'] < df['EMA18']) 
    & (df['MACD_3_6'] > df['MACDSign20']) & (df['MACD_3_6'] > 0) & (df['MACDSign20'] < 0) 
    & (df['MACD_50_100'] < df['MACDSign9']) & (df['MACD_50_100'] > 0))
   
    
    
    # PRICE_ACTION
    df['1TT_LONG'] = ((df['High']< df['High'].shift(1)) 
    & (df['Close'] > df['EMA18']) & (df['Close'].shift(1) < df['EMA18'].shift(1)))
    
    df['2TT_LONG'] = ((df['High']< df['High'].shift(1)) 
    & (df['Close'] > df['EMA18']) & (df['Open'] < df['EMA18'])
    & (df['Close'].shift(1) < df['EMA18'].shift(1)) & (df['Open'].shift(1) > df['EMA18'].shift(1)))
    
    df['B_LONG'] = ((df['High']< df['High'].shift(1)) 
    & (df['Close'] > df['EMA18']) & (df['Open'] > df['EMA18']) & (df['Low'] < df['EMA18'])
    & (df['Close'].shift(1) > df['EMA18'].shift(1)) & (df['Open'].shift(1) > df['EMA18'].shift(1))
    & (df['Low'].shift(1) < df['EMA18'].shift(1)))
    
    
    df['S2BR_LONG'] = ((df['Low']< df['Low'].shift(1)) & (df['High'].shift(1) < df['High'].shift(2))
    & (df['Close'] > df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1))
    & (df['1TT_LONG'] | df['2TT_LONG'] | df['B_LONG']))
    
    df['PAR_LONG'] = ((df['Low']< df['Low'].shift(1)) & (df['High'].shift(1) < df['High'].shift(2))
    & (df['Close'] > df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1))
    & (df['Open'] > df['Low'].shift(1)) & (df['Close'] > df['Low'].shift(1))
    & (df['1TT_LONG'] | df['2TT_LONG'] | df['B_LONG']))
    
    df['PARW_LONG'] = ((df['Low']< df['Low'].shift(1)) & (df['High'].shift(1) < df['High'].shift(2))
    & (df['Open'] > df['Low'].shift(1)) & (df['Close'] > df['Low'].shift(1))
    & (df['1TT_LONG'] | df['2TT_LONG'] | df['B_LONG']))
    
    df['LIBR_LONG'] = ((df['Low'] > df['Low'].shift(1)) & (df['High'].shift(1) < df['High'].shift(2))
    & (df['Close'] > df['Open']) & (df['Close'].shift(1) < df['Open'].shift(1))
    & (df['1TT_LONG'] | df['2TT_LONG'] | df['B_LONG']))
    
    df['LIBPR_LONG'] =  ((df['Low']< df['Low'].shift(1)) & (df['High'].shift(1) < df['High'].shift(2))
    & (df['Low'].shift(1) > df['Low'].shift(2)) & (df['High'].shift(2) < df['High'].shift(3))
    & (df['Low'].shift(2) < df['Low'].shift(3))
    & (df['1TT_LONG'] | df['2TT_LONG'] | df['B_LONG']))
    
    df['LHPR_LONG'] = ((df['Low']< df['Low'].shift(1)) & (df['High'].shift(1) > df['High'].shift(2))
    & (df['Low'].shift(1) > df['Low'].shift(2)) & (df['High'].shift(2) < df['High'].shift(3))
    & (df['Low'].shift(2) < df['Low'].shift(3))
    & (df['1TT_LONG'] | df['2TT_LONG'] | df['B_LONG']))
    
    
    
    df['LTT'] = df['TT_LONG'] & (df['1TT_LONG'] | df['2TT_LONG'] | df['B_LONG'])
    df['LCTT'] = df['TCT_LONG'] & (df['1TT_LONG'] | df['2TT_LONG'] | df['B_LONG'])
    
    df['LTT_A'] = df['TT_LONG'] & (df['S2BR_LONG']  | df['PAR_LONG'] | df['PARW_LONG'] | df['LIBR_LONG'] | df['LIBPR_LONG']
    | df['LHPR_LONG'] )
    df['LCTT_A'] = df['TCT_LONG'] & (df['S2BR_LONG']  | df['PAR_LONG'] | df['PARW_LONG'] | df['LIBR_LONG'] | df['LIBPR_LONG']
    | df['LHPR_LONG'])
    
    df['Signal'] = 1*(df['LTT'] | df['LCTT'] | df['LTT_A'] | df['LCTT_A'])
    
    
    
    df['1TT_SHORT'] = ((df['Low']> df['Low'].shift(1)) 
    & (df['Close'] < df['EMA18']) & (df['Close'].shift(1) > df['EMA18'].shift(1)))
    
    df['2TT_SHORT'] = ((df['Low'] > df['Low'].shift(1)) 
    & (df['Close'] < df['EMA18']) & (df['Open'] > df['EMA18'])
    & (df['Close'].shift(1) > df['EMA18'].shift(1)) & (df['Open'].shift(1) < df['EMA18'].shift(1)))
    
    df['B_SHORT'] = ((df['Low'] > df['Low'].shift(1)) 
    & (df['Close'] < df['EMA18']) & (df['Open'] < df['EMA18']) & (df['High'] > df['EMA18'])
    & (df['Close'].shift(1) < df['EMA18'].shift(1)) & (df['Open'].shift(1) < df['EMA18'].shift(1))
    & (df['High'].shift(1) > df['EMA18'].shift(1)))
    
    
     # MOMENTUM     
    n_fast = 12
    n_slow = 26
    nema = 9
    MACD, MACDsign,_ = compute_MACD(df, n_fast, n_slow, nema)
    df['MACD_UP'] = (MACD > MACDsign)
    df['MACD_DOWN'] = (MACD < MACDsign)
    
    
    hm_days = 5
    for i in range(1,hm_days+1):
        if (df['LTT'].iloc[-i] | df['LCTT'].iloc[-i]):
            print(" Time for slingshot trading ", str(i), " days before ", df.iloc[-i].name ,  ticker)
#            print(" Price at that day : ", df.iloc[-i][0:4])
        if (df['LTT_A'].iloc[-i] | df['LCTT_A'].iloc[-i]):
            print(" Advanced slingshot trading ", str(i), " days before ", df.iloc[-i].name ,  ticker)
        
    return df

def bollinger_bands(ticker, start, end, realtime = False, source = "cp68",):
    
    if source == "ssi":
        file_path = symbol_to_path_ssi(ticker)
        df = pd.read_csv(file_path, index_col ="DATE", parse_dates = True,  dayfirst=True,
                     usecols = ["DATE", "OPEN","CLOSE","HIGHEST","LOWEST","TOTAL VOLUMN"], na_values = "nan")
        df = df.rename(columns = {'DATE': 'Date', "OPEN": 'Open', 'HIGHEST': 'High',
                                  'LOWEST': 'Low','CLOSE' : 'Close', 'TOTAL VOLUMN': 'Volume'})
    else:
        file_path = symbol_to_path(ticker)
        df = pd.read_csv(file_path, index_col ="<DTYYYYMMDD>", parse_dates = True, 
                     usecols = ["<DTYYYYMMDD>", "<OpenFixed>","<HighFixed>","<LowFixed>","<CloseFixed>","<Volume>"], na_values = "nan")
        df = df.rename(columns = {'<DTYYYYMMDD>': 'Date', "<OpenFixed>": 'Open', '<HighFixed>': 'High',
                                  '<LowFixed>': 'Low','<CloseFixed>' : 'Close', '<Volume>': 'Volume'})
    
    # columns order for backtrader type
    columnsOrder=["Open","High","Low","Close", "Volume", "OpenInterest"]
    # change the index by new index
    df = df.reindex(columns = columnsOrder)  
    # change date index to increasing order
    df = df.sort_index()   
    # take a part of dataframe
    df = df.loc[start:end]
    
    if realtime:
        actual_price = get_info_stock(ticker)
        today = datetime.datetime.today()
        next_date = today
        df.loc[next_date] = ({ 'Open' : actual_price['Open'].iloc[-1],
                        'High' : actual_price['High'].iloc[-1], 
                        'Low' : actual_price['Low'].iloc[-1],
                        'Close' : actual_price['Close'].iloc[-1],
                        'Volume' : actual_price['Volume'].iloc[-1],
                        'OpenInterest': np.nan})
    
    
    
    period = 20
    nstd = 2
    rolling_mean = df['Close'].rolling(window=period,center=False).mean()
    rolling_std = df['Close'].rolling(window=period,center=False).mean()
    
    df['Bollinger High'] = rolling_mean + (rolling_std * nstd)
    df['Bollinger Low'] = rolling_mean - (rolling_std * nstd)
    df['Signal'] = -1*((df['Close'] > df['Bollinger High']) & (df['Close'].shift(1) < df['Bollinger High'].shift(1))) + \
                   1 *((df['Close'] < df['Bollinger Low']) & (df['Close'].shift(1) > df['Bollinger Low'].shift(1)))
            
    
    hmdays = 5
    for row in range(1,hmdays+1):    
        if (df['Close'].iloc[-row] > df['Bollinger High'].iloc[-row]) and (df['Close'].iloc[-row-1] < df['Bollinger High'].iloc[-row-1]):
            print(" Time for bollinger trading sell ", str(row), " days before ", df.iloc[-row].name ,  ticker)
        
        if (df['Close'].iloc[-row] < df['Bollinger Low'].iloc[-row]) and (df['Close'].iloc[-row-1] > df['Bollinger Low'].iloc[-row-1]):
            print(" Time for bollinger trading buy ", str(row), " days before ", df.iloc[-row].name ,  ticker)
            
    return df

def compute_MACD(df, n_fast, n_slow, nema = 9):  
    EMAfast = pd.Series(pd.Series.ewm(df['Close'], span = n_fast, min_periods = n_fast - 1).mean())  
    EMAslow = pd.Series(pd.Series.ewm(df['Close'], span = n_slow, min_periods = n_slow - 1).mean())  
    MACD = pd.Series(EMAfast - EMAslow, name = 'MACD_' + str(n_fast) + '_' + str(n_slow))  
    MACDsign = pd.Series(pd.Series.ewm(MACD, span = nema, min_periods = nema-1).mean(), name = 'MACDsign_' + str(n_fast) + '_' + str(n_slow))  
    MACDdiff = pd.Series(MACD - MACDsign, name = 'MACDdiff_' + str(n_fast) + '_' + str(n_slow))  
    
#    MACD, MACDsign, MACDdiff = talib.MACD(df['Close'].values, fastperiod=n_fast, slowperiod= n_slow, signalperiod=nema)
    return MACD, MACDsign, MACDdiff

