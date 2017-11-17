#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""

取引を行う

"""

import json
import time
import os
from datetime import datetime as dt

from coincheck_api import CoincheckAPIManager
from policy import NaivePolicy as Policy


class BTCTrader(object):
    """

    取引を行う

    """

    def __init__(self, Policy, accesskey, secret_accesskey, sleep_interval=2, budget_ratio=0.01):
        self.api = CoincheckAPIManager(
            accesskey, secret_accesskey,
            debug=True,
            private_request_interval=sleep_interval
        )
        self.waiting_order = False
        self.waiting_order_ids = []
        self.last_order_id = -1
        self.budget_ratio = budget_ratio # 危険なので使用できる資産を制限する

        #現在の資産を確認
        self.balance = self.api.private_balance()

        self.policy = Policy(balance=self.balance)

    def run(self):
        while True:
            #注文を投げている場合，ステータスの確認と更新
            if self.waiting_order:
                _, tarnsactions = self.api.private_transactions(pagenate=True)
                if self.last_order_id != transactions['data'][0]['order_id']:
                    self.last_order_id = transactions['data'][0]['order_id']
                    for idx, order_id in enumerate(self.waiting_order_ids):
                        if order_id == self.last_order_id:
                            self.waiting_order_ids.pop(idx)

                    print('new transaction: {}'.format(transactions['data'][0]))
                    if len(self.waiting_order_ids) == 0:
                        self.waiting_order = False
                    else:
                        print('still waiting... {}'.format(self.waiting_order_ids))

            info = self._listen_info()
            actions = self.policy.decide_actions(based_on=info)
            for action in actions:
                print(action)
                self._take(action)

    def report(self):
        """
        取引履歴をレポートに出力
        """

        balance = self.api.private_balance()
        transactions = self.api.private_transactions()

        timestamp = dt.now().strftime('%Y%m%d_%H%M')
        output_path = '../report/{}/'.format(timestamp)

        if not os.path.exists(output_path):
            os.mkdir(output_path)

        with open(os.path.join(output_path, 'balance.json'), 'w') as f:
            json.dump(balance, f)

        with open(os.path.join(output_path, 'transactions.json'), 'w') as f:
            json.dump(transactions, f)

    def _listen_info(self):
        """
        取引所APIで情報を確認
        """

        _, ticker = self.api.public_ticker()
        _, trades = self.api.public_trades()
        _, orderbooks = self.api.public_orderbooks()
        _, balance = self.api.private_balance()

        balance = self._format_balance(balance)

        return {
            "ticker": ticker,
            "trades": trades,
            "orderbooks": orderbooks,
            "balance": balance
        }

    def _format_balance(self, balance):
        # multiply budget ratio
        if not balance['success']:
            raise ValueError(str(balance))

        del balance['success']
        for key, value in balance.items():
            if key == 'success':
                continue

            balance[key] = float(balance[key])*self.budget_ratio

        return balance

    def _take(action):
        """
        アクションに応じたオーダAPI叩き
        """
        if action.order_type in ('sell', 'buy'):
            if action.order_type == 'sell':
                assert float(self.balance["btc"]) >= action.amount
            else:
                assert float(self.balance["jpy"]) >= action.amount

            _, order = self.api.private_new_order(action.rate, action.amount, action.order_type)
            if order['success']:
                self.waiting_order = True
                self.waiting_order_ids.append(order['id'])
                return 0
            else:
                print('failed to order')
                print(order)
                return -1

        elif action.order_type == 'cancel':
            cancel_order = self.api.private_cancel_order(action.cancel_id)
            if cancel_order['success']:
                try:
                    canceled_order_idx = self.waiting_order_ids.index(cancel_order['id'])
                    self.waiting_order_ids.pop(canceled_order_idx)
                except ValueError as e:
                    print('error in indexing waiting order')
                    raise ValueError(e)

                if len(self.waiting_order_ids) == 0:
                    self.waiting_order = False

                return 0


if __name__ == '__main__':
    api_keys = json.load(
        open('../static/api_key.json')
    )

    trader = BTCTrader(
        Policy=Policy,
        accesskey=api_keys['accesskey'],
        secret_accesskey=api_keys['secret_accesskey'],
    )

    try:
        trader.run()
    except KeyboardInterrupt:
        trader.report()
