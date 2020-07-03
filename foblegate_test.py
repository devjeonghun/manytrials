from foblgate import Foblgate

if __name__ == '__main__':
    symbol = 'ZEN/KRW'
    connect_key ='9b901f49bab0bffb'
    secret_key = '56febbab81ee53a5'
    foblgate = Foblgate('0', connect_key, secret_key, 'zen', 'krw')
    ticker = foblgate.Orderbook()
    print(ticker)
    '''
    orderbook = foblegate.depth_all(symbol)
    print(orderbook)
    balances = foblegate.balances()
    print(balances)
    order = foblegate.create_order(symbol, price=1000, amount=1, side='BUY')
    print(order)
    foblegate.job_function()
    '''
