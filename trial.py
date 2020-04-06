import unittest
import os, time
from bithumb import Bithumb
from configparser import ConfigParser

# Load Config File
config = ConfigParser()
config.read('trading.conf')

connect_key = config.get('ArbBot', 'bithumbKey')
secret_key  = config.get('ArbBot', 'bithumbSecret')

bithumb = Bithumb(connect_key, secret_key)
# TestCase를 작성
class CustomTests(unittest.TestCase):

    def setUp(self):
        print('setup')

    def tearDown(self):
        """테스트 종료 후 파일 삭제 """
        print('tear down')

    def test_mybalance(self):
        start = time.time()
        for _ in range(16):
            result = bithumb.balance('ETH')
            print(result)
        print("time :", time.time() - start)


# unittest를 실행
if __name__ == '__main__':
    unittest.main()