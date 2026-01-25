import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { captureApi } from '../api/capture';

const CAPTURE_TYPES = [
  { value: 'book_page', label: '📖 Book Page' },
  { value: 'whiteboard', label: '📋 Whiteboard' },
  { value: 'document', label: '📄 Document' },
  { value: 'general', label: '📷 General' },
];

/**
 * Photo capture component using device camera or file picker.
 * Supports book pages, whiteboards, documents, and general photos.
 */
export function PhotoCapture({ onComplete, isOnline }) {
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState(null);
  const [captureType, setCaptureType] = useState('book_page');
  const [notes, setNotes] = useState('');
  const [bookTitle, setBookTitle] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [useCamera, setUseCamera] = useState(false);
  const [cameraError, setCameraError] = useState(null);
  
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  // Start camera when useCamera is true
  useEffect(() => {
    if (useCamera) {
      startCamera();
    }
    return () => stopCamera();
  }, [useCamera]);

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'environment', // Use back camera
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      });
      
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraError(null);
    } catch (err) {
      console.error('Camera access failed:', err);
      setCameraError('Camera access denied. Please allow camera permissions.');
      setUseCamera(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
  };

  const captureFromCamera = () => {
    if (!videoRef.current || !canvasRef.current) return;
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    
    canvas.toBlob((blob) => {
      const file = new File([blob], `capture-${Date.now()}.jpg`, { type: 'image/jpeg' });
      setPhoto(file);
      setPreview(URL.createObjectURL(blob));
      stopCamera();
      setUseCamera(false);
    }, 'image/jpeg', 0.9);
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      setPhoto(file);
      setPreview(URL.createObjectURL(file));
    }
  };

  const clearPhoto = () => {
    setPhoto(null);
    if (preview) {
      URL.revokeObjectURL(preview);
      setPreview(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!photo) {
      toast.error('Please take or select a photo');
      return;
    }

    setIsSubmitting(true);

    try {
      await captureApi.capturePhoto({
        file: photo,
        captureType,
        notes: notes.trim() || undefined,
        bookTitle: captureType === 'book_page' ? bookTitle.trim() || undefined : undefined,
      });

      toast.success(isOnline ? 'Photo captured!' : 'Saved offline');
      onComplete();
    } catch (err) {
      console.error('Photo capture failed:', err);
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
        {useCamera ? (
          <div className="camera-view">
            <video 
              ref={videoRef} 
              autoPlay 
              playsInline 
              muted
              className="camera-preview"
            />
            <canvas ref={canvasRef} className="hidden" />
            <div className="camera-controls">
              <button
                type="button"
                className="camera-button cancel"
                onClick={() => {
                  stopCamera();
                  setUseCamera(false);
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="camera-button capture"
                onClick={captureFromCamera}
              >
                📸 Take Photo
              </button>
            </div>
          </div>
        ) : preview ? (
          <div className="photo-preview">
            <img src={preview} alt="Captured" />
            <button
              type="button"
              className="clear-photo"
              onClick={clearPhoto}
            >
              ✕
            </button>
          </div>
        ) : (
          <div className="photo-input-area">
            {cameraError && (
              <p className="camera-error">{cameraError}</p>
            )}
            <button
              type="button"
              className="photo-action-button"
              onClick={() => setUseCamera(true)}
            >
              📷 Use Camera
            </button>
            <span className="or-divider">or</span>
            <button
              type="button"
              className="photo-action-button"
              onClick={() => fileInputRef.current?.click()}
            >
              🖼️ Choose Photo
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
        )}
      </div>

      {/* Book title field (only for book_page) */}
      {captureType === 'book_page' && (
        <input
          type="text"
          className="capture-input"
          placeholder="Book title (optional)"
          value={bookTitle}
          onChange={(e) => setBookTitle(e.target.value)}
        />
      )}

      {/* Notes field */}
      <textarea
        className="capture-textarea capture-textarea-small"
        placeholder="Notes (optional)"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={2}
      />

      <button 
        type="submit" 
        className="submit-button"
        disabled={isSubmitting || !photo}
      >
        {isSubmitting ? 'Uploading...' : 'Capture'}
      </button>
    </motion.form>
  );
}

export default PhotoCapture;
