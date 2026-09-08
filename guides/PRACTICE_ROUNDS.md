# Practice rounds

[English](PRACTICE_ROUNDS.md) · [简体中文](PRACTICE_ROUNDS_CN.md) · [Home](../README.md)

Stock God 0.6 lets you repeat free practice while keeping each earlier account and its records. Rounds use the existing fixed teaching dataset, not real historical market data.

## Start again

1. Open **Practice → New round**.
2. Review the round number, teaching day, and virtual assets in the dialog.
3. Cancel or settle any pending orders first. Starting another round does not silently cancel them.
4. Choose **Archive and start again**. A new account starts on teaching day 20 with 100,000 virtual CNY, no positions, and its own cash ledger.

The previous account becomes read-only. Its cash, positions, orders, ledger, and reflections remain available. Positions are not automatically sold: archived position values use the closing prices on that round's final teaching day. You can also start again after reaching day 60.

The new round repeats the same scenario, so it is useful for practicing a different decision rather than testing on unseen data. Tutorial accounts, course completion, XP, listening bookmarks, and strategy experiments are separate.

## Inspect a round

Open **Practice → Practice rounds → View round**. The dialog shows cash and position values, orders, positions, cash movements, visible prices for SG001, and saved reflections. Earlier rounds load in pages. The view never includes prices beyond that round's current or archived day.

Use **Reflect on this round** to save a plan and reflection to the current free-practice account. The form records your written account of the exercise; it does not prove the plan was written before trading. Once a round is archived, its reflections cannot be added to or edited through this flow.

## Persistence and concurrency

- Accounts are unique by player, mode, and round number. Application mutations run inside a transaction that locks the player, ensuring only one current round is created.
- Starting a round archives the existing account and creates the new account and opening ledger entry in the same transaction.
- Free-practice orders, day advances, and reflections include `expected_account_id` and `expected_day`. A stale tab receives HTTP 409, rather than applying an old intention to a new round or teaching day. Reload the page and review the action again.
- Repeated requests with the same idempotency key and body return the original result. Concurrent distinct requests to start the next round cannot create two replacement accounts.
- Record access and exports remain scoped to the authenticated user. A round belonging to another user returns HTTP 404.
- Each account pins its data and rules versions. If these are unavailable, detailed valuation is unavailable with HTTP 503; the round list and raw account export remain available.

## Upgrade from 0.5

Back up MySQL before rebuilding the services. Migration `f24ca6e36155` keeps existing account IDs and balances, assigns round number 1, and adds archive timestamps and data versions. Creation timestamps for pre-existing accounts remain unknown instead of being invented.

The standard `/api/export` audit file includes all owned rounds and their associated records. Use a full database backup for restoration, as described in [operations](OPERATIONS.md). The migration deliberately refuses a destructive downgrade that would discard later rounds.

## Relevant endpoints and checks

| Endpoint | Purpose |
| --- | --- |
| `GET /api/accounts/free` | Current free-practice account |
| `GET /api/practice/rounds?limit=20&before=3` | Owned rounds, in descending order |
| `GET /api/practice/rounds/{account_id}` | Read-only account detail with reflections |
| `POST /api/practice/rounds` | Archive the current account and start another |

The last endpoint accepts only `expected_account_id` and `expected_day`; starting funds, clock, and round number are set by the server. Existing cookie, CSRF, origin, and idempotency requirements apply to writes. Pre-0.6 free-practice clients must reload to send the new context fields.

Regression tests cover preservation, migration, ownership, pagination, repeat requests, concurrent archive/order/day operations, stale clients, end-of-data recovery, and unchanged course rewards. UI controls reuse the compact workspace and existing dialogs.
