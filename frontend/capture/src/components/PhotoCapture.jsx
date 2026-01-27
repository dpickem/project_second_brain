import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { captureApi } from '../api/capture';
import { CaptureOptions } from './CaptureOptions';

const CAPTURE_TYPES = [
  { value: 'book_page', label: '📖 Book Page', multi: true },
  { value: 'whiteboard', label: '📋 Whiteboard', multi: false },
  { value: 'document', label: '📄 Document', multi: false },
  { value: 'general', label: '📷 General', multi: false },
];

/**
 * Photo capture component using device camera or file picker.
 * Supports book pages (multiple photos), whiteboards, documents, and general photos.
 * 
 * Uses native file inputs with capture attribute for reliable camera access
 * on mobile devices (especially iOS) instead of getUserMedia API.
 */
export function PhotoCapture({ onComplete, isOnline }) {
  // Store array of {file, preview} objects
  const [photos, setPhotos] = useState([]);
  const [captureType, setCaptureType] = useState('book_page');
  const [notes, setNotes] = useState('');
  const [bookTitle, setBookTitle] = useState('');
  const [createCards, setCreateCards] = useState(false);
  const [createExercises, setCreateExercises] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Two separate file inputs: one for camera, one for photo library
  const cameraInputRef = useRef(null);
  const libraryInputRef = useRef(null);

  // Check if current capture type supports multiple photos
  const supportsMultiple = CAPTURE_TYPES.find(t => t.value === captureType)?.multi ?? false;

  // Cleanup preview URLs on unmount
  useEffect(() => {
    return () => {
      photos.forEach(p => URL.revokeObjectURL(p.preview));
    };
  }, []);

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    
    if (supportsMultiple) {
      // Add to existing photos
      const newPhotos = files.map(file => ({
        file,
        preview: URL.createObjectURL(file),
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      }));
      setPhotos(prev => [...prev, ...newPhotos]);
    } else {
      // Replace existing photo (single mode)
      photos.forEach(p => URL.revokeObjectURL(p.preview));
      const file = files[0];
      setPhotos([{
        file,
        preview: URL.createObjectURL(file),
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      }]);
    }
    
    // Reset input so the same file can be selected again if needed
    e.target.value = '';
  };

  const removePhoto = (id) => {
    setPhotos(prev => {
      const photo = prev.find(p => p.id === id);
      if (photo) {
        URL.revokeObjectURL(photo.preview);
      }
      return prev.filter(p => p.id !== id);
    });
  };

  const clearAllPhotos = () => {
    photos.forEach(p => URL.revokeObjectURL(p.preview));
    setPhotos([]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (photos.length === 0) {
      toast.error('Please take or select a photo');
      return;
    }

    setIsSubmitting(true);

    try {
      // Use book endpoint for multiple book pages, photo endpoint otherwise
      if (captureType === 'book_page' && photos.length > 1) {
        await captureApi.captureBook({
          files: photos.map(p => p.file),
          title: bookTitle.trim() || undefined,
          notes: notes.trim() || undefined,
          createCards,
          createExercises,
        });
        toast.success(isOnline ? `${photos.length} pages captured!` : 'Saved offline');
      } else {
        // Single photo - use photo endpoint
        await captureApi.capturePhoto({
          file: photos[0].file,
          captureType,
          notes: notes.trim() || undefined,
          bookTitle: captureType === 'book_page' ? bookTitle.trim() || undefined : undefined,
          createCards,
          createExercises,
        });
        toast.success(isOnline ? 'Photo captured!' : 'Saved offline');
      }

      onComplete();
    } catch (err) {
      toast.error(err.message || 'Capture failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <motion.form 
      className="capture-form"
      onSubmit={handleSubmit}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div className="form-header">
        <span className="form-icon">📷</span>
        <h2>Photo Capture</h2>
      </div>

      {/* Capture type selector */}
      <div className="capture-type-selector">
        {CAPTURE_TYPES.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            className={`type-button ${captureType === value ? 'active' : ''}`}
            onClick={() => setCaptureType(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Camera/Photo area */}
      <div className="photo-capture-area">
        {photos.length > 0 ? (
          <div className="photos-preview-container">
            <div className="photos-grid">
              <AnimatePresence>
                {photos.map((photo, index) => (
                  <motion.div
                    key={photo.id}
                    className="photo-preview-item"
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.8 }}
                  >
                    <img src={photo.preview} alt={`Photo ${index + 1}`} />
                    <span className="photo-number">{index + 1}</span>
                    <button
                      type="button"
                      className="remove-photo"
                      onClick={() => removePhoto(photo.id)}
                    >
                      ✕
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
            <div className="photos-actions">
              {supportsMultiple && (
                <>
                  <button
                    type="button"
                    className="photo-action-button small"
                    onClick={() => cameraInputRef.current?.click()}
                  >
                    📷 Add More
                  </button>
                  <button
                    type="button"
                    className="photo-action-button small"
                    onClick={() => libraryInputRef.current?.click()}
                  >
                    🖼️ Add from Library
                  </button>
                </>
              )}
              <button
                type="button"
                className="photo-action-button small danger"
                onClick={clearAllPhotos}
              >
                🗑️ Clear All
              </button>
            </div>
            {/* Hidden inputs for adding more */}
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileSelect}
              className="hidden"
            />
            <input
              ref={libraryInputRef}
              type="file"
              accept="image/*"
              multiple={supportsMultiple}
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
        ) : (
          <div className="photo-input-area">
            <button
              type="button"
              className="photo-action-button"
              onClick={() => cameraInputRef.current?.click()}
            >
              📷 Take Photo
            </button>
            <span className="or-divider">or</span>
            <button
              type="button"
              className="photo-action-button"
              onClick={() => libraryInputRef.current?.click()}
            >
              🖼️ Choose from Library
            </button>
            {supportsMultiple && (
              <p className="hint-text" style={{ marginTop: 'var(--space-sm)', textAlign: 'center' }}>
                You can select multiple photos for book pages
              </p>
            )}
            {/* Camera input - opens native camera app on mobile */}
            <input
              ref={cameraInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileSelect}
              className="hidden"
            />
            {/* Library input - opens photo picker without camera */}
            <input
              ref={libraryInputRef}
              type="file"
              accept="image/*"
              multiple={supportsMultiple}
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
        )}
      </div>

      <CaptureOptions
        bookTitle={captureType === 'book_page' ? bookTitle : undefined}
        setBookTitle={captureType === 'book_page' ? setBookTitle : undefined}
        notes={notes}
        setNotes={setNotes}
        notesPlaceholder="Notes (optional)"
        createCards={createCards}
        setCreateCards={setCreateCards}
        createExercises={createExercises}
        setCreateExercises={setCreateExercises}
      />

      <button 
        type="submit" 
        className="submit-button"
        disabled={isSubmitting || photos.length === 0}
      >
        {isSubmitting 
          ? 'Uploading...' 
          : photos.length > 1 
            ? `Capture ${photos.length} Photos` 
            : 'Capture'}
      </button>
    </motion.form>
  );
}

export default PhotoCapture;
