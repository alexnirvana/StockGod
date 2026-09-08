import { describe, expect, it, vi } from 'vitest'
import { BookmarkWriter, audioTime, type Bookmark } from './bookmarks'

describe('listening checkpoints', () => {
  it('serializes a rewind behind an in-flight checkpoint', async () => {
    let resolve!: (value: Bookmark) => void
    const post = vi.fn().mockImplementationOnce(() => new Promise<Bookmark>(r => { resolve = r }))
      .mockImplementationOnce(async body => ({ ...body, revision: body.revision + 1 }))
    const writer = new BookmarkWriter({ position_ms: 0, playback_rate: 1, revision: 0 }, post, vi.fn(), vi.fn())
    const flight = writer.save({ position_ms: 20000, playback_rate: 1 })
    void writer.save({ position_ms: 5000, playback_rate: 1.5 })
    expect(post).toHaveBeenCalledTimes(1)
    resolve({ position_ms: 20000, playback_rate: 1, revision: 1 })
    await flight
    expect(post.mock.calls[1][0]).toEqual({ position_ms: 5000, playback_rate: 1.5, revision: 1 })
  })
  it('reuses an uncertain intent before writing the latest position', async () => {
    const post = vi.fn().mockRejectedValueOnce(new Error('connection lost'))
      .mockImplementation(async body => ({ ...body, revision: body.revision + 1 }))
    const failed = vi.fn()
    const writer = new BookmarkWriter({ position_ms: 0, playback_rate: 1, revision: 0 }, post, vi.fn(), failed)
    await writer.save({ position_ms: 15000, playback_rate: 1 })
    expect(failed).toHaveBeenCalledTimes(1)
    await writer.save({ position_ms: 21000, playback_rate: 1 })
    expect(post.mock.calls[0]).toEqual(post.mock.calls[1])
    expect(post.mock.calls[2][0]).toEqual({ position_ms: 21000, playback_rate: 1, revision: 1 })
    expect(post.mock.calls[2][1]).not.toBe(post.mock.calls[0][1])
  })
  it('does not write untouched playback state', async () => {
    const post = vi.fn()
    const writer = new BookmarkWriter({ position_ms: 0, playback_rate: 1, revision: 0 }, post, vi.fn(), vi.fn())
    await writer.save({ position_ms: 0, playback_rate: 1 })
    expect(post).not.toHaveBeenCalled()
    expect(audioTime(61000)).toBe('1:01')
  })
})
