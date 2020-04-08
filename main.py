# -*- coding: utf-8 -*-

from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import *

import sys
from configparser import ConfigParser
import logging

from bithumb import Bithumb

from concurrent.futures import ThreadPoolExecutor, as_completed

gui_form = uic.loadUiType('maniBot.ui')[0]

stop_flag = True

def get_logger():
    logger = logging.getLogger("Thread Example")
    logger.setLevel(logging.DEBUG)
    # fh = logging.FileHandler("threading.log") #로그 파일 출력
    fh = logging.StreamHandler()
    fmt = '%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt)
    fh.setFormatter(formatter)

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

        self.bot = Bithumb(connect_key, secret_key)

        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.result = {}

        self.per_run = per_run
        self.tot_run = 0

    def set_run(self, tot_run):
        self.tot_run = tot_run

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

            self.user_confirm = False
            return True

        except Exception as ex:
            logger.debug('create_thread fail %s' %ex)
            self.user_confirm = False
            return False


    def run_thread(self, start, end):
        logger.debug("run thread {} ~ {}" .format(start, end))
        futures = {self.executor.submit(self.seek_balance, i): i for i in range(start, end)}
        for future in as_completed(futures):
            try:
                data = future.result()
                # print(data)
            except Exception as ex:
                self.result[future] = 'Fail'
            else:
                self.result[future] = data

    def seek_balance(self, number):
        logger.debug('execute function executing')
        result = self.bot.balance('ETH')
        logger.debug('execute function ended with: {}'.format(number))
        return result

class MyWindow(QMainWindow, gui_form):

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.MyDialgo()

        self.mode  = 'sell'
        self.auto  = True

        # logger = self.get_logger()
        self.result = []

        self.user_confirm = False
        self.tot_run = 0
        self.per_run = 5

        self.worker = Worker()
        self.worker.update_signal.connect(self.display_result)
        self.worker.start()

    @pyqtSlot(dict)
    def display_result(self, data):
        logger.debug('===>display_result')

        try:
            for k, v in data.items():
                print(k, ' :', v)
            self.user_confirm = False

        except Exception as ex:
            logger.debug('display_result fail %s' %ex)

    def MyDialgo(self):

        self.confirm_pushButton.clicked.connect(self.confirm_cmd)
        self.action_pushButton.clicked.connect(self.action_cmd)
        self.refresh_pushButton.clicked.connect(self.refresh_cmd)

        self.sell_radioButton.clicked.connect(self.mode_cmd)
        self.buy_radioButton.clicked.connect(self.mode_cmd)

        self.auto_checkBox.stateChanged.connect(self.auto_cmd)

    def confirm_cmd(self):

        self.user_confirm = False

        price = self.price_lineEdit.text()
        qty   = self.qty_lineEdit.text()
        tot_run = self.count_lineEdit.text()
        # coin  = self.coin_lineEdit.text()
        coin = 'DAC'

        if price == '' or qty == '' or tot_run == '' or coin == '':
            print("Type in parameters")
            self.textBrowser.setText('메시지 : ' + '값을 입력해 주세요')
            return "Error"

        self.price = float(price)
        self.qty   = float(qty)
        self.tot_run = int(tot_run)

        self.worker.set_run(self.tot_run)
        logger.debug("{} @ {} for {}" .format(self.qty, self.price, self.tot_run))
        # display on pannel

        # confirm for user input
        self.user_confirm = True

    def action_cmd(self):
        logger.debug("action_orders_cmd")
        if self.user_confirm :
            # self.create_thread(self.count, 5)
            global stop_flag
            print('stop flag ' , stop_flag)
            stop_flag = False

    def refresh_cmd(self):
        pass

    def mode_cmd(self):
        if self.sell_radioButton.isChecked():
            self.mode = 'sell'
            print('sell')
        elif self.buy_radioButton.isChecked():
            self.mode = 'buy'
            print('buy')
        else:
            raise ValueError

    def auto_cmd(self):
        if self.auto_checkBox.isChecked():
            self.auto = True
        else:
            self.auto = False


def main_QApp():
    app = QApplication(sys.argv)
    main_dialog = MyWindow()
    main_dialog.show()
    app.exec_()


if __name__ == '__main__':
    main_QApp()
