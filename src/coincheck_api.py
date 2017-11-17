#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""

coincheckの提供するapiへのアクセス

"""

import hashlib
import hmac
import json
import time
import urllib

import requests


class CoincheckAPIManager(object):

    COINCHECK_URL_BASE = "https://coincheck.com/"

    def __init__(self, accesskey, secret_accesskey, debug=False, private_request_interval=2):
        self.__accesskey = accesskey
        self.__secret_accesskey = bytes(secret_accesskey, 'latin-1')
        self.__debug_mode = debug
        self.__private_request_interval = private_request_interval
        self.__last_nonce = -1

    def public_ticker(self):
        """
        /api/ticker

        RESPONSE ITEMS

        last 最後の取引の価格
        bid 現在の買い注文の最高価格
        ask 現在の売り注文の最安価格
        high 24時間での最高取引価格
        low 24時間での最安取引価格
        volume 24時間での取引量
        timestamp 現在の時刻
        """

        return self._get('/api/ticker', is_public=True)

    def public_trades(self):
        """
        /api/trades

        最新の取引履歴を取得
        """

        return self._get('/api/trades', is_public=True)

    def public_orderbooks(self):
        """
        /api/order_books

        RESPONSE ITEMS

        asks 売り注文の情報
        bids 買い注文の情報
        """

        return self._get('/api/order_books', is_public=True)

    def public_rate(self, order_type="sell", pair="btc_jpy", amount='1'):
        """
        /api/exchange/orders/rate

        PARAMETERS

        *order_type 注文のタイプ（"sell" or "buy"）
        *pair 取引ペア。現在は "btc_jpy" のみです。
        amount 注文での量。（例）0.1
        price 注文での金額。（例）28000

        RESPONSE ITEMS

        rate 注文のレート
        price 注文の金額
        amount 注文の量
        """

        return self._get('/api/exchange/orders/rate', is_public=True, params={
            "order_type": order_type,
            "pair": pair,
            "amount": amount
        })

    def public_rate_purchase(self, pair='btc/jpy'):
        """
        /api/rate/[pair]

        PARAMETERS

        *pair 通貨ペア ( "btc_jpy" "eth_jpy" "etc_jpy" "dao_jpy" "lsk_jpy" "fct_jpy" "xmr_jpy" "rep_jpy" "xrp_jpy" "zec_jpy" "xem_jpy" "ltc_jpy" "dash_jpy" "bch_jpy" "eth_btc" "etc_btc" "lsk_btc" "fct_btc" "xmr_btc" "rep_btc" "xrp_btc" "zec_btc" "xem_btc" "ltc_btc" "dash_btc" "bch_btc" )
        """

        return self._get('/api/rate/{pair}'.format(pair=pair), is_public=True)

    def private_new_order(self, rate, amount, order_type, pair='btc_jpy', stop_loss_rate=None):
        """
        /api/exchange/orders [POST]

        PARAMETERS

        *pair 取引ペア。現在は "btc_jpy" のみです。
        *order_type 注文方法
        rate 注文のレート。（例）28000 成行の場合はNone
        amount 注文での量。（例）0.1
        market_buy_amount 成行買で利用する日本円の金額。（例）10000
        position_id 決済するポジションのID
        stop_loss_rate 逆指値レート

        RESPONSE ITEMS

        id 新規注文のID
        rate 注文のレート
        amount 注文の量
        order_type 注文方法
        stop_loss_rate 逆指値レート
        pair 取引ぺア
        created_at 注文の作成日時
        """

        request_body = {
            'pair': pair,
            'order_type': order_type,
            'amount': amount
        }
        if rate is not None:
            request_body['rate'] = rate
        if stop_loss_rate is not None:
            request_body['stop_loss_rate'] = stop_loss_rate

        return self._post('api/exchange/orders', body=request_body, is_public=False)

    def private_current_orders(self):
        """
        /api/exchange/orders/opens

        未決済の注文一覧
        """

        return self._get('/api/exchange/orders/opens', is_public=False)

    def private_cancel_order(self, id):
        """
        /api/exchange/orders/[id] [DELETE]

        注文のキャンセル

        :param id: <int> 注文のid
        """

        return self._delete('/api/exchange/orders/{id}'.format(id=id), is_public=False)

    def private_transactions(self, pagenate=False):
        """
        /api/exchange/orders/transactions

        取引履歴

        :params pagenate: <boolean> pagenate request or not
        """

        endpoint = '/api/exchange/orders/transactions'
        if pagenate:
            endpoint += '_pagination'

        return self._get(endpoint, is_public=False)

    def private_balance(self):
        """
        /api/accounts/balance

        残高確認
        """

        return self._get('/api/accounts/balance', is_public=False)

    def _build_header(self, for_private, url='', body=''):
        """
        ヘッダの作成

        :param for_private: <boolean> whether the header to build is used for private api or not
        :param url: <str> url
        :param body: <str> body of the request if exists
        """

        header = {'Content-Type': 'application/json'}
        if for_private:
            nonce, signature = self._build_signature(url, body)
            header['ACCESS-KEY'] = self.__accesskey
            header['ACCESS-NONCE'] = nonce
            header['ACCESS-SIGNATURE'] = signature

        return header

    def _build_signature(self, url, body):
        nonce = str(int(time.time())) # use unix timestamp as nonce
        message = bytes(nonce + url + body, 'latin-1')
        signature = hmac.new(
            self.__secret_accesskey,
            message,
            hashlib.sha256
        ).hexdigest()

        return nonce, signature

    def _build_url(self, endpoint):
        return urllib.parse.urljoin(self.COINCHECK_URL_BASE, endpoint)

    def _delete(self, endpoint, is_public, params=None):
        """
        :param url: <str>
        :param is_public: <boolean> public or not
        :param params: <dict> query parameters. default None
        """

        if not is_public:
            self._wait()

        url = self._build_url(endpoint)
        header = self._build_header(for_private=not is_public, url=url, body='')
        response = requests.delete(url, headers=header, params=params)
        return self._parse_result(response)

    def _get(self, endpoint, is_public, params=None):
        """
        :param url: <str>
        :param is_public: <boolean> public or not
        :param params: <dict> query parameters. default None
        """

        if not is_public:
            self._wait()

        url = self._build_url(endpoint)
        header = self._build_header(for_private=not is_public, url=url, body='')
        response = requests.get(url, headers=header, params=params)
        return self._parse_result(response)

    def _parse_result(self, r):
        if self.__debug_mode:
            print('request to {url}'.format(url=r.url))
            print('-------request---------')
            print('header:\n{header}'.format(header=r.request.headers))
            print('body:\n{body}'.format(body=r.request.body))
            print('-------response---------')
            print('status:{status}'.format(status=r.status_code))
            print('response body:\n{body}'.format(body=r.json()))
            print('------------------------')

        return r.status_code, r.json()

    def _post(self, endpoint, body, is_public, params=None):
        """
        :param url: <str>
        :param body: <dict>
        :param is_public: <boolean> public or not
        """

        if not is_public:
            self._wait()

        url = self._build_url(endpoint)
        body = json.dumps(body)
        header = self._build_header(for_private=not is_public, url=url, body=body, params=None)
        response = requests.post(url, headers=header, data=body)
        return self._parse_result(response)

    def _wait(self):
        """
        stop program to increment nonce
        """

        time_remaining = self.__private_request_interval - (time.time() - self.__last_nonce)
        if time_remaining > 0:
            time.sleep(time_remaining)

        self.__last_nonce = int(time.time())

        return
