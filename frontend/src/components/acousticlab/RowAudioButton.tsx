"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Play, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface Props {
  trialId: number;
}

/**
 * Inline play/stop button. On first click fetches the MP3 with auth,
 * creates an object URL, and plays it via a hidden <audio>. Click again
 * to stop. URL is revoked on unmount.
 */
export default function RowAudioButton({ trialId }: Props) {
  const [loading, setLoading] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = "";
      }
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    };
  }, []);

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (playing) {
      audioRef.current?.pause();
      audioRef.current && (audioRef.current.currentTime = 0);
      setPlaying(false);
      return;
    }
    if (loading) return;

    if (!urlRef.current) {
      setLoading(true);
      setError(false);
      try {
        const res = await apiFetch(`/trials/${trialId}/audio`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const blob = await res.blob();
        urlRef.current = URL.createObjectURL(blob);
      } catch {
        setError(true);
        setLoading(false);
        return;
      }
      setLoading(false);
    }

    if (!audioRef.current) {
      audioRef.current = new Audio(urlRef.current);
      audioRef.current.addEventListener("ended", () => setPlaying(false));
      audioRef.current.addEventListener("error", () => {
        setError(true);
        setPlaying(false);
      });
    }
    try {
      await audioRef.current.play();
      setPlaying(true);
    } catch {
      setError(true);
    }
  };

  const Icon = loading ? Loader2 : playing ? Square : Play;
  return (
    <Button
      size="sm"
      variant={playing ? "default" : "outline"}
      onClick={handleClick}
      disabled={error}
      title={error ? "Audio nicht verfügbar" : undefined}
      className="gap-1.5"
    >
      <Icon className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
      {playing ? "Stop" : error ? "—" : "Play"}
    </Button>
  );
}
