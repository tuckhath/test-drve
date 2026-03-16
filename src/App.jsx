import { useState, useEffect, useCallback } from 'react'
import collection from './data/collection.json'
import InspirationCard from './components/InspirationCard'
import ActionBar from './components/ActionBar'
import FavoritesList from './components/FavoritesList'

const STORAGE_KEY = 'daily-inspiration-state'
const FAVORITES_KEY = 'daily-inspiration-favorites'

function getTodayString() {
  return new Date().toISOString().slice(0, 10)
}

// Deterministic index from a seed string
function seededIndex(seed, length) {
  let hash = 0
  for (let i = 0; i < seed.length; i++) {
    hash = ((hash << 5) - hash + seed.charCodeAt(i)) | 0
  }
  return Math.abs(hash) % length
}

function getItemForDay(dateStr, shuffleOffset) {
  const seed = dateStr + ':' + shuffleOffset
  return seededIndex(seed, collection.length)
}

export default function App() {
  const [today] = useState(getTodayString)

  const [shuffleOffset, setShuffleOffset] = useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY))
      if (saved?.date === getTodayString()) return saved.shuffleOffset ?? 0
    } catch (_) {}
    return 0
  })

  const [favorites, setFavorites] = useState(() => {
    try {
      return new Set(JSON.parse(localStorage.getItem(FAVORITES_KEY)) ?? [])
    } catch (_) {
      return new Set()
    }
  })

  const [showFavorites, setShowFavorites] = useState(false)
  const [animating, setAnimating] = useState(false)

  const currentIndex = getItemForDay(today, shuffleOffset)
  const currentItem = collection[currentIndex]

  // Persist shuffle state
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ date: today, shuffleOffset }))
  }, [today, shuffleOffset])

  // Persist favorites
  useEffect(() => {
    localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites]))
  }, [favorites])

  const handleShowAnother = useCallback(() => {
    setAnimating(true)
    setTimeout(() => {
      setShuffleOffset(n => n + 1)
      setAnimating(false)
    }, 300)
  }, [])

  const handleToggleFavorite = useCallback((id) => {
    setFavorites(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const favoriteItems = collection.filter(item => favorites.has(item.id))

  const formattedDate = new Date(today + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <div className="header-title">
            <span className="header-icon">✦</span>
            <h1>Daily Inspiration</h1>
          </div>
          <button
            className={`favorites-toggle ${showFavorites ? 'active' : ''}`}
            onClick={() => setShowFavorites(v => !v)}
            aria-label="View favorites"
          >
            <span className="heart-icon">♥</span>
            <span>Favorites</span>
            {favorites.size > 0 && (
              <span className="badge">{favorites.size}</span>
            )}
          </button>
        </div>
      </header>

      <main className="app-main">
        <p className="date-label">{formattedDate}</p>

        <div className={`card-wrapper ${animating ? 'fade-out' : 'fade-in'}`}>
          <InspirationCard
            item={currentItem}
            isFavorite={favorites.has(currentItem.id)}
            onToggleFavorite={handleToggleFavorite}
          />
        </div>

        <ActionBar
          onShowAnother={handleShowAnother}
          isFavorite={favorites.has(currentItem.id)}
          onToggleFavorite={() => handleToggleFavorite(currentItem.id)}
        />
      </main>

      <FavoritesList
        items={favoriteItems}
        isOpen={showFavorites}
        onClose={() => setShowFavorites(false)}
        onRemove={(id) => handleToggleFavorite(id)}
      />

      {showFavorites && (
        <div className="overlay" onClick={() => setShowFavorites(false)} />
      )}
    </div>
  )
}
