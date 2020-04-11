# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import *

import sys
from configparser import ConfigParser
import logging
import timeit
import math
import time
import random

from deadline import isDeadline
from bithumb import Bithumb

from concurrent.futures import ThreadPoolExecutor, as_completed

gui_form = uic.loadUiType('maniBot2.ui')[0]

stop_flag = True

def get_logger():
    logger = logging.getLogger("maniBot")
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()

    fh = logging.FileHandler('user.log', mode='a', encoding=None, delay=False)
    fh.setLevel(logging.DEBUG)
    # create formatter
    formatter = logging.Formatter("%(asctime)s %(filename)s %(lineno)s %(message)s")
    formatter_fh = logging.Formatter("%(asctime)s %(filename)s %(lineno)s %(message)s")
    # add formatter to ch
    ch.setFormatter(formatter)
    fh.setFormatter(formatter_fh)

    logger.addHandler(ch)
    logger.addHandler(fh)
    return logger

logger = get_logger()

class Worker(QThread):

    update_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        # Load Config File
        config = ConfigParser()
        config.read('trading.conf')

        connect_key = config.get('ArbBot', 'bithumbKey')
        secret_key = config.get('ArbBot', 'bithumbSecret')
        max_workers = int(config.get('ArbBot', 'MAX_WORKERS'))
        per_run     = int(config.get('ArbBot', 'PER_RUN'))

        self.coin = config.get('ArbBot', 'coin')
        self.dryrun = int(config.get('ArbBot', 'dryrun'))
        self.tick_interval = float(config.get('ArbBot', 'tick_interval'))

        if connect_key and secret_key and max_workers and per_run and self.tick_interval and self.coin:
            logger.debug("configurations ok")
        else:
            logger.debug("Please add info into configurations")
            raise ValueError

        self.bot = Bithumb(connect_key, secret_key)

        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.result = {}

        self.per_run = per_run
        self.tot_run = 0

        self.runtime = 0  # 실행 시간 측정
        self.success = 0  # 성공률

        self.qty  = 0


    def set_run(self, price, qty, tot_run, mode):
        self.price = price
        self.qty  = qty
        self.tot_run = tot_run
        self.mode = mode

    def run(self):
        while True:
            global stop_flag
            if stop_flag == False:
               stop_flag = True
               self.result = {}
               ret = self.create_thread(self.tot_run)
               if ret:
                    self.update_signal.emit(self.result)
            self.msleep(1000)

    def create_thread(self, tot_run):
        logger.debug('create_thread tot {}' .format(tot_run))

        self.runtime = 0
        t1 = timeit.default_timer()

        try:
            mok = tot_run // self.per_run
            nam = tot_run % self.per_run
            r= 0
            self.result = {}
            for j in range(1, mok+1):
                start = r
                end = r + self.per_run
                self.run_thread(start=r, end=end)
                if r >= tot_run:
                    break
                r += self.per_run
            if r <= tot_run:
                self.run_thread(start=r, end=r+nam)

            self.runtime = timeit.default_timer() - t1
            logger.debug("{} Runtime Process".format(self.runtime))
            self.user_confirm = False
            return True

        except Exception as ex:
            logger.debug('create_thread fail %s' %ex)
            self.runtime = 0
            self.user_confirm = False
            return False


    def run_thread(self, start, end):
        logger.debug("run thread {} ~ {}" .format(start, end))

        if self.dryrun:
            futures = {self.executor.submit(self.seek_balance, i): i for i in range(start, end)}
        else:
            futures = {self.executor.submit(self.zero_trade, i): i for i in range(start, end)}

        for future in as_completed(futures):
            try:
                data = future.result()
                # print(data)
            except Exception as ex:
                self.result[future] = (0, 'fail')
            else:
                self.result[future] = data

    def seek_balance(self, number):
        logger.debug('execute function executing')
        result = self.bot.balance('ETH')
        logger.debug('execute function ended with: {}'.format(number))
        return result

    def sellnbuy(self, number):
        try:
            time.sleep(0.01)
            result = 0
            status, orderNumber, response = self.bot.sell(self.coin, self.qty, self.price)
            m = 'No.{} sell {}, orderNumber {}, result {}\n' .format(number, status, orderNumber, response)
            if status == 'OK':
                result += 1
            time.sleep(0.01)
            if orderNumber :
                status, orderNumber, response = self.bot.buy(self.coin, self.qty, self.price)
                m += 'No.{} buy  {}, orderNumber {}, result {}\n'.format(number, status, orderNumber, response)
                if status == 'OK':
                    result += 1
            # time.sleep(0.4)
            return (result, m)

        except Exception as ex:
            logger.debug("sell n buy error %s" %ex)

    def buynsell(self, number):
        try:
            time.sleep(0.01)
            result = 0
            status, orderNumber, response = self.bot.buy(self.coin, self.qty, self.price)
            m = 'No.{} buy  {}, orderNumber {}, result {}\n'.format(number, status, orderNumber, response)
            if status == 'OK':
                result += 1
            time.sleep(0.01)
            if orderNumber:
                status, orderNumber, response = self.bot.sell(self.coin, self.qty, self.price)
                m += 'No.{} sell {}, orderNumber {}, result {}\n' .format(number, status, orderNumber, response)
                if status == 'OK':
                    result += 1
            # time.sleep(0.4)
            return (result, m)

        except Exception as ex:
            logger.debug("buy n sell error %s" %ex)


    def zero_trade(self, number):
        # logger.debug("->execute start %d" %number)
        try:
            mod = number % 2

            if mod == 0 : # even
                if self.mode == 'sell':
                    ret = self.sellnbuy(number)
                else:
                    ret = self.buynsell(number)
                return ret
            else:
                if self.mode == 'sell':
                    ret = self.buynsell(number)
                else:
                    ret = self.sellnbuy(number)
                return ret
            # logger.debug("<-execute end %d" % number)

        except Exception as ex:
            logger.debug("sell n buy error %s" %ex)
            return ('fail', 'fail')


    def seek_orderbook(self, coin):
        try:
            self.bot.get_order_info(coin)
            return self.bot.askprice, self.bot.bidprice, self.bot.askqty, self.bot.bidqty
        except Exception as ex:
            logger.debug("seek orderbook error %s" %ex)
            return 0, 0, 0, 0

    def seek_ticker(self, coin):
        try:
            self.bot.get_ticker_info(coin)
            return self.bot.ticker
        except Exception as ex:
            logger.debug("seek ticker error %s" % ex)
            return 0

    def seek_spread(self, bid, ask):
        if self.tick_interval == 0.0 :
            return ValueError
        tick_floor = 1/self.tick_interval
        mid_price = (bid + ask) / 2
        mid_price = math.floor(mid_price * tick_floor) / tick_floor  # 버림처리
        if bid < mid_price < ask:
            return mid_price
        else:
            return 0

    def seek_midprice(self):

        self.seek_orderbook(self.coin)
        mid_price = self.seek_spread(self.bot.bidprice, self.bot.askprice)
        if mid_price <= 0:
            logger.debug('No spread : bids_price {} < mid_price {} < asks_price {}'
                         .format(self.bot.bidprice, mid_price, self.bot.askprice))
            return "Wait"
        else:
            return mid_price


