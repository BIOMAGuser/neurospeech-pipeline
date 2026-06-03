'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AuthService } from '@/services/auth';
import { apiPublicFetch } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { BrainCircuit, LogIn, KeyRound } from 'lucide-react';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [devAutologin, setDevAutologin] = useState(false);
  const [testCredentials, setTestCredentials] = useState<{ username: string; password: string } | null>(null);
  const router = useRouter();
  const { toast } = useToast();

  useEffect(() => {
    const controller = new AbortController();
    apiPublicFetch('/config/client', { signal: controller.signal })
      .then((r) => r.json())
      .then((cfg) => {
        if (controller.signal.aborted) return;
        setDevAutologin(!!cfg.dev_autologin);
        if (cfg.test_username && cfg.test_password) {
          setTestCredentials({ username: cfg.test_username, password: cfg.test_password });
        }
      })
      .catch(() => {});
    return () => controller.abort();
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await AuthService.login(username, password);
      toast({
        title: 'Login erfolgreich',
        description: 'Sie wurden erfolgreich angemeldet.',
      });
      router.push('/');
    } catch (error) {
      console.error('Login error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unbekannter Fehler';
      toast({
        title: 'Login fehlgeschlagen',
        description: errorMessage,
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestLogin = () => {
    if (!testCredentials) return;
    setUsername(testCredentials.username);
    setPassword(testCredentials.password);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-6">
        {/* Branding */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-2">
            <BrainCircuit className="h-8 w-8 text-blue-600" />
            <h1 className="text-3xl font-bold text-slate-800">Neurolingo</h1>
          </div>
          <p className="text-sm text-slate-500">
            Sprachanalyse-Plattform für klinische Diagnostik
          </p>
        </div>

        {/* Login Card */}
        <Card className="shadow-md">
          <CardHeader className="pb-4">
            <p className="text-center text-sm text-slate-600">
              Melden Sie sich an, um auf Patientendaten, Sprachaufnahmen und Analysen zuzugreifen.
            </p>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="username">Benutzername</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="Benutzername eingeben"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">Passwort</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Passwort eingeben"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-3 pt-2">
                <Button
                  type="submit"
                  size="lg"
                  className="w-full bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white shadow-md hover:shadow-lg transition-all"
                  disabled={isLoading}
                >
                  <LogIn className="h-4 w-4 mr-2" />
                  {isLoading ? 'Anmelden...' : 'Anmelden'}
                </Button>
                {devAutologin && (
                  <Button
                    type="button"
                    variant="outline"
                    className="w-full"
                    onClick={handleTestLogin}
                    disabled={isLoading}
                  >
                    <KeyRound className="h-4 w-4 mr-2" />
                    Test-Anmeldedaten ausfüllen
                  </Button>
                )}
              </div>
            </form>
          </CardContent>
        </Card>

      </div>
    </div>
  );
}
