import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiFetch } from '@/services/http'
import {
  acceptFollower,
  fetchFollowers,
  fetchFollowersCount,
  fetchFollowing,
  fetchFollowingCount,
  fetchFollowStatus,
  followUser,
  mapFollowStatus,
  removeFollower,
  unfollowUser,
} from '@/features/followers/services/followers'

vi.mock('@/services/http', () => ({ apiFetch: vi.fn<typeof apiFetch>() }))

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe('mapFollowStatus', () => {
  it('returns none when there is no relationship', () => {
    expect(mapFollowStatus(null)).toBe('none')
  })

  it('returns pending for an unaccepted relationship', () => {
    expect(mapFollowStatus({ follower_id: 1, following_id: 2, is_accepted: false })).toBe('pending')
  })

  it('returns accepted for an accepted relationship', () => {
    expect(mapFollowStatus({ follower_id: 1, following_id: 2, is_accepted: true })).toBe('accepted')
  })
})

describe('fetchFollowers', () => {
  it('maps the *follower* (other user) from follower_id', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([
      { follower_id: 3, following_id: 9, is_accepted: true },
      { follower_id: 4, following_id: 9, is_accepted: false },
    ])

    const edges = await fetchFollowers(9)

    expect(apiFetch).toHaveBeenCalledWith('/followers/user/9/followers/all', { signal: undefined })
    expect(edges).toEqual([
      { userId: 3, isAccepted: true },
      { userId: 4, isAccepted: false },
    ])
  })

  it('treats a null payload as an empty list', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(null)
    expect(await fetchFollowers(9)).toEqual([])
  })
})

describe('fetchFollowing', () => {
  it('maps the *followed* (other user) from following_id', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce([
      { follower_id: 9, following_id: 5, is_accepted: true },
    ])

    const edges = await fetchFollowing(9)

    expect(apiFetch).toHaveBeenCalledWith('/followers/user/9/following/all', { signal: undefined })
    expect(edges).toEqual([{ userId: 5, isAccepted: true }])
  })
})

describe('follower counts', () => {
  it('requests the accepted-followers count', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(12)

    expect(await fetchFollowersCount(9)).toBe(12)
    expect(apiFetch).toHaveBeenCalledWith('/followers/user/9/followers/count/accepted', {
      signal: undefined,
    })
  })

  it('requests the accepted-following count', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(7)

    expect(await fetchFollowingCount(9)).toBe(7)
    expect(apiFetch).toHaveBeenCalledWith('/followers/user/9/following/count/accepted', {
      signal: undefined,
    })
  })
})

describe('fetchFollowStatus', () => {
  it('maps the viewer→target relationship to a status', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      follower_id: 1,
      following_id: 2,
      is_accepted: false,
    })

    const status = await fetchFollowStatus(1, 2)

    expect(apiFetch).toHaveBeenCalledWith('/followers/user/1/targetUser/2', { signal: undefined })
    expect(status).toBe('pending')
  })

  it('returns none when there is no relationship', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce(null)
    expect(await fetchFollowStatus(1, 2)).toBe('none')
  })
})

describe('follow-graph mutations', () => {
  it('follows via POST on the create path', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({
      follower_id: 1,
      following_id: 2,
      is_accepted: false,
    })

    await followUser(2)

    expect(apiFetch).toHaveBeenCalledWith('/followers/create/targetUser/2', { method: 'POST' })
  })

  it('accepts a pending request via PUT', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ message: 'ok' })

    await acceptFollower(3)

    expect(apiFetch).toHaveBeenCalledWith('/followers/accept/targetUser/3', { method: 'PUT' })
  })

  it('unfollows (or cancels a request) via DELETE on the follower path', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ message: 'ok' })

    await unfollowUser(4)

    expect(apiFetch).toHaveBeenCalledWith('/followers/delete/follower/targetUser/4', {
      method: 'DELETE',
    })
  })

  it('removes (or declines) a follower via DELETE on the following path', async () => {
    vi.mocked(apiFetch).mockResolvedValueOnce({ message: 'ok' })

    await removeFollower(5)

    expect(apiFetch).toHaveBeenCalledWith('/followers/delete/following/targetUser/5', {
      method: 'DELETE',
    })
  })
})