class MyWindow(QMainWindow, gui_form):

    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.result = []

        self.user_confirm = False
        self.tot_run = 0
        self.per_run = 5
        self.mode = ''

        self.worker = Worker()
        self.worker.update_signal.connect(self.display_result)
        self.worker.start()

        # Load Config File
        config = ConfigParser()
        config.read('trading.conf')

        self.coin = config.get('ArbBot', 'Coin')
        if self.coin:
            self.orderbook_Label.setText(self.coin)
        else:
            self.textBrowser.append('Please add coin name in trading.conf file')
            raise ValueError

        self.MyDialgo()

    @pyqtSlot(dict)
    def display_result(self, data):
        logger.debug('===>display_result')

        try:
            fail = processed = traded = 0
            result = ''
            for k, v in data.items():
                if v[1] == 'fail':
                    fail += 1
                else:
                    processed += 1
                    traded += v[0]
                result += "{} \n" .format(v[1])

            message = ''
            message += result
            message += "{} traded - {} processed/{} requested \n" .format(traded, processed, self.tot_run)
            # run_per_sec = self.tot_run / self.worker.runtime
            message += "{:.4f} s runtime \n" .format(self.worker.runtime)

            self.textBrowser.append(message)
            self.user_confirm = False

        except Exception as ex:
            logger.debug('display_result fail %s' %ex)

    def MyDialgo(self):

        self.action_pushButton.clicked.connect(self.action_cmd)
        self.refresh_pushButton.clicked.connect(self.refresh_cmd)

        self.sell_radioButton.clicked.connect(self.mode_cmd)
        self.buy_radioButton.clicked.connect(self.mode_cmd)

        self.autoinput_pushButton.clicked.connect(self.autoinput_cmd)

        self.orderbook_Label.setText("호가창 : {}" .format(self.coin))
        self.delete_pushButton.clicked.connect(self.delete_logs_cmd)

    def action_cmd(self):

        # check deadline
        check = isDeadline()
        if check == 'NG':
            self.textBrowser.setText('사용기간이 만료되었습니다')
            return "Error"
        elif check == 'ERROR':
            self.textBrowser.setText('네트워크를 점검해 주세요')
            return "Error"
        else:
            self.textBrowser.setText('Bot Validation OK')
        # end check deadline

        self.user_confirm = False

        price = self.price_lineEdit.text()
        qty   = self.qty_lineEdit.text()
        tot_run = self.count_lineEdit.text()

        if price == '' or price == 'Wait' \
                or qty == '' or tot_run == '' or self.mode == '':
            print("Type in parameters")
            self.textBrowser.setText('입력값을 확인해 주세요')
            return "Error"

        if not self.mode:
            self.textBrowser.append('Please select sell or buy prefer mode')
            return "Error"

        try:
            self.price = float(price)
            self.qty   = float(qty)
            self.tot_run = int(tot_run)
        except Exception as ex:
            self.textBrowser.setText('입력값을 확인해 주세요')
            return "Error"

        if self.price <= 0 or self.qty <= 0 or self.tot_run <= 0:
            self.textBrowser.setText('입력값을 확인해 주세요')
            return "Error"

        self.worker.set_run(self.price, self.qty, self.tot_run, self.mode)
        self.textBrowser.append("{} @ {} in {}" .format(self.qty, self.price, self.tot_run))
        # display on pannel

        # confirm for user input
        self.user_confirm = True

        self.textBrowser.append("do action")
        global stop_flag
        print('stop flag ' , stop_flag)
        stop_flag = False

    def refresh_cmd(self):
        askprice, bidprice, askqty, bidqty = self.worker.seek_orderbook(self.coin)
        ticker = self.worker.seek_ticker(self.coin)
        self.last_lineEdit.setText("{:.4f}".format(ticker))
        self.ask_lineEdit.setText("{:5.0f}@{:.4f}".format(askqty, askprice))
        self.bid_lineEdit.setText("{:5.0f}@{:.4f}".format(bidqty, bidprice))
        self.textBrowser.append("ASKS {:5.0f}@{:.4f}".format(askqty, askprice))
        self.textBrowser.append("BIDS {:5.0f}@{:.4f}".format(bidqty, bidprice))

    def mode_cmd(self):
        if self.sell_radioButton.isChecked():
            self.mode = 'sell'
            print('sell')
        elif self.buy_radioButton.isChecked():
            self.mode = 'buy'
            print('buy')
        else:
            self.mode = ''

    def autoinput_cmd(self):
        val = self.worker.seek_midprice()
        if val == "Wait":
            self.price_lineEdit.setText("{}".format(val))
            self.textBrowser.append("Please wait. No spread")
        else:
            self.price_lineEdit.setText("{}" .format(val))

    def delete_logs_cmd(self):
        self.textBrowser.clear()


def main_QApp():
    app = QApplication(sys.argv)
    main_dialog = MyWindow()
    main_dialog.show()
    app.exec_()


if __name__ == '__main__':
    main_QApp()
