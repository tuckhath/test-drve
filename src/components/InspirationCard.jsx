const TYPE_META = {
  quote: { label: 'Quote', icon: '"', color: 'type-quote' },
  memory: { label: 'Memory', icon: '◈', color: 'type-memory' },
  goal: { label: 'Goal', icon: '◎', color: 'type-goal' },
  idea: { label: 'Idea', icon: '◆', color: 'type-idea' },
}

export default function InspirationCard({ item, isFavorite, onToggleFavorite }) {
  const meta = TYPE_META[item.type] ?? TYPE_META.quote

  return (
    <article className="inspiration-card">
      <div className="card-top">
        <span className={`type-badge ${meta.color}`}>
          <span className="type-icon">{meta.icon}</span>
          {meta.label}
        </span>
        <button
          className={`heart-btn ${isFavorite ? 'favorited' : ''}`}
          onClick={() => onToggleFavorite(item.id)}
          aria-label={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
        >
          {isFavorite ? '♥' : '♡'}
        </button>
      </div>

      <blockquote className="card-content">
        {item.type === 'quote' && (
          <span className="open-quote">"</span>
        )}
        <p>{item.content}</p>
        {item.type === 'quote' && (
          <span className="close-quote">"</span>
        )}
      </blockquote>

      <footer className="card-source">
        <span className="source-dash">—</span>
        <span>{item.source}</span>
      </footer>
    </article>
  )
}
