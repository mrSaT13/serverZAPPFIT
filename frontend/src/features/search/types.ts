/**
 * The entity scope a global search runs against. Mirrors v1's three search
 * modes (users, activities, gear); the active scope selects which backend
 * "contains" endpoint the search box queries.
 */
export type SearchScope = 'users' | 'activities' | 'gears'
