#!/usr/bin/env python
# -*- coding:utf-8 -*-

import numpy as np


class BasePolicy(object):
    def __init__(self, balance, limit_budget=0.01):
        self.init_balance = balance
        self.last_indexes = {"ticker": {}, "trades": {}, "orderbooks": {}, "balance": {}}
        self.limit_budget = limit_budget # 予算の割合に対する制限

    def decide_actions(self, based_on):
        """
        得られた情報に従ってアクションリストを作成
        """
        actions = []
        return actions

    def set_indexes(self, ticker, trades, orderbooks, balance):
        self.last_indexes = {"ticker": ticker, "trades": trades, "orderbooks": orderbooks, "balance": balance}


class NaivePolicy(BasePolicy):
    """

    とりあえずめちゃくちゃ愚直なアルゴリズムで遊んでみる

    価格の変化履歴を10秒分保持

    jpyが手元にある場合
    -> 上昇トレンドであればbtcを買う、0.1%高い価格で即売りに出す
    -> 下降トレンドであれば何もしない

    btcが手元にある場合
    -> 上昇トレンドであれば買った価格の100.05%で売り出し
    -> 下降トレンドであれば、閾値以上の下げ(~1%?)に対して損切り

    """

    def __init__(self, balance, limit_budget=0.01, history_length=100):
        super().__init__(balance, limit_budget)
        self.price_history = []
        self.last_buy_price = 1e10
        self.last_sell_price = -1
        self.history_length = history_length

    def decide_actions(self, based_on):
        actions = []
        self.ticker, self.trades, self.balance = based_on["ticker"], based_on["trades"], based_on["balance"]

        last_price = float(self.trades[0]['rate'])
        self.update_price_history(last_price)

        jpy = max(float(self.balance['jpy']) - float(self.init_balance['jpy'])*(1-self.limit_budget), 0)
        btc = max(float(self.balance['btc']) - float(self.init_balance['btc'])*(1-self.limit_budget), 0)
        jpy_inuse = float(self.balance['jpy_reserved'])
        btc_inuse = float(self.balance['btc_reserved'])

        print(self.ticker)
        print('jpy:{} btc:{} jpy_inuse:{} btc_inuse:{}'.format(jpy, btc, jpy_inuse, btc_inuse))

        gradient = self.trend()

        if gradient > -100 and jpy > .005/last_price:
            rate = int(last_price+gradient)
            actions.append(
                Action('buy', rate=rate, amount=jpy/rate, stop_loss_rate=rate*1.01)
            )
            self.last_buy_price = rate

        if gradient > -100 and btc > .005:
            rate = int(max(last_price, self.last_buy_price)*1.0005)
            actions.append(
                Action('sell', rate=rate, amount=btc, stop_loss_rate=rate*0.99)
            )
            self.last_sell_price = rate

        return actions

    def update_price_history(self, price):
        if len(self.price_history) < self.history_length:
            self.price_history.append(price)
        else:
            self.price_history = self.price_history[1:]
            self.price_history.append(price)

    def trend(self):
        """
        最小二乗法によって傾きを求める
        """

        if len(self.price_history) < self.history_length:
            return -1e10

        idxes = np.arange(self.history_length)
        observed = np.array(self.price_history)
        gradient = ( self.history_length*np.sum(idxes*observed) - np.sum(idxes)*np.sum(observed) ) / ( self.history_length*np.sum(idxes**2) - np.sum(idxes)**2 )
        return gradient


class Action(object):
    def __init__(self, order_type, rate, amount, cancel_id=None, stop_loss_rate=None):
        assert order_type in ('sell', 'buy', 'cancel')
        assert order_type != 'cancel' or (order_type == 'cancel' and cancel_id is not None)

        self.order_type = order_type
        self.rate = rate
        self.amount = amount
        self.cancel_id = cancel_id
        self.stop_loss_rate = None

    def __repr__(self):
        return '< order_type : {}, rate: {}, amount: {}>'.format(self.order_type, self.rate, self.amount)
