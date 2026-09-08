export type Bookmark = { position_ms: number; playback_rate: number; revision: number }
type Position = Pick<Bookmark, 'position_ms' | 'playback_rate'>
type Intent = Position & { revision: number }

// Serialize checkpoints and retain the same intent after an uncertain response.
// A later rewind must remain a rewind, even when an earlier write is still in flight.
export class BookmarkWriter {
  private saved: Bookmark
  private desired?: Position
  private pending?: { body: Intent; key: string }
  private running?: Promise<void>
  constructor(initial: Bookmark, private post: (body: Intent, key: string) => Promise<Bookmark>,
    private updated: (bookmark: Bookmark) => void, private failed: (error: Error) => void) { this.saved = initial }

  save(value: Position) {
    this.desired = value
    return this.flush()
  }

  retry() { return this.flush() }

  private flush(): Promise<void> {
    if (this.running) return this.running
    this.running = this.drain().finally(() => { this.running = undefined })
    return this.running
  }

  private async drain() {
    while (this.pending || this.desired) {
      if (!this.pending) {
        const value = this.desired!
        this.desired = undefined
        if (value.position_ms === this.saved.position_ms && value.playback_rate === this.saved.playback_rate) continue
        this.pending = { body: { ...value, revision: this.saved.revision }, key: crypto.randomUUID() }
      }
      try {
        this.saved = await this.post(this.pending.body, this.pending.key)
        this.pending = undefined
        this.updated(this.saved)
      } catch (error) {
        this.failed(error as Error)
        return
      }
    }
  }
}

export function audioTime(ms: number) {
  const seconds = Math.max(0, Math.floor(ms / 1000))
  return Math.floor(seconds / 60) + ':' + String(seconds % 60).padStart(2, '0')
}
