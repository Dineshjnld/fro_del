import { useState, useRef, useCallback } from 'react';
import type { VoiceRecordingState } from '../types';
import { transcribeAudio } from '../services/voiceService';

export const useVoiceRecording = () => {
  const [state, setState] = useState<VoiceRecordingState>({
    isRecording: false,
    isProcessing: false,
    error: null,
    language: 'te'
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
          sampleRate: 16000
        } 
      });

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        setState(prev => ({ ...prev, isRecording: false, isProcessing: true }));

        try {
          const result = await transcribeAudio(audioBlob, {
            language: state.language,
            enhanceText: true
          });

          setState(prev => ({ ...prev, isProcessing: false }));
          
          // Return the transcription result
          return result;

        } catch (error) {
          setState(prev => ({ 
            ...prev, 
            isProcessing: false, 
            error: error instanceof Error ? error.message : 'Transcription failed' 
          }));
          throw error;
        }
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();

    } catch (error) {
      setState(prev => ({ 
        ...prev, 
        isRecording: false, 
        error: error instanceof Error ? error.message : 'Failed to start recording' 
      }));
      throw error;
    }
  }, [state.language]);

  const stopRecording = useCallback((): Promise<any> => {
    return new Promise((resolve, reject) => {
      if (mediaRecorderRef.current && state.isRecording) {
        mediaRecorderRef.current.onstop = async () => {
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          
          setState(prev => ({ ...prev, isRecording: false, isProcessing: true }));

          try {
            const result = await transcribeAudio(audioBlob, {
              language: state.language,
              enhanceText: true
            });

            setState(prev => ({ ...prev, isProcessing: false }));
            resolve(result);

          } catch (error) {
            setState(prev => ({ 
              ...prev, 
              isProcessing: false, 
              error: error instanceof Error ? error.message : 'Transcription failed' 
            }));
            reject(error);
          }
        };

        mediaRecorderRef.current.stop();
        
        // Stop all tracks
        if (mediaRecorderRef.current.stream) {
          mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
        }
      } else {
        reject(new Error('No active recording'));
      }
    });
  }, [state.isRecording, state.language]);

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