import { useState, useRef, useCallback, useEffect } from 'react';

/**
 * Detect if running on iOS
 */
function isIOS() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent) || 
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
}

/**
 * Get the best supported audio mime type for the current browser
 */
function getSupportedMimeType() {
  // Order of preference - iOS needs mp4/m4a, others prefer webm
  const mimeTypes = isIOS()
    ? [
        'audio/mp4',
        'audio/aac',
        'audio/mpeg',
        'audio/wav',
        '', // fallback to browser default
      ]
    : [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        '', // fallback to browser default
      ];
  
  for (const mimeType of mimeTypes) {
    if (mimeType === '' || (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(mimeType))) {
      console.log('Using audio mime type:', mimeType || 'browser default');
      return mimeType;
    }
  }
  
  return '';
}

/**
 * Hook for recording audio using MediaRecorder API.
 * 
 * @param {Object} options
 * @param {Function} options.onRecordingComplete - Callback when recording finishes with the audio blob
 * @param {number} options.maxDuration - Maximum recording duration in seconds (default: 300 = 5 min)
 */
export function useMediaRecorder({ 
  onRecordingComplete, 
  maxDuration = 300 
} = {}) {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState(null);
  const [isSupported, setIsSupported] = useState(true);
  
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);

  // Check MediaRecorder and mediaDevices support on mount
  useEffect(() => {
    // Check if we're in a secure context (HTTPS or localhost)
    const isSecureContext = window.isSecureContext || 
      window.location.protocol === 'https:' || 
      window.location.hostname === 'localhost' ||
      window.location.hostname === '127.0.0.1';
    
    if (!isSecureContext) {
      setIsSupported(false);
      setError('Voice recording requires HTTPS. Please access via https:// or localhost.');
      return;
    }
    
    // Check for mediaDevices API
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setIsSupported(false);
      setError('Voice recording is not supported in this browser. Please use Safari or Chrome.');
      return;
    }
    
    // Check for MediaRecorder API
    if (typeof MediaRecorder === 'undefined') {
      setIsSupported(false);
      setError('Voice recording is not supported in this browser.');
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  const startRecording = useCallback(async () => {
    // Check if mediaDevices is available (requires HTTPS)
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setError('Voice recording requires HTTPS. Please access via https:// or localhost.');
      return;
    }
    
    // Check if MediaRecorder is available
    if (typeof MediaRecorder === 'undefined') {
      setError('Voice recording is not supported in this browser. Try using Safari or Chrome.');
      return;
    }
    
    try {
      setError(null);
      chunksRef.current = [];
      
      console.log('Requesting microphone access...');
      
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100,
        } 
      });
      
      console.log('Microphone access granted');
      streamRef.current = stream;
      
      // Determine supported mime type
      const mimeType = getSupportedMimeType();
      
      // Create MediaRecorder with options
      const options = mimeType ? { mimeType } : {};
      console.log('Creating MediaRecorder with options:', options);
      
      const mediaRecorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = mediaRecorder;
      
      console.log('MediaRecorder created, state:', mediaRecorder.state);
      
      mediaRecorder.ondataavailable = (event) => {
        console.log('Data available, size:', event.data.size);
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        console.log('Recording stopped, chunks:', chunksRef.current.length);
        const finalMimeType = mediaRecorder.mimeType || mimeType || 'audio/mp4';
        const blob = new Blob(chunksRef.current, { type: finalMimeType });
        console.log('Created blob, size:', blob.size, 'type:', blob.type);
        onRecordingComplete?.(blob);
        
        // Stop all tracks
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
      };
      
      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        setError('Recording failed. Please try again.');
        setIsRecording(false);
        
        // Cleanup
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
      };
      
      // Start recording - iOS needs longer timeslice or no timeslice
      const timeslice = isIOS() ? undefined : 1000;
      console.log('Starting recording with timeslice:', timeslice);
      mediaRecorder.start(timeslice);
      setIsRecording(true);
      setDuration(0);
      
      console.log('Recording started, state:', mediaRecorder.state);
      
      // Start duration timer
      timerRef.current = setInterval(() => {
        setDuration((d) => {
          const newDuration = d + 1;
          
          // Auto-stop at max duration
          if (newDuration >= maxDuration) {
            mediaRecorderRef.current?.stop();
            clearInterval(timerRef.current);
            setIsRecording(false);
          }
          
          return newDuration;
        });
      }, 1000);
      
    } catch (err) {
      console.error('Failed to start recording:', err);
      
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setError('Microphone access denied. Please allow microphone permissions in Settings.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        setError('No microphone found. Please connect a microphone.');
      } else if (err.name === 'NotSupportedError') {
        setError('Voice recording is not supported in this browser.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        setError('Microphone is in use by another app. Please close other apps using the microphone.');
      } else {
        setError(`Recording failed: ${err.message || 'Unknown error'}`);
      }
    }
  }, [onRecordingComplete, maxDuration]);

  const stopRecording = useCallback(() => {
    console.log('Stopping recording...');
    
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, []);

  return {
    isRecording,
    duration,
    error,
    isSupported,
    startRecording,
    stopRecording,
  };
}

export default useMediaRecorder;
