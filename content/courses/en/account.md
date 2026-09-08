# Meet your simulated account

Your goal is to distinguish **cash**, **available cash**, **positions**, and **orders**.

## One account, several different numbers

- **Cash** is the money currently in the account.
- **Reserved cash** supports pending buy orders. It cannot support another order at the same time.
- **Available cash** is cash minus reserved cash.
- **Position value** is the current teaching price multiplied by shares held.
- **Total assets** are cash plus position value.

For example, CNY 30,000 in cash with CNY 5,000 reserved leaves CNY 25,000 available. Cancelling that pending order releases the reservation; it does not create new money.

## Orders are intentions

Submitting an order does not immediately create a position. Open the order record to inspect its state. An execution changes positions and the cash ledger.

The tutorial account and the free-practice account each start with **100,000 virtual CNY**, and their records are separate.

## Try it yourself

Inspect available and reserved cash in the tutorial overview. Then close this explanation and answer the two independent questions.

All prices and funds are simulated. Understanding the account, rather than making a profit, completes this lesson.
