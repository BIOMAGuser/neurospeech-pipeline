"use client";

import { Button } from "@/components/ui/button";

export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="max-w-md w-full text-center space-y-4">
        <h1 className="text-xl font-bold text-red-600">
          Ein Fehler ist aufgetreten
        </h1>
        <p className="text-sm text-slate-600">
          Beim Laden der Anwendung ist ein unerwarteter Fehler aufgetreten.
        </p>
        {error.message && (
          <p className="text-xs text-slate-400 font-mono bg-slate-100 p-2 rounded">
            {error.message}
          </p>
        )}
        <Button onClick={reset}>Erneut versuchen</Button>
      </div>
    </div>
  );
}
