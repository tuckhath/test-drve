const TYPE_META = {
  quote: { label: 'Quote', icon: '"', color: 'type-quote' },
  memory: { label: 'Memory', icon: '◈', color: 'type-memory' },
  goal: { label: 'Goal', icon: '◎', color: 'type-goal' },
  idea: { label: 'Idea', icon: '◆', color: 'type-idea' },
}

export default function FavoritesList({ items, isOpen, onClose, onRemove }) {
  return (
    <aside className={`favorites-panel ${isOpen ? 'open' : ''}`}>
      <div className="favorites-header">
        <h2>
          <span>♥</span> Favorites
        </h2>
        <button className="close-btn" onClick={onClose} aria-label="Close favorites">
          ✕
        </button>
      </div>

      <div className="favorites-body">
        {items.length === 0 ? (
          <div className="favorites-empty">
            <p>♡</p>
            <p>Nothing saved yet.</p>
            <p>Tap the heart on any card to save it here.</p>
          </div>
        ) : (
          <ul className="favorites-list">
            {items.map(item => {
              const meta = TYPE_META[item.type] ?? TYPE_META.quote
              return (
                <li key={item.id} className="favorite-item">
                  <div className="fav-item-top">
                    <span className={`type-badge small ${meta.color}`}>
                      {meta.icon} {meta.label}
                    </span>
                    <button
                      className="remove-btn"
                      onClick={() => onRemove(item.id)}
                      aria-label="Remove from favorites"
                    >
                      ✕
                    </button>
                  </div>
                  <p className="fav-content">{item.content}</p>
                  <p className="fav-source">— {item.source}</p>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </aside>
  )
}
