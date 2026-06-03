'use client';

import { createContext, useContext, useState, useCallback, useEffect } from 'react';

export interface PatientData {
  patientId: string;
  testDate: string;
  birthDate: string;
  gender: string;
  mocaScore: string;
  group: string;
  notes: string;
  saveToDatabase: boolean;
}

const defaultPatientData: PatientData = {
  patientId: '',
  testDate: '',
  birthDate: '',
  gender: '',
  mocaScore: '',
  group: '',
  notes: '',
  saveToDatabase: true,
};

export interface PatientContextValue {
  patient: PatientData;
  updateField: <K extends keyof PatientData>(field: K, value: PatientData[K]) => void;
  reset: () => void;
}

export const PatientContext = createContext<PatientContextValue | null>(null);

export function usePatientState(): PatientContextValue {
  const [patient, setPatient] = useState<PatientData>(defaultPatientData);

  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    setPatient((prev) => ({ ...prev, testDate: today }));
  }, []);

  const updateField = useCallback(<K extends keyof PatientData>(field: K, value: PatientData[K]) => {
    setPatient((prev) => ({ ...prev, [field]: value }));
  }, []);

  const reset = useCallback(() => {
    setPatient(defaultPatientData);
  }, []);

  return { patient, updateField, reset };
}

export function usePatient(): PatientContextValue {
  const ctx = useContext(PatientContext);
  if (!ctx) throw new Error('usePatient must be used inside PatientContext.Provider');
  return ctx;
}
