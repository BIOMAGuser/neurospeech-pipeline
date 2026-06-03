'use client';

import { useState, useEffect, useMemo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Loader2, Search, UserCheck } from 'lucide-react';
import { fetchPatients, type PatientListItem } from '@/services/history';

interface PatientSearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectPatient: (patient: PatientListItem) => void;
}

export default function PatientSearchDialog({
  open,
  onOpenChange,
  onSelectPatient,
}: PatientSearchDialogProps) {
  const [patients, setPatients] = useState<PatientListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    fetchPatients()
      .then(setPatients)
      .catch(() => setError('Patienten konnten nicht geladen werden.'))
      .finally(() => setLoading(false));
  }, [open]);

  const filtered = useMemo(() => {
    if (!search.trim()) return patients;
    const q = search.toLowerCase();
    return patients.filter(
      (p) =>
        p.patient_id.toLowerCase().includes(q) ||
        (p.gender && p.gender.toLowerCase().includes(q))
    );
  }, [patients, search]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Patient suchen</DialogTitle>
          <DialogDescription>
            Wählen Sie einen vorhandenen Patienten aus, um eine neue Messung hinzuzufügen.
          </DialogDescription>
        </DialogHeader>

        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Patienten-ID suchen..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 border-slate-300 text-sm"
            autoFocus
          />
        </div>

        <div className="max-h-64 overflow-y-auto space-y-1">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
            </div>
          )}

          {error && (
            <p className="text-sm text-red-500 text-center py-4">{error}</p>
          )}

          {!loading && !error && filtered.length === 0 && (
            <p className="text-sm text-slate-500 text-center py-4">
              Keine Patienten gefunden.
            </p>
          )}

          {!loading &&
            !error &&
            filtered.map((p) => (
              <Button
                key={p.id}
                variant="ghost"
                className="w-full justify-start h-auto py-2.5 px-3 text-left"
                onClick={() => {
                  onSelectPatient(p);
                  onOpenChange(false);
                  setSearch('');
                }}
              >
                <UserCheck className="h-4 w-4 mr-2.5 text-blue-600 shrink-0" />
                <div className="flex flex-col min-w-0">
                  <span className="text-sm font-medium text-slate-800 truncate">
                    {p.patient_id}
                  </span>
                  <span className="text-xs text-slate-500">
                    {p.gender === 'm' ? 'Männlich' : p.gender === 'f' ? 'Weiblich' : p.gender === 'd' ? 'Divers' : '—'}
                    {p.birth_date ? ` · Geb. ${p.birth_date}` : ''}
                    {` · ${p.analysis_count} Messung${p.analysis_count !== 1 ? 'en' : ''}`}
                  </span>
                </div>
              </Button>
            ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
