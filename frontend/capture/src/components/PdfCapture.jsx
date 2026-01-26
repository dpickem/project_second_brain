import { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { captureApi } from '../api/capture';
import { CaptureOptions } from './CaptureOptions';

const CONTENT_TYPES = [
  { value: 'paper', label: '📄 Paper' },
  { value: 'article', label: '📰 Article' },
  { value: 'book', label: '📚 Book' },
  { value: 'general', label: '📋 General' },
];

/**
 * PDF capture component.
 * Uploads PDFs for text extraction and annotation processing.
 */
export function PdfCapture({ onComplete, isOnline, initialFile = null }) {
  const [file, setFile] = useState(initialFile);
  const [contentType, setContentType] = useState('general');
  const [detectHandwriting, setDetectHandwriting] = useState(true);
  const [createCards, setCreateCards] = useState(false);
  const [createExercises, setCreateExercises] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const fileInputRef = useRef(null);

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.type !== 'application/pdf' && !selectedFile.name.endsWith('.pdf')) {
        toast.error('Please select a PDF file');
        return;
      }
      setFile(selectedFile);
    }
  };

  const clearFile = () => {
    setFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      toast.error('Please select a PDF file');
      return;
    }

    setIsSubmitting(true);

    try {
      await captureApi.capturePdf({
        file,
        contentTypeHint: contentType,
        detectHandwriting,
        createCards,
        createExercises,
      });

      toast.success(isOnline ? 'PDF captured!' : 'Saved offline');
      onComplete();
    } catch (err) {
      console.error('PDF capture failed:', err);
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
        <span className="form-icon">📑</span>
        <h2>PDF Upload</h2>
      </div>

      {/* Content type selector */}
      <div className="capture-type-selector">
        {CONTENT_TYPES.map(({ value, label }) => (
          <button
            key={value}
            type="button"
            className={`type-button ${contentType === value ? 'active' : ''}`}
            onClick={() => setContentType(value)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* File selection area */}
      <div className="photo-capture-area">
        {file ? (
          <div className="file-preview">
            <div className="file-info">
              <span className="file-icon">📄</span>
              <div className="file-details">
                <span className="file-name">{file.name}</span>
                <span className="file-size">{formatFileSize(file.size)}</span>
              </div>
            </div>
            <button
              type="button"
              className="clear-file"
              onClick={clearFile}
            >
              ✕
            </button>
          </div>
        ) : (
          <div className="photo-input-area">
            <button
              type="button"
              className="photo-action-button"
              onClick={() => fileInputRef.current?.click()}
            >
              📄 Choose PDF
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf,.pdf"
              onChange={handleFileSelect}
              className="hidden"
            />
          </div>
        )}
      </div>

      <CaptureOptions
        createCards={createCards}
        setCreateCards={setCreateCards}
        createExercises={createExercises}
        setCreateExercises={setCreateExercises}
        detectHandwriting={detectHandwriting}
        setDetectHandwriting={setDetectHandwriting}
      />

      <button 
        type="submit" 
        className="submit-button"
        disabled={isSubmitting || !file}
      >
        {isSubmitting ? 'Uploading...' : 'Capture'}
      </button>
    </motion.form>
  );
}

export default PdfCapture;
