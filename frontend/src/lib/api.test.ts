import { afterEach, expect, it, vi } from 'vitest'
import { api, setActiveUser } from './api'

afterEach(() => { vi.unstubAllGlobals(); setActiveUser('anonymous') })

it('does not sign out a new account when an old checkpoint returns unauthorized', async () => {
  let respond!: (response: Response) => void
  const dispatchEvent = vi.fn()
  vi.stubGlobal('window', { dispatchEvent })
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(resolve => { respond = resolve })))
  setActiveUser('first-account')
  const oldRequest = api('/listening')
  setActiveUser('second-account')
  respond(new Response(JSON.stringify({ detail: 'Session expired' }), { status: 401 }))
  await expect(oldRequest).rejects.toThrow('Session expired')
  expect(dispatchEvent).not.toHaveBeenCalled()
  const currentRequest = api('/listening')
  respond(new Response(JSON.stringify({ detail: 'Session expired' }), { status: 401 }))
  await expect(currentRequest).rejects.toThrow('Session expired')
  expect(dispatchEvent).toHaveBeenCalledTimes(1)
})
