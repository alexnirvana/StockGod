# Build your first rule-based strategy

Your goal is to run a reproducible experiment and explain what it can and cannot establish.

## A precise rule

The preset strategy compares short and long moving averages. It buys when the short average is above the long average and sells otherwise.

Signals use **previous closing prices**. Execution is estimated at the next open under a model fixed in advance. Using later information to make an earlier decision would introduce look-ahead bias.

## Run the experiment

Open Strategy Lab. Choose a short window, a longer window, and an entry allocation. The worker saves the task and produces a report using 60 days of fixed fictional data.

Inspect the equity curve, benchmark, maximum drawdown, fees, trades, data version, rule version, and parameters.

## Compare with care

The benchmark is buy-and-hold without fees; the strategy includes teaching fees. The report explains this difference. End-of-period holdings are valued at the close rather than forcibly sold.

Trying many parameter sets and choosing the highest return can overfit the dataset. A result describes only the selected data and assumptions.

## Completion

Finish one teaching experiment and answer both independent questions. No level of profit is required, and the report does not predict future returns.
