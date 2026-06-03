/**
 * Audio utility functions for file processing and validation
 */

import { MAX_AUDIO_FILE_SIZE, MIN_AUDIO_FILE_SIZE, AUDIO_DURATION_TIMEOUT_MS } from '@/constants/audio';

export async function getAudioDuration(file: File): Promise<number> {
  // First, try to get duration from Web Audio API if available
  if (typeof window !== 'undefined' && (window.AudioContext || (window as any).webkitAudioContext)) {
    try {
      return await tryWebAudioDuration(file);
    } catch (webAudioError) {
      console.warn('Web Audio API failed, falling back to HTML Audio:', webAudioError);
      // Fallback to HTML Audio element
      try {
        return await tryHTMLAudioDuration(file);
      } catch (htmlAudioError) {
        console.error('Both Web Audio and HTML Audio failed:', htmlAudioError);
        throw htmlAudioError;
      }
    }
  } else {
    // Fallback to HTML Audio element
    return await tryHTMLAudioDuration(file);
  }
}

function tryWebAudioDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    // Check if we're in a browser environment
    if (typeof window === 'undefined' || typeof FileReader === 'undefined') {
      reject(new Error('Web Audio API not available in this environment'));
      return;
    }

    const reader = new FileReader();
    
    reader.onload = async () => {
      try {
        const AudioContext = window.AudioContext || (window as any).webkitAudioContext;
        if (!AudioContext) {
          reject(new Error('AudioContext not available'));
          return;
        }
        
        const audioContext = new AudioContext();
        const arrayBuffer = reader.result as ArrayBuffer;
        
        if (!arrayBuffer) {
          reject(new Error('Failed to read file as ArrayBuffer'));
          return;
        }
        
        const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
        audioContext.close();
        resolve(audioBuffer.duration);
      } catch (error) {
        reject(error);
      }
    };
    
    reader.onerror = () => reject(new Error('Fehler beim Lesen der Datei'));
    reader.readAsArrayBuffer(file);
  });
}

function tryHTMLAudioDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    // Check if we're in a browser environment
    if (typeof window === 'undefined' || typeof URL === 'undefined' || typeof Audio === 'undefined') {
      reject(new Error('HTML Audio API not available in this environment'));
      return;
    }

    const url = URL.createObjectURL(file);
    const audio = new Audio();
    
    // Set a timeout to avoid hanging indefinitely
    const timeout = setTimeout(() => {
      URL.revokeObjectURL(url);
      reject(new Error('Timeout beim Laden der Audiodatei'));
    }, AUDIO_DURATION_TIMEOUT_MS);
    
    let resolved = false;
    
    const cleanup = () => {
      if (!resolved) {
        resolved = true;
        clearTimeout(timeout);
        URL.revokeObjectURL(url);
      }
    };
    
    audio.addEventListener('loadedmetadata', () => {
      if (resolved) return;
      
      // Check if duration is valid
      if (isNaN(audio.duration) || !isFinite(audio.duration) || audio.duration <= 0) {
        cleanup();
        reject(new Error('Ungültige Audiodauer ermittelt'));
        return;
      }
      
      cleanup();
      resolve(audio.duration);
    });
    
    audio.addEventListener('error', () => {
      if (resolved) return;
      cleanup();
      reject(new Error('Fehler beim Laden der Audiodatei'));
    });
    
    audio.addEventListener('abort', () => {
      if (resolved) return;
      cleanup();
      reject(new Error('Laden der Audiodatei wurde abgebrochen'));
    });
    
    // Try to load the audio
    try {
      audio.preload = 'metadata';
      audio.src = url;
      audio.load();
    } catch (loadError) {
      cleanup();
      reject(loadError);
    }
  });
}

