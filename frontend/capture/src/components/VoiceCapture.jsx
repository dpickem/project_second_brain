import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { captureApi } from '../api/capture';
import { useMediaRecorder } from '../hooks/useMediaRecorder';
import { CaptureOptions } from './CaptureOptions';

/**
 * Voice memo capture component using MediaRecorder API.
 * Records audio or uploads audio files for Whisper transcription.
 */
export function VoiceCapture({ onComplete, isOnline }) {
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioFileName, setAudioFileName] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [expandTranscript, setExpandTranscript] = useState(true);
  const [createCards, setCreateCards] = useState(false);
  const [createExercises, setCreateExercises] = useState(false);
  
  const audioRef = useRef(null);
  const fileInputRef = useRef(null);

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
    setAudioFileName(null);
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    // Validate audio file
    const validTypes = [
      'audio/mpeg', 'audio/mp3', 'audio/mp4', 'audio/m4a', 'audio/x-m4a',
      'audio/wav', 'audio/webm', 'audio/ogg', 'audio/flac', 'audio/aac'
    ];
    const ext = file.name.split('.').pop()?.toLowerCase();
    const validExts = ['mp3', 'mp4', 'm4a', 'wav', 'webm', 'ogg', 'flac', 'aac'];
    
    if (!validTypes.includes(file.type) && !validExts.includes(ext)) {
      toast.error('Please select a valid audio file (MP3, M4A, WAV, etc.)');
      return;
    }
    
    setAudioBlob(file);
    setAudioUrl(URL.createObjectURL(file));
    setAudioFileName(file.name);
    
    // Reset input so the same file can be selected again
    e.target.value = '';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!audioBlob) {
      toast.error('Please record or upload a voice memo');
      return;
    }

    setIsSubmitting(true);

    try {
      let file;
      
      // If it's already a File (from upload), use it directly
      if (audioBlob instanceof File) {
        file = audioBlob;
      } else {
        // It's a Blob from recording - create a File
        const mimeType = audioBlob.type || 'audio/mp4';
        let extension = 'mp4';
        if (mimeType.includes('webm')) extension = 'webm';
        else if (mimeType.includes('ogg')) extension = 'ogg';
        else if (mimeType.includes('wav')) extension = 'wav';
        else if (mimeType.includes('aac')) extension = 'm4a';
        else if (mimeType.includes('mpeg')) extension = 'mp3';
        
        file = new File(
          [audioBlob], 
          `voice-memo-${Date.now()}.${extension}`, 
          { type: mimeType }
        );
      }
      
      console.log('Uploading voice memo:', file.name, file.size, file.type);

      await captureApi.captureVoice({
        file,
        expand: expandTranscript,
        createCards,
        createExercises,
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
        {audioBlob ? (
          <div className="audio-preview">
            {audioFileName && (
              <p className="audio-filename">{audioFileName}</p>
            )}
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
        ) : (
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
              <>
                {isSupported && (
                  <button
                    type="button"
                    className="record-button start"
                    onClick={startRecording}
                  >
                    🎤 Record
                  </button>
                )}
                {isSupported && <span className="or-divider">or</span>}
                <button
                  type="button"
                  className="photo-action-button"
                  onClick={() => fileInputRef.current?.click()}
                >
                  📁 Upload Audio File
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="audio/*,.mp3,.m4a,.wav,.webm,.ogg,.flac,.aac"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                {!isSupported && (
                  <p className="hint-text" style={{ marginTop: 'var(--space-sm)' }}>
                    Recording requires HTTPS. Upload a voice memo instead.
                  </p>
                )}
              </>
            )}
          </div>
        )}
      </div>

      <CaptureOptions
        createCards={createCards}
        setCreateCards={setCreateCards}
        createExercises={createExercises}
        setCreateExercises={setCreateExercises}
        expandTranscript={expandTranscript}
        setExpandTranscript={setExpandTranscript}
      />

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
