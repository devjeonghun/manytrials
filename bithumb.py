#
# XCoin API-call related functions
#
# @author	btckorea
# @date	2017-04-12
#
# Compatible with python3 version.

import time
import base64
import hmac, hashlib
import urllib.parse
import urllib.request
import json
import logging
import requests


class Bithumb(object):
    def __init__(self, key, secret):
        self.exid = "bithumb"
        self.key = key
        self.secret = secret

        self.trade_fee = None  #BTC, 0.0005 BTC
        self.taker_fee  = 0.0015  #% btc
        self.maker_fee  = 0.0015  #%
        self.minimum_trade_amount = 0.0001 #5만원:0.01, 5천원:0.001, 5백원:0.0001
        self.exchange_rate = 1100
        self.targetBalance = 0
        self.baseBalance   = 0
        self.default_currency = 'KRW'

        self.targetLast    = []
        self.baseLast      = []

        self.askprice = 0
        self.bidprice = 0
        self.askqty   = 0
        self.bidqty   = 0
        self.BCH      = 0.001  #min tradable volume
        self.BTC      = 0.0001
        self.ETH      = 0.001
        self.ETC      = 0.1
        self.QTUM     = 0.0015
        self.LTC      = 0.01
        self.XRP      = 1
        self.XMR      = 0.001  #guess
        self.ZEC      = 0.0001
        self.BTG      = 0.0001
        self.DASH     = 0.0001

    def set_trade_fee(self, currency):
        response_fee = self.account(currency)
        status = "OK" if response_fee["status"] == "0000" else "ERROR"
        self.trade_fee = float(response_fee["data"]["trade_fee"])
        print("==========[Bithumb Register Trade Fee]==========")
        print("Status   : " + status)
        print("Trade Fee: " + str(response_fee["data"]["trade_fee"]))
        return None

    def get_signature(self, encoded_payload, secret_key):

        signature = hmac.new(secret_key, encoded_payload, hashlib.sha512)
        api_sign  = base64.b64encode(signature.hexdigest().encode('utf-8'))
        return api_sign

    def query(self, endpoint, params):
        base_url = 'https://api.bithumb.com'
        endpoint_item_array = {
            "endpoint": endpoint
        };

        uri_array = dict(endpoint_item_array, **params)  # Concatenate the two arrays.
        e_uri_data = urllib.parse.urlencode(uri_array)

        # Api-Nonce information generation.
        nonce = str(int(time.time() * 1000))

        data = endpoint + chr(0) + e_uri_data + chr(0) + nonce
        utf8_data = data.encode('utf-8')

        secret_key  = self.secret
        utf8_secret_key = secret_key.encode('utf-8')

        headers = {
            'Content-Type' : 'application/x-www-form-urlencoded',
            'Api-Key'      : self.key,
            'Api-Sign'     : self.get_signature(utf8_data, bytes(utf8_secret_key)),
            'Api-Nonce'    : nonce

        }
        url = base_url + endpoint
        res = requests.post(url, headers=headers, data=e_uri_data)
        result = res.json()
        return result

    def public_query(self, endpoint):
        base_url = 'https://api.bithumb.com'
        url = base_url + endpoint
        ret = urllib.request.urlopen(urllib.request.Request(url), timeout=2)
        return json.loads(ret.read())

    def ticker(self, currency):
        return self.public_query('/public/ticker/' + currency)

    def orderbook(self, currency):
        # return self.public_query('/public/orderbook/' + currency +'?group_orders=0')
        return self.public_query('/public/orderbook/' + currency )

    def recent_transactions(self, currency):
        return self.public_query('/public/recent_transactions/' + currency)

    # info api
    def account(self, currency):
        params = {
                    "currency" : currency
        }
        return self.query('/info/account/'+ currency, params)

    def balance(self, currency):
        params = {
                    "currency": currency
        }
        return self.query('/info/balance/' + currency, params)

    def infoticker(self, market):  # latest transaction info
        return self.query('ticker', {'market': market})


    def orders(self, order_id, type, currency): # 회원의 판매, 구매 거래 주문 등록 또는 진행중인 거래
        params = {
            "order_id": order_id,
            "type": type,
            "order_currency": currency,
            "payment_currency" : self.default_currency,
        }
        return self.query('/info/orders/', params)

    # executed
    def order_detail(self, order_id, type, order_currency): # 회원의 판/구매 체결 내역
        params = {
                    "order_id"  : order_id,
                    "type"      : type,
                    "order_currency"  : order_currency,
                    }
        return self.query('/info/order_detail/', params)

    # trade api
    def place(self, currency, payment_currency, units, price, type):
        params = {
                    "order_currency"    : currency,
                    "payment_currency"  : payment_currency,
                    "units"             : units,
                    "price"             : price,
                    "type"              : type
        }
        return self.query('/trade/place/', params)

    def buy(self, currency, units, price):
        payment_currency = "KRW"
        response = self.place(currency, payment_currency, units, price, "bid")
        status = "OK" if response["status"] == "0000" else "ERROR"
        orderNumber = response.get("order_id", "orderID is not key")
        return status, orderNumber, response

    def sell(self, currency, units, price):
        payment_currency = "KRW"
        response = self.place(currency, payment_currency, units, price, "ask")
        status = "OK" if response["status"] == "0000" else "ERROR"
        orderNumber = response.get("order_id", "orderID is not key")
        return status, orderNumber, response

    def cancel(self, order_id, type, currency):
        params = {
                    'type'    :type,
                    'order_id': order_id,
                    'order_currency': currency,
                    }
        return self.query('/trade/cancel/', params)

    def btc_withdrawal(self, currency, dest_address, units, tag = 0):
        params = {
                    "units"             : units,        #float
                    "address"           : dest_address,
                    "currency"          : currency,
                    "destination"       : tag
        }
        response =  self.query('/trade/btc_withdrawal', params)
        return response

    def krw_withdrawal(self, bank='', account='', price=0):
        params = {
                    "bank"              : bank,
                    "account"           : account,
                    "price"             : price,  # float
        }
        response =  self.query('/trade/krw_withdrawal', params)
        return response

    def krw_deposit(self):
        params = {}
        response =  self.query('/trade/krw_deposit', params)
        return response

    def get_last_info(self, base, currency):
        marketinfo = self.recent_transactions(currency)
        return float(marketinfo["data"][0]["price"])

    def get_ticker_info(self, currency):
        marketinfo = self.ticker(currency)
        self.askprice = float(marketinfo["data"]["sell_price"])
        self.bidprice = float(marketinfo["data"]["buy_price"])

    def get_order_info(self, currency):
        marketinfo = self.orderbook(currency)
        self.askprice = float(marketinfo["data"]["asks"][0]["price"])
        self.bidprice = float(marketinfo["data"]["bids"][0]["price"])
        self.askqty   = float(marketinfo["data"]["asks"][0]["quantity"])
        self.bidqty   = float(marketinfo["data"]["bids"][0]["quantity"])

    # def get_balance_info(self, base, currency):
    def get_balance_info(self, currency):
        balance = self.balance(currency.lower())
        self.targetBalance = (float)(balance["data"]["available_" + currency.lower()])
        self.baseBalance   = (float)(balance["data"]["available_" + 'krw'.lower()])
        # logging.info("**{} : (tBal: {:.8f}) | (pBal: {:.4f})**"
        #       .format(self.exid, self.targetBalance, self.baseBalance))

    def get_last_info_all(self, base, targets):
        raw_tickers = None
        restarget = {}

        try:
            raw_tickers = self.ticker('ALL')
        except KeyboardInterrupt:
            quit()
        except:
            logging.error('Failed to Query Bittrex API, Restarting Loop')

        for ptarget in targets:
            for praw_tickers in raw_tickers["data"]:
                if praw_tickers == ptarget:
                    restarget[ptarget] = (float)(raw_tickers["data"][ptarget]["closing_price"])
        return restarget


    def review_cancel_order(self, orderNumber, type, currency, price, qty):
        units_traded = 0
        count = 0
        while True:
            count += 1
            resp = self.orders(orderNumber, type, currency)
            print("bithumb: response %s" % resp)
            if resp["status"] == "0000":  # normal operation
               units_traded = float(resp["data"][0]["units"]) - float(resp["data"][0]["units_remaining"])
               print("units_traded %.4f" % units_traded)
               if units_traded == qty:
                   return "GO", units_traded
               elif count < 10:  #waiting trading complete
                   print("loop %d" % count)
                   continue
               else:             # failure in waiting trading complete
                   resp = self.cancel(orderNumber, type, currency)
                   print("ko %s" % resp)
                   return "NG", units_traded
            elif resp["status"] == "5600":   # order_id does not exist, ie completed
                units_traded = qty
                return "GO", units_traded
                # old version style
                # if count < 10:               # wait to start trading
                #     print("loop 5600 %d" % count)
                #     continue
                # else:                        # too long to wait to start trading
                #     resp = self.cancel(orderNumber, type, currency)
                #     print("bith: trading not exist. cancel %s" % resp)
                #     return "NG", 0
            else:   # unacceptable error
                resp = self.cancel(orderNumber, type, currency)
                print("bithumb: missed order")
                return "NG", 0