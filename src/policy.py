#!/usr/bin/env python
# -*- coding:utf-8 -*-


class BasePolicy(object):
    def __init__(self, balance):
        self.balance = balance
        self.last_indexes = {"ticker": {}, "trades": {}, "orderbooks": {}, "balance": {}}

    def decide_actions(self, based_on):
        """
        得られた情報に従ってアクションリストを作成
        """
        actions = []
        return actions

    def _set_indexes(self, ticker, trades, orderbooks, balance):
        self.last_indexes = {"ticker": ticker, "trades": trades, "orderbooks": orderbooks, "balance": balance}


class NaivePolicy(BasePolicy):
    def decide_actions(self, based_on):
        ticker, trades, orderbooks, balance = based_on["ticker"], based_on["trades"], based_on["orderbooks"], based_on["balance"]
        actions = []

        return actions


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
