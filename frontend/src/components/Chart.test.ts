import { describe, expect, it } from 'vitest'
import { aggregateBars } from './Chart'
const bars = [
  { day: 0, open: '10', close: '12', high: '13', low: '9', volume: 100, suspended: false },
  { day: 1, open: '12', close: '11', high: '14', low: '10', volume: 250, suspended: false },
  { day: 2, open: '11', close: '15', high: '16', low: '10.5', volume: 300, suspended: false },
]
describe('period aggregation preserves visible OHLCV data', () => {
  it('uses first open, last close, extrema and summed volume', () => {
    expect(aggregateBars(bars, 5)).toEqual([{ day: 2, open: '10', close: '15', high: '16', low: '9', volume: 650, suspended: false }])
  })
  it('retains incomplete visible periods without inventing future bars', () => {
    expect(aggregateBars(bars, 2)).toHaveLength(2)
    expect(aggregateBars(bars, 2)[1]).toEqual(bars[2])
    expect(aggregateBars([], 5)).toEqual([])
  })
})

