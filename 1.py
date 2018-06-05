from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])

# Import the backtrader platform
import backtrader as bt


# Create a Stratey
class TestStrategy(bt.Strategy):
    params = (
        ('maperiod', 15),
        ('printlog', False),
    )

    def log(self, txt, dt=None, doprint=False):
        ''' Logging function for this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # Keep a reference to the "close" line in the data[0] dataseries
# ? The first data in the list self.datas[0] is the default data for trading operations and to keep all strategy elements synchronized (it’s the system clock)
# it's a thing like this: <backtrader.feeds.yahoo.YahooFinanceCSVData object at
# 0x000001E15C409668> Only one level of indirection is later needed to access the close values.

        self.dataclose = self.datas[0].close
       # ? The strategy next method will be called on each bar of the system clock (self.datas[0]). This is true until other things come into play like indicators, which need some bars to start producing an output. More on that later.

        # To keep track of pending orders and buy price/commission
        self.order = None
        self.buyprice = None
        self.buycomm = None

        # Add a MovingAverageSimple indicator
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.maperiod)

        # Indicators for the plotting show
        # bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        # bt.indicators.WeightedMovingAverage(self.datas[0], period=25,
        #                                     subplot=True)
        # bt.indicators.StochasticSlow(self.datas[0])
        # bt.indicators.MACDHisto(self.datas[0])
        # rsi = bt.indicators.RSI(self.datas[0])
        # bt.indicators.SmoothedMovingAverage(rsi, period=10)
        # bt.indicators.ATR(self.datas[0], plot=False)

        
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # print("I am self: ", self, self.__dict__)
        # Simply log the closing price of the series from the reference
        self.log('Close, %.2f' % self.dataclose[0])

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

            # Not yet ... we MIGHT BUY if ...
            if self.dataclose[0] > self.sma[0]:

                # BUY, BUY, BUY!!! (with all possible default parameters)
                self.log('BUY CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.buy()

        else:

            if self.dataclose[0] < self.sma[0]:
                # SELL, SELL, SELL!!! (with all possible default parameters)
                self.log('SELL CREATE, %.2f' % self.dataclose[0])

                # Keep track of the created order to avoid a 2nd order
                self.order = self.sell()

    def stop(self):
        self.log('(MA Period %2d) Ending Value %.2f' %
                 (self.params.maperiod, self.broker.getvalue()), doprint=True)


if __name__ == '__main__':
    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    # cerebro.addstrategy(TestStrategy)
    strats = cerebro.optstrategy(
        TestStrategy,
        maperiod=range(10, 31))


    # Datas are in a subfolder of the samples. Need to find where the script is
    # because it could have been called from anywhere
    ###!!! needdd adjustements (not working without changes)
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    # print("modpath: ", modpath)
    datapath = os.path.join(modpath, 'backtrader\datas\orcl-1995-2014.txt')
    # print("datapath: ", datapath)

    # import pdb; pdb.set_trace()
    # Create a Data Feed - reformat info from csv file
    data = bt.feeds.YahooFinanceCSVData(
        dataname=datapath,
        # Do not pass values before this date
        fromdate=datetime.datetime(2000, 1, 1),
        # Do not pass values after this date
        todate=datetime.datetime(2000, 12, 31),
        reverse=False)
# at this point the metabase __call__function kicks in
# this may be just a *brilliant^ attempt to javafy python
#     print("data: ", data)
#     data:  <backtrader.feeds.yahoo.YahooFinanceCSVDat
# 0x000001E15C409668>

# p data.__dict__.keys()
# dict_keys(['params', 'p', '_owner', 'plotinfo', 'lines', 'plotlines', 'l', 'line', 'line_0', 'line0', 'line_1', 'line1', 'line_2', 'line2', 'line_3', 'line3', 'line_4', 'li
# ne4', 'line_5', 'line5', 'line_6', 'line6', '_feed', 'notifs', '_dataname', '_name', '_compression', '_timeframe', '_barstack', '_barstash', '_filters', '_ffilters'])

    # Add the Data Feed to Cerebro
    cerebro.adddata(data)
# data is now cerebro.datas
    # Set our desired cash start
    cerebro.broker.setcash(1000.0)

    # Add a FixedSize sizer according to the stake
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)

    # Set the commission - 0.1% ... divide by 100 to remove the %
    cerebro.broker.setcommission(commission=0.00)

    # Print out the starting conditions
    # print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    # import pdb; pdb.set_trace()
    # Run over everything
    cerebro.run()

    # Print out the final result
    # print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.plot()