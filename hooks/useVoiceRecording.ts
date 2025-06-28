import { useState, useRef, useCallback } from 'react';
import type { VoiceRecordingState } from '../types'; // Adjusted path
import { transcribeAudio } from '../services/voiceService'; // Adjusted path

export const useVoiceRecording = () => {
  const [state, setState] = useState<VoiceRecordingState>({
    isRecording: false,
    isProcessing: false,
    error: null,
    language: 'te' // Default language
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, isRecording: true, error: null }));

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000 // Explicitly set sample rate
        }
      });

      // Determine a suitable MIME type, preferring webm but falling back if necessary
      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        console.warn(`${mimeType} not supported, trying audio/ogg;codecs=opus`);
        mimeType = 'audio/ogg;codecs=opus';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          console.warn(`${mimeType} not supported, trying audio/wav`);
          mimeType = 'audio/wav'; // Fallback, though often uncompressed and large
           if (!MediaRecorder.isTypeSupported(mimeType)) {
            console.warn(`${mimeType} not supported, using default`);
            mimeType = ''; // Let the browser decide
          }
        }
      }

      const mediaRecorderOptions: MediaRecorderOptions = {};
      if (mimeType) {
        mediaRecorderOptions.mimeType = mimeType;
      }


      const mediaRecorder = new MediaRecorder(stream, mediaRecorderOptions);
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // This onstop is for when recording is initiated and then stopped by user/timeout
      // The stopRecording function below has its own onstop logic for explicit calls
      mediaRecorder.onstop = async () => {
        // This is usually handled by the explicit stopRecording call's onstop
        // but can act as a fallback.
        console.log("Implicit mediaRecorder.onstop triggered");
        // To avoid double processing if stopRecording is called, check state.
        if (state.isProcessing || !audioChunksRef.current.length) return;

        const audioBlob = new Blob(audioChunksRef.current, { type: mediaRecorderOptions.mimeType || 'audio/webm' });
        setState(prev => ({ ...prev, isRecording: false, isProcessing: true }));
        try {
          // Note: transcribeAudio is already called in stopRecording's logic.
          // This might be redundant if stopRecording is always the one to finalize.
          // For safety, ensure it doesn't get called twice.
          // The `stopRecording` method is now the primary way to get the result.
        } catch (error) {
          // Error handling is done in stopRecording
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();

    } catch (error) {
      console.error("Error starting recording:", error);
      let errorMessage = 'Failed to start recording. Please ensure microphone access is allowed.';
      if (error instanceof Error) {
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
          errorMessage = 'Microphone access was denied. Please enable it in your browser settings.';
        } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
          errorMessage = 'No microphone found. Please ensure a microphone is connected and enabled.';
        } else {
          errorMessage = error.message;
        }
      }
      setState(prev => ({
        ...prev,
        isRecording: false,
        error: errorMessage
      }));
      // Do not re-throw here, allow UI to show error from state
    }
  }, [state.language]); // Removed state from dependency array to avoid re-creating startRecording too often

  const stopRecording = useCallback((): Promise<any> => {
    return new Promise((resolve, reject) => {
      if (mediaRecorderRef.current && (state.isRecording || mediaRecorderRef.current.state === "recording")) {

        // Set up the onstop handler for this specific call to stopRecording
        mediaRecorderRef.current.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: mediaRecorderRef.current?.mimeType || 'audio/webm' });

          setState(prev => ({ ...prev, isRecording: false, isProcessing: true, error: null }));

          try {
            const result = await transcribeAudio(audioBlob, {
              language: state.language,
              // enhanceText: true, // Removed as per voiceService update
            });

            setState(prev => ({ ...prev, isProcessing: false }));
            resolve(result);

          } catch (error) {
             let errorMessage = 'Transcription failed.';
             if (error instanceof Error) {
                errorMessage = error.message;
             }
            setState(prev => ({
              ...prev,
              isProcessing: false,
              error: errorMessage
            }));
            reject(new Error(errorMessage)); // Reject the promise with an Error object
          } finally {
             // Clean up stream tracks
            if (mediaRecorderRef.current?.stream) {
                mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
            }
            mediaRecorderRef.current = null; // Important to clear ref after tracks are stopped.
          }
        };

        // Check if recorder is actually recording before trying to stop.
        if (mediaRecorderRef.current.state === "recording") {
            mediaRecorderRef.current.stop();
        } else if (mediaRecorderRef.current.state === "inactive") {
            // If it's already inactive, it means ondataavailable might not have been called recently.
            // Process any existing chunks. This case might happen if stop is called rapidly after start.
            if (audioChunksRef.current.length > 0) {
                 // Directly trigger the processing part of the onstop logic
                 mediaRecorderRef.current.onstop();
            } else {
                // No data and not recording, resolve or reject based on what's appropriate
                // This might indicate an issue or just a quick toggle.
                setState(prev => ({ ...prev, isRecording: false, isProcessing: false }));
                resolve(null); // Or reject(new Error('No audio data recorded'));
            }
        }


      } else {
        // Not recording or recorder not initialized.
        // Clean up any existing stream just in case.
        if (mediaRecorderRef.current?.stream) {
            mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
        mediaRecorderRef.current = null;
        setState(prev => ({ ...prev, isRecording: false, isProcessing: false })); // Ensure states are reset
        reject(new Error('No active recording to stop.'));
      }
    });
  }, [state.isRecording, state.language]); // state.language is needed for transcribeAudio call

  const setLanguage = useCallback((language: string) => {
    setState(prev => ({ ...prev, language }));
  }, []);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  return {
    state,
    startRecording,
    stopRecording,
    setLanguage,
    clearError
  };
};
