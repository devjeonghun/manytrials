import time
import hashlib
from operator import itemgetter
import hmac
import requests

import logging
logger = logging.getLogger(__name__)

# https://api-document.foblgate.com/
API_URL = 'https://api2.foblgate.com'

class Foblgate(object):

    def __init__(self, id, api_key, api_secret, target, payment):
        self.id = id
        self.connect_key = api_key
        self.secret_key = api_secret
        self.target = target.upper()
        self.payment = payment.upper()
        self.targetBalance = 0
        self.baseBalance = 0
        self.bids_qty = 0
        self.bids_price = 0
        self.asks_qty = 0
        self.asks_price = 0

        self.bot_conf = None
        # self.get_config()
        self.GET_TIME_OUT = 30
        self.POST_TIME_OUT = 60

        self.mid_price = 0 # previous mid_price

    # def __init__(self, id, api_key, api_secret, target, payment):
    #     super().__init__(id, api_key, api_secret, target, payment)
        self.nickname = 'foblgate'
        self.symbol = '%s/%s' %(self.target, self.payment)

    def http_request(self, method, path, params=None, headers=None, auth=None):
        url = API_URL + path
        try:
            if method == "GET":
                response = requests.get(url, params=params, timeout=self.GET_TIME_OUT)
                if response.status_code == 200:
                    response = response.json()
                    return response
                else:
                    logger.error('http_request_{}_{}_{}_{}'.format(method, url, params, response.read()))
            if method == "POST":
                response = requests.post(url, data=params, headers=headers, timeout=self.POST_TIME_OUT)
                if response.status_code == 200:
                    response = response.json()
                    return response
                else:
                    logger.error('http_request_{}_{}_{}_{}'.format(method, url, params, response.read()))
        except Exception as e:
            logger.error('http_request_{}_{}_{}'.format(url, params, e))

        return False

    def _produce_sign(self, params):
        connect_key = self.connect_key #.encode('utf-8')
        secret_key = self.secret_key #.encode('utf-8')
        pairName = params['pairName'] #.encode('utf-8')
        text_str = connect_key + pairName + secret_key
        md5 = hashlib.sha256()
        md5.update(text_str.encode())
        sign = md5.hexdigest()
        return sign

    def __produce_sign(self, params):
        sign_str = ''
        params['api_key'] = self.connect_key
        params['time'] = str(int(round(time.time() * 1000)))
        for k in sorted(params.keys()):
            sign_str += '{}{}'.format(k, str(params[k]))
        sign_str += self.secret_key

        return hashlib.md5(sign_str.encode('utf8')).hexdigest()

    def ticker(self, symbol):
        path =  '/open/api/get_ticker'
        request = {
            'symbol': symbol
        }
        res =   self.http_request('GET', path, request)
        if res is False:
            return False

        if isinstance(res, dict):
            if 'data' in res:
                if res['data']:
                    a = float(res['data']['buy'])
                    b = float(res['data']['sell'])
                    return (a, b)

    def depth_all(self, symbol):
        path =  '/open/api/market_dept'
        request = {
            'symbol': symbol,  # 币种对
            'type': 'step0'  # 深度类型,step0, step1, step2（合并深度0-2）；step0时，精度最高
        }
        res =   self.http_request('GET', path, request)
        if not res:
            return False

        buy_list = []
        sell_list = []
        if isinstance(res, dict):
            if 'data' in res:
                if res['data']:
                    if 'tick' in res['data']:
                        if res['data']['tick']:
                            if 'bids' in res['data']['tick']:
                                for i in res['data']['tick']['bids']:
                                    price = float(i[0])
                                    amount = float(i[1])
                                    buy_list.append([price, amount])
                            if 'asks' in res['data']['tick']:
                                for i in res['data']['tick']['asks']:
                                    price = float(i[0])
                                    amount = float(i[1])
                                    sell_list.append([price, amount])
        buy_list = sorted(buy_list, key=itemgetter(0), reverse=True)  # data["data"]["tick"]["bids"]
        sell_list = sorted(sell_list, key=itemgetter(0))  # data["data"]["tick"]["asks"]
        return {'bids': buy_list, 'asks': sell_list}

    def depth_my(self, symbol):
        path =  '/exchange-open-api/open/api/v2/new_order'
        request = {
            "pageSize": 200,
            "symbol": symbol
        }
        request['sign'] = self._produce_sign(request)
        res =   self.http_request('GET', path, request)
        if not res:
            return False

        buy_list = []
        sell_list = []
        if isinstance(res, dict):
            if 'data' in res:
                if res['data']:
                    if 'resultList' in res['data']:
                        if res['data']['resultList']:
                            for i in res['data']['resultList']:
                                price = float(i["price"])
                                amount = float(i["volume"])
                                order_id = i["id"]
                                if i['side'] == "BUY":
                                    buy_list.append((price, order_id, amount))
                                if i['side'] == "SELL":
                                    sell_list.append((price, order_id, amount))
        buy_list = sorted(buy_list, key=itemgetter(0), reverse=True)  # data["data"]["tick"]["bids"]
        sell_list = sorted(sell_list, key=itemgetter(0))  # data["data"]["tick"]["asks"]
        return {'bids': buy_list, 'asks': sell_list}

    def balances(self):
        path =  '/open/api/user/account'
        request = {}
        request['sign'] = self._produce_sign(request)
        res =   self.http_request('GET', path, request)
        if not res:
            return False
        bal = {}
        if isinstance(res, dict):
            if 'data' in res:
                if res['data']:
                    if 'coin_list' in res['data']:
                        if res['data']['coin_list']:
                            for i in res['data']['coin_list']:
                                free = float(i["normal"])
                                freeze = float(i["locked"])
                                coin = i["coin"]
                                if free + freeze > 0.0:
                                    bal[coin] = {"free": free, "freeze": freeze}
        return bal

    def create_order(self, symbol, price, amount, side):
        path =  '/open/api/create_order'
        request = {
            "side": side.upper(),  # buy or sell
            "type": 1,  # 挂单类型:1.限价委托2.市价委托
            "volume": amount,  # type=1买卖数量 type=2买总价格，卖总个数
            "price": price,  # type=1委托单价
            "symbol": symbol,  # 市场标记
            "fee_is_user_exchange_coin": 0
        }
        request['sign'] = self._produce_sign(request)
        res =   self.http_request('POST', path, request)
        if res['code'] == 0:
            print('order', symbol, price, amount, side, res['code'])
        else:
            print('order', symbol, price, amount, side, res)

    def cancel_order(self, symbol, order_id):
        path =  '/open/api/cancel_order'
        request = {
            "order_id": order_id,
            "symbol": symbol
        }
        request['sign'] = self._produce_sign(request)
        res =   self.http_request('POST', path, request)
        if res['code'] == 0:
            print('order', symbol, order_id, res['code'])
        else:
            print('order', symbol, order_id, res)

    def Ticker(self):
        path =  '/open/api/get_ticker'
        request = {
            'symbol': self.symbol
        }
        res =   self.http_request('GET', path, request)
        if res is False:
            return False

        if isinstance(res, dict):
            if 'data' in res:
                if res['data']:
                    last = float(res['data']['sell'])
                    return last

    def Balance(self):
        path = '/open/api/user/account'
        request = {}
        request['sign'] = self._produce_sign(request)
        res = self.http_request('GET', path, request)
        if not res:
            return False
        bal = {}
        if isinstance(res, dict):
            if 'data' in res:
                if res['data']:
                    if 'coin_list' in res['data']:
                        if res['data']['coin_list']:
                            for i in res['data']['coin_list']:
                                if i['coin'] == self.target:
                                    self.targetBalance = float(i['normal'])
                                if i['coin'] == self.payment:
                                    self.baseBalance = float(i['normal'])
        return True

    def Orderbook(self):
        path = '/api/ticker/orderBook'
        request = {
            'apiKey'   : self.connect_key,
            'pairName' : self.symbol,  # 币种对
        }
        # "d9522a1c5f780757d924c393c6428b246fd9541c549ca440deadd332a1be6932"
        sign = self._produce_sign(request)
        headers = {
            'SecretHeader' : sign,
        }
        res = self.http_request('POST', path, request, headers=headers)
        if not res:
            return False

        return

        buy_list = []
        sell_list = []
        try:
            if isinstance(res, dict):
                if 'data' in res:
                    if res['data']:
                        if 'tick' in res['data']:
                            if res['data']['tick']:
                                if 'bids' in res['data']['tick']:
                                    self.bids_price  = float(res['data']['tick']['bids'][0][0])
                                    self.bids_qty    = float(res['data']['tick']['bids'][0][1])
                                if 'asks' in res['data']['tick']:
                                    self.asks_price  = float(res['data']['tick']['asks'][0][0])
                                    self.asks_qty    = float(res['data']['tick']['asks'][0][1])
                                return True
        except Exception as ex:
            logger.error("Orderbook exception error %s" %ex)

        return False

    def Order(self, price, amount, side):
        path =  '/open/api/create_order'
        request = {
            "side": side.upper(),  # buy or sell
            "type": 1,  # limit order
            "volume": amount,  # type=1 Represents the quantity of sales and purchases
            "price": price,  # type=1
            "symbol": self.symbol,
            "fee_is_user_exchange_coin": 0
        }
        request['sign'] = self._produce_sign(request)
        content = self.http_request('POST', path, request)
        if not content:
            return 'ERROR', 0, content

        order_id = 0
        status = 'ERROR'
        if 'code' in content:
            status = 'OK' if content['code'] == '0' else 'ERROR'
            if status == 'OK' and 'data' in content and 'order_id' in content['data']:
                order_id = content['data']['order_id'] #string
                if not order_id :
                    status = 'ERROR'
                    order_id = 0

        return status, order_id, content

    def Cancel(self, order_id):
        path =  '/open/api/cancel_order'
        request = {
            "order_id": order_id,
            "symbol": self.symbol
        }
        request['sign'] = self._produce_sign(request)
        res =   self.http_request('POST', path, request)
        return res

    '''
    "order_info":{
        "id":343,
        "side":"sell",
        "side_msg":"Sell out",
        "created_at":"09-22 12:22",
        "price":222.33,
        "volume":222.33,
        "deal_volume":222.33,
        "total_price":222.33,
        "fee":222.33,
        "avg_price":222.33}
    }
    '''

    def Order_info(self, order_id):
        path =  '/open/api/order_info'
        request = {
            "order_id": order_id,
            "symbol": self.symbol
        }
        request['sign'] = self._produce_sign(request)
        res =   self.http_request('GET', path, request)
        if not res:
            return False

        if isinstance(res, dict):
            return res

    def review_order(self, order_id, _qty):
        units_traded = 0
        try:
            resp = self.Order_info(order_id)
            if 'code' in resp and resp['code'] == '0':
                if 'data' in resp and 'order_info' in resp['data'] :
                    if isinstance(resp['data']['order_info'], dict):
                        units_traded = float(resp['data']['order_info']['deal_volume'])
                        qty = float(resp['data']['order_info']['volume'])
                        avg_price = float(resp['data']['order_info']['avg_price'])
                        fee = float(resp['data']['order_info']['fee'])
                        if units_traded == 0:   # unfilled
                            return "GO", units_traded, avg_price, fee
                        elif units_traded < qty : #partially filled
                            print("units_traded %.4f" % units_traded)
                            return "NG", units_traded, avg_price, fee
                        else:  # filled or canceled
                            return "SKIP", units_traded, avg_price, fee
                    else:
                        # response error {'code': '0', 'msg': 'suc', 'data': {'trade_list': None, 'order_info': None}}
                        # it might be caused from not yet recorded
                        print('response error %s' % resp)
                        logger.debug("response error %s" % resp)
                        return "GO", 0, 0, 0

            logger.debug("response error %s" % resp)
            return "SKIP", 0, 0, 0
        except Exception as ex:
            logger.debug("Exception error in review order {}-{}" .format(resp, ex))
            return "SKIP", 0, 0, 0