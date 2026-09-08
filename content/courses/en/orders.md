# Your first simulated trade

Your goal is to place a limit order and explain what happened to it.

## From order to execution

1. Select a teaching stock, price, and a quantity in **100-share lots**.
2. Submit the order. A buy order reserves cash; a sell order reserves shares.
3. Advance to the **next teaching day**.
4. Open the result and inspect its status, execution price, and fees.

A buy limit is the highest acceptable price. A sell limit is the lowest acceptable price. The teaching model checks the next day's reference open against this limit.

## If an order does not execute

A buy limit of CNY 12.00 cannot match a CNY 12.50 open. This model expires unmatched orders and releases reservations. Suspensions and a conservative one-price limit rule may also prevent execution.

Pending orders can be cancelled. An already processed order cannot be cancelled.

## Holdings and sellable shares

Shares bought today become sellable on the next teaching day. Pending sell orders also reserve shares. Therefore, total holdings can be larger than the quantity available for a new sell order.

## Completion

Complete one actual **tutorial execution**, inspect the result, and answer both independent questions. Trading in the separate free-practice account does not satisfy this tutorial requirement.

These are daily execution estimates; real order queues, partial fills, and intraday paths are not reproduced.
