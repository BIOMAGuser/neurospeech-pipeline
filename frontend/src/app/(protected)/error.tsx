"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function ProtectedError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex justify-center py-12">
      <Card className="max-w-lg w-full">
        <CardHeader>
          <CardTitle className="text-red-600">Ein Fehler ist aufgetreten</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-slate-600">
            Beim Laden der Seite ist ein unerwarteter Fehler aufgetreten. Bitte
            versuchen Sie es erneut.
          </p>
          {error.message && (
            <p className="text-xs text-slate-400 font-mono bg-slate-50 p-2 rounded">
              {error.message}
            </p>
          )}
          <Button onClick={reset}>Erneut versuchen</Button>
        </CardContent>
      </Card>
    </div>
  );
}
