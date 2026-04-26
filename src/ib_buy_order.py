from ib_async import *

ib = IB()
ib.connect('127.0.0.1', 4001, clientId=1)

# Request delayed market data (free, no subscription needed)
# 1=Live, 2=Frozen, 3=Delayed, 4=Delayed-Frozen
ib.reqMarketDataType(3)

stock = Stock('TSLA', 'SMART', 'USD')
[qualified_contract] = ib.qualifyContracts(stock)
ticker = ib.reqMktData(qualified_contract)
ib.sleep(2)
print(ticker.last)

#ib.disconnect()


# ib = IB()
# ib.connect('127.0.0.1', 7497, clientId=1)

contract = Stock('LYFT', 'SMART', 'USD')
ib.qualifyContracts(contract)
#order = MarketOrder('BUY', 1) # Buy 10 shares
order = LimitOrder('SELL', 1, 1.00)
order.outsideRth = True # Allow execution outside regular trading hours
order.tif = 'GTC'  # Set to Good Till Cancelled

# # Place the order and get a Trade object

trade = ib.placeOrder(contract, order)

# Assuming 'trade' was the result of ib.placeOrder()
# ib.cancelOrder(trade.order)

# ib.reqGlobalCancel() 


# Monitor status
# ib.sleep(1)
# print(trade.orderStatus.status)

# # Wait for order to complete
# while not trade.isDone():
#     ib.sleep(1)
#     print(f"Status: {trade.orderStatus.status}")

# print("Trade filled!")
ib.disconnect()
