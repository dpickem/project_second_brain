import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { captureApi } from '../api/capture';
import { useMediaRecorder } from '../hooks/useMediaRecorder';

/**
 * Voice memo capture component using MediaRecorder API.
 * Records audio and sends for Whisper transcription.
 */
export function VoiceCapture({ onComplete, isOnline }) {
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [expandTranscript, setExpandTranscript] = useState(true);
  
  const audioRef = useRef(null);

  const {
    isRecording,
    duration,
    error: recorderError,
    isSupported,
    startRecording,
    stopRecording,
  } = useMediaRecorder({
    onRecordingComplete: (blob) => {
      console.log('Recording complete, blob:', blob.size, blob.type);
      setAudioBlob(blob);
      setAudioUrl(URL.createObjectURL(blob));
    },
  });

  // Cleanup audio URL on unmount
  useEffect(() => {
    return () => {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const clearRecording = () => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    setAudioBlob(null);
    setAudioUrl(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!audioBlob) {
      toast.error('Please record a voice memo');
      return;
    }

    setIsSubmitting(true);

    try {
      // Determine file extension based on mime type
      const mimeType = audioBlob.type || 'audio/mp4';
      let extension = 'mp4';
      if (mimeType.includes('webm')) extension = 'webm';
      else if (mimeType.includes('ogg')) extension = 'ogg';
      else if (mimeType.includes('wav')) extension = 'wav';
      else if (mimeType.includes('aac')) extension = 'm4a';
      else if (mimeType.includes('mpeg')) extension = 'mp3';
      
      // Create file from blob
      const file = new File(
        [audioBlob], 
        `voice-memo-${Date.now()}.${extension}`, 
        { type: mimeType }
      );
      
      console.log('Uploading voice memo:', file.name, file.size, file.type);

      await captureApi.captureVoice({
        file,
        expand: expandTranscript,
      });

      toast.success(isOnline ? 'Voice memo captured!' : 'Saved offline');
      onComplete();
    } catch (err) {
      console.error('Voice capture failed:', err);
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
        <span className="form-icon">🎤</span>
        <h2>Voice Memo</h2>
      </div>

      {recorderError && (
        <div className="error-banner">
          {recorderError}
        </div>
      )}

      <div className="voice-capture-area">
        {!isSupported ? (
          <div className="recording-controls">
            <p className="hint-text">
              Voice recording is not supported in this browser.
              Please use Safari or Chrome.
            </p>
          </div>
        ) : !audioBlob ? (
          <div className="recording-controls">
            {isRecording ? (
              <>
                <div className="recording-indicator">
                  <span className="recording-dot" />
                  <span className="recording-time">{formatDuration(duration)}</span>
                </div>
                <button
                  type="button"
                  className="record-button stop"
                  onClick={stopRecording}
                >
                  ⏹️ Stop
                </button>
              </>
            ) : (
              <button
                type="button"
                className="record-button start"
                onClick={startRecording}
              >
                🎤 Start Recording
              </button>
            )}
          </div>
        ) : (
          <div className="audio-preview">
            <audio 
              ref={audioRef} 
              src={audioUrl} 
              controls 
              className="audio-player"
            />
            <button
              type="button"
              className="clear-recording"
              onClick={clearRecording}
            >
              🗑️ Discard
            </button>
          </div>
        )}
      </div>

      {/* Expand option */}
      <label className="checkbox-label">
        <input
          type="checkbox"
          checked={expandTranscript}
          onChange={(e) => setExpandTranscript(e.target.checked)}
        />
        <span>Expand into structured note</span>
      </label>

      <p className="hint-text">
        {expandTranscript 
          ? 'Your voice memo will be transcribed and expanded into a well-formatted note.'
          : 'Your voice memo will be transcribed as-is.'}
      </p>

      <button 
        type="submit" 
        className="submit-button"
        disabled={isSubmitting || !audioBlob}
      >
        {isSubmitting ? 'Uploading...' : 'Capture'}
      </button>
    </motion.form>
  );
}

export default VoiceCapture;