// Improved fallback method using file size estimation
export function estimateAudioDuration(file: File): number {
  // Get file extension to determine likely format and bitrate
  const fileName = file.name.toLowerCase();
  let estimatedBitrate = 128; // Default 128 kbps
  
  if (fileName.endsWith('.mp3')) {
    estimatedBitrate = 128; // Typical MP3 bitrate
  } else if (fileName.endsWith('.wav') || fileName.endsWith('.flac')) {
    estimatedBitrate = 1411; // Uncompressed audio (44.1kHz * 16bit * 2channels)
  } else if (fileName.endsWith('.aac') || fileName.endsWith('.m4a')) {
    estimatedBitrate = 128; // Typical AAC bitrate
  } else if (fileName.endsWith('.ogg')) {
    estimatedBitrate = 112; // Typical OGG Vorbis bitrate
  } else if (fileName.endsWith('.webm')) {
    estimatedBitrate = 128; // Typical WebM audio bitrate
  }
  
  // Convert bitrate to bytes per second
  const bytesPerSecond = (estimatedBitrate * 1000) / 8;
  const estimatedDuration = file.size / bytesPerSecond;
  
  // Ensure minimum reasonable duration (0.1 seconds)
  return Math.max(0.1, estimatedDuration);
}

// Get audio duration with automatic fallback
export async function getAudioDurationWithFallback(file: File): Promise<number> {
  // Ensure we're running in browser environment
  if (typeof window === 'undefined') {
    console.warn('getAudioDurationWithFallback called in non-browser environment');
    return estimateAudioDuration(file);
  }

  try {
    return await getAudioDuration(file);
  } catch (error) {
    console.warn('Audio duration detection failed, using estimation:', error);
    return estimateAudioDuration(file);
  }
}

export function validateAudioFile(file: File): { isValid: boolean; error?: string } {
  // List of common audio MIME types
  const supportedTypes = [
    'audio/mpeg', 'audio/mp3', 'audio/mp4', 'audio/wav', 'audio/wave',
    'audio/webm', 'audio/ogg', 'audio/aac', 'audio/flac', 'audio/m4a',
    'audio/x-wav', 'audio/x-flac', 'audio/x-mp3'
  ];
  
  // Check file extension as fallback
  const supportedExtensions = ['.mp3', '.wav', '.mp4', '.m4a', '.webm', '.ogg', '.aac', '.flac'];
  const fileName = file.name.toLowerCase();
  const hasValidExtension = supportedExtensions.some(ext => fileName.endsWith(ext));
  
  // Check MIME type
  const hasValidMimeType = supportedTypes.includes(file.type.toLowerCase()) || file.type.startsWith('audio/');
  
  if (!hasValidMimeType && !hasValidExtension) {
    return {
      isValid: false,
      error: `Ungültiger Dateityp: "${file.type || 'unbekannt'}". Unterstützte Formate: MP3, WAV, MP4, M4A, WebM, OGG, AAC, FLAC.`
    };
  }
  
  // Check file size (limit to 100MB)
  if (file.size > MAX_AUDIO_FILE_SIZE) {
    return {
      isValid: false,
      error: `Datei ist zu groß (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximale Größe: 100MB.`
    };
  }
  
  // Check minimum file size (1KB)
  if (file.size < MIN_AUDIO_FILE_SIZE) {
    return {
      isValid: false,
      error: 'Datei ist zu klein. Minimale Größe: 1KB.'
    };
  }
  
  return { isValid: true };
}

// Test if browser can handle audio files
export function testAudioSupport(): boolean {
  // Check if we're in browser environment
  if (typeof window === 'undefined' || typeof Audio === 'undefined') {
    return false;
  }

  try {
    const audio = new Audio();
    return !!(audio.canPlayType && (
      audio.canPlayType('audio/mpeg') ||
      audio.canPlayType('audio/wav') ||
      audio.canPlayType('audio/mp4') ||
      audio.canPlayType('audio/webm')
    ));
  } catch (error) {
    console.warn('Audio support test failed:', error);
    return false;
  }
}

export function formatAudioDuration(duration: number): string {
  return `${duration.toFixed(2)}s`;
} 