import { useState, useEffect } from 'react'

/**
 * JSON state synced to localStorage.
 * @template T
 * @param {string} key
 * @param {T} defaultValue
 * @returns {[T, import('react').Dispatch<import('react').SetStateAction<T>>]}
 */
export function usePersistedJsonState(key, defaultValue) {
  const [state, setState] = useState(() => {
    try {
      const saved = localStorage.getItem(key)
      return saved ? JSON.parse(saved) : defaultValue
    } catch {
      return defaultValue
    }
  })

  useEffect(() => {
    localStorage.setItem(key, JSON.stringify(state))
  }, [key, state])

  return [state, setState]
}
