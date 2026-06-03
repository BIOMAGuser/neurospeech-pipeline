import { useQuery } from "@tanstack/react-query";
import {
  fetchPatients,
  fetchPatientAnalyses,
  fetchAnalysis,
} from "@/services/history";

export function usePatients() {
  return useQuery({
    queryKey: ["patients"],
    queryFn: fetchPatients,
  });
}

export function usePatientAnalyses(patientId: number | null) {
  return useQuery({
    queryKey: ["patient-analyses", patientId],
    queryFn: () => fetchPatientAnalyses(patientId!),
    enabled: patientId !== null,
  });
}

export function useAnalysis(id: number) {
  return useQuery({
    queryKey: ["analysis", id],
    queryFn: () => fetchAnalysis(id),
    enabled: !!id,
  });
}
