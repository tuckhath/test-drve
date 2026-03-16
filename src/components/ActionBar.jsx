export default function ActionBar({ onShowAnother, isFavorite, onToggleFavorite }) {
  return (
    <div className="action-bar">
      <button className="btn-primary" onClick={onShowAnother}>
        <span className="btn-icon">↻</span>
        Show me another
      </button>
      <button
        className={`btn-secondary ${isFavorite ? 'favorited' : ''}`}
        onClick={onToggleFavorite}
      >
        <span className="btn-icon">{isFavorite ? '♥' : '♡'}</span>
        {isFavorite ? 'Saved' : 'Save to favorites'}
      </button>
    </div>
  )
}
