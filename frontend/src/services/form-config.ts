import { apiPublicFetch } from "@/lib/api";
import type { PatientFormConfig } from "@/types/form-config";

export async function fetchPatientFormConfig(): Promise<PatientFormConfig> {
  const res = await apiPublicFetch("/config/patient-form");
  if (!res.ok) throw new Error("Failed to fetch form config");
  return res.json();
}
