import React, { useState } from 'react';

interface ReviewModalProps {
  isOpen: boolean;
  onSubmit: (rating: number, comment: string) => Promise<void> | void;
  onSkip: () => Promise<void> | void;
  onClose: () => void;
  sessionTitle?: string;
  disabled?: boolean;
}

const Star: React.FC<{ filled: boolean; onClick: () => void; onEnter: () => void; onLeave: () => void; }> = ({ filled, onClick, onEnter, onLeave }) => (
  <button
    type="button"
    className={`text-3xl transition-colors ${filled ? 'text-yellow-400' : 'text-gray-300'} hover:text-yellow-500`}
    onClick={onClick}
    onMouseEnter={onEnter}
    onMouseLeave={onLeave}
    aria-label={filled ? 'Selected star' : 'Unselected star'}
  >
    ★
  </button>
);

const ReviewModal: React.FC<ReviewModalProps> = ({
  isOpen,
  onSubmit,
  onSkip,
  onClose,
  sessionTitle,
  disabled
}) => {
  const [rating, setRating] = useState<number>(0);
  const [hover, setHover] = useState<number>(0);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (!rating) return;
    setSubmitting(true);
    try {
      await onSubmit(rating, comment.trim());
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  const handleSkip = async () => {
    setSubmitting(true);
    try {
      await onSkip();
      onClose();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white w-full max-w-md rounded-xl shadow-lg p-6 animate-fadeIn" role="dialog" aria-modal="true">
        <h2 className="text-lg font-semibold mb-1">Rate Your Last Chat</h2>
        <p className="text-sm text-gray-500 mb-4">{sessionTitle ? `Session: ${sessionTitle}` : 'Previous session'}</p>

        <div className="flex items-center gap-2 mb-4" role="radiogroup" aria-label="Star rating">
          {[1,2,3,4,5].map(num => (
            <Star
              key={num}
              filled={num <= (hover || rating)}
              onClick={() => setRating(num)}
              onEnter={() => setHover(num)}
              onLeave={() => setHover(0)}
            />
          ))}
        </div>

        <textarea
            className="w-full border rounded-lg p-2 text-sm focus:ring focus:ring-blue-300 focus:outline-none mb-4"
            rows={3}
            placeholder="Optional comments to help improve..."
            value={comment}
            onChange={e => setComment(e.target.value)}
            disabled={submitting || disabled}
        />

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={handleSkip}
            disabled={submitting || disabled}
            className="px-4 py-2 text-sm rounded-lg border border-gray-300 text-gray-600 hover:bg-gray-100 disabled:opacity-50"
          >
            Skip
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!rating || submitting || disabled}
            className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? 'Saving...' : 'Submit'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReviewModal;
