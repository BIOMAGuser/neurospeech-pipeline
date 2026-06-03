'use client';

import { useState, useEffect, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Search, Info } from 'lucide-react';
import { usePatient, type PatientData } from '@/hooks/use-patient';
import { fetchPatients, type PatientListItem } from '@/services/history';
import PatientSearchDialog from '@/components/PatientSearchDialog';
import { usePatientFormConfig } from '@/hooks/queries/use-form-config';
import type { FormFieldConfig } from '@/types/form-config';

export default function PatientInfoForm() {
  const { patient, updateField } = usePatient();
  const { data: formFields = [] } = usePatientFormConfig();
  const [searchOpen, setSearchOpen] = useState(false);
  const [existingPatient, setExistingPatient] = useState<PatientListItem | null>(null);
  const [knownPatientIds, setKnownPatientIds] = useState<PatientListItem[]>([]);

  // Load known patient IDs once on mount for inline checking
  useEffect(() => {
    fetchPatients()
      .then(setKnownPatientIds)
      .catch(() => {});
  }, []);

  // Check if typed patient ID matches an existing patient
  const checkExistingPatient = useCallback(
    (id: string) => {
      if (!id.trim()) {
        setExistingPatient(null);
        return;
      }
      const match = knownPatientIds.find(
        (p) => p.patient_id.toLowerCase() === id.toLowerCase()
      );
      setExistingPatient(match ?? null);
    },
    [knownPatientIds]
  );

  const handlePatientIdChange = (value: string) => {
    updateField('patientId', value);
    checkExistingPatient(value);
  };

  const handleSelectPatient = (p: PatientListItem) => {
    updateField('patientId', p.patient_id);
    if (p.gender) updateField('gender', p.gender);
    if (p.birth_date) updateField('birthDate', p.birth_date);
    setExistingPatient(p);
  };

  const gridFields = formFields.filter(f => !f.full_width);
  const fullWidthFields = formFields.filter(f => f.full_width);

  function renderField(field: FormFieldConfig) {
    const key = field.key as keyof PatientData;
    const value = patient[key] as string;

    switch (field.type) {
      case 'select':
        return (
          <div key={field.key}>
            <Label htmlFor={field.key} className="text-sm font-medium text-slate-700">
              {field.label}{field.required && '*'}
            </Label>
            <Select value={value} onValueChange={(v) => updateField(key, v)}>
              <SelectTrigger className="border-slate-300 focus:border-blue-500 focus:ring-blue-500 text-sm">
                <SelectValue placeholder={field.placeholder ?? 'Auswählen...'} />
              </SelectTrigger>
              <SelectContent>
                {field.options?.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        );

      case 'number':
        return (
          <div key={field.key}>
            <Label htmlFor={field.key} className="text-sm font-medium text-slate-700">
              {field.label}{field.required && '*'}
            </Label>
            <Input
              id={field.key}
              type="number"
              min={field.min}
              max={field.max}
              value={value}
              onChange={(e) => {
                const val = e.target.value;
                if (val === '' || (
                  (field.min === undefined || Number(val) >= field.min) &&
                  (field.max === undefined || Number(val) <= field.max)
                )) {
                  updateField(key, val);
                }
              }}
              placeholder={field.placeholder}
              className="border-slate-300 focus:border-blue-500 focus:ring-blue-500 text-sm"
            />
            {field.min !== undefined && field.max !== undefined && value &&
              (Number(value) < field.min || Number(value) > field.max) && (
              <p className="text-xs text-red-500 mt-1">
                {field.label} muss zwischen {field.min} und {field.max} liegen
              </p>
            )}
          </div>
        );

      case 'date':
        return (
          <div key={field.key}>
            <Label htmlFor={field.key} className="text-sm font-medium text-slate-700">
              {field.label}{field.required && '*'}
            </Label>
            <Input
              id={field.key}
              type="date"
              value={value}
              onChange={(e) => updateField(key, e.target.value)}
              className="border-slate-300 focus:border-blue-500 focus:ring-blue-500 text-sm"
            />
          </div>
        );

      case 'textarea':
        return (
          <div key={field.key} className="mt-4">
            <Label htmlFor={field.key} className="text-sm font-medium text-slate-700">
              {field.label}{field.required && '*'}
            </Label>
            <Textarea
              id={field.key}
              value={value}
              onChange={(e) => updateField(key, e.target.value)}
              placeholder={field.placeholder}
              className="border-slate-300 focus:border-blue-500 focus:ring-blue-500 text-sm mt-1"
            />
          </div>
        );

      default: // text
        return (
          <div key={field.key}>
            <Label htmlFor={field.key} className="text-sm font-medium text-slate-700">
              {field.label}{field.required && '*'}
            </Label>
            <Input
              id={field.key}
              type="text"
              value={value}
              onChange={(e) => updateField(key, e.target.value)}
              placeholder={field.placeholder}
              className="border-slate-300 focus:border-blue-500 focus:ring-blue-500 text-sm"
            />
          </div>
        );
    }
  }

  return (
    <>
      <Card className="w-full shadow-lg border border-slate-200 transition-all duration-200 hover:shadow-xl hover:border-blue-200">
        <CardHeader>
          <CardTitle className="text-lg sm:text-xl text-slate-800">
            Patienteninformationen
          </CardTitle>
          <CardDescription className="text-sm text-slate-600">
            Bitte geben Sie die notwendigen Patientendaten ein. Diese Felder sind
            für die ordnungsgemäße Dokumentation erforderlich, können aber beim
            Testen weggelassen werden.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-5">
            {/* Patient ID — hardcoded (search dialog) */}
            <div>
              <Label htmlFor="patientID" className="text-sm font-medium text-slate-700">
                Patienten-ID*
              </Label>
              <div className="flex gap-3">
                <Input
                  id="patientID"
                  type="text"
                  value={patient.patientId}
                  onChange={(e) => handlePatientIdChange(e.target.value)}
                  placeholder="z.B. P000001"
                  className="border-slate-300 focus:border-blue-500 focus:ring-blue-500 text-sm"
                  required
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="shrink-0 border-slate-300 hover:border-blue-400 hover:bg-blue-50"
                  onClick={() => setSearchOpen(true)}
                  title="Vorhandenen Patienten suchen"
                >
                  <Search className="h-4 w-4 text-slate-600" />
                </Button>
              </div>
              {existingPatient && (
                <div className="flex items-start gap-1.5 mt-1.5 p-2 bg-blue-50 border border-blue-200 rounded-md">
                  <Info className="h-3.5 w-3.5 text-blue-600 mt-0.5 shrink-0" />
                  <p className="text-xs text-blue-700">
                    Patient <span className="font-semibold">{existingPatient.patient_id}</span> existiert
                    bereits ({existingPatient.analysis_count} Messung{existingPatient.analysis_count !== 1 ? 'en' : ''}).
                    Die neue Messung wird diesem Patienten hinzugefügt.
                  </p>
                </div>
              )}
            </div>

            {/* Test date — hardcoded (default date logic) */}
            <div>
              <Label htmlFor="datum" className="text-sm font-medium text-slate-700">
                Sitzungsdatum*
              </Label>
              <Input
                id="datum"
                type="date"
                value={patient.testDate}
                onChange={(e) => updateField('testDate', e.target.value)}
                className="border-slate-300 focus:border-blue-500 focus:ring-blue-500 text-sm"
                required
              />
            </div>

            {/* Dynamic grid fields from config */}
            {gridFields.map(renderField)}
          </div>

          {/* Dynamic full-width fields from config */}
          {fullWidthFields.map(renderField)}
        </CardContent>
      </Card>

      <PatientSearchDialog
        open={searchOpen}
        onOpenChange={setSearchOpen}
        onSelectPatient={handleSelectPatient}
      />
    </>
  );
}
