import { useQuery } from "@tanstack/react-query";
import { fetchPatientFormConfig } from "@/services/form-config";
import type { FormFieldConfig } from "@/types/form-config";

const DEFAULT_FIELDS: FormFieldConfig[] = [
  { key: "birthDate", type: "date", label: "Geburtsdatum" },
  {
    key: "gender", type: "select", label: "Geschlecht",
    placeholder: "Auswählen...",
    options: [
      { value: "m", label: "Männlich" },
      { value: "f", label: "Weiblich" },
      { value: "d", label: "Divers" },
    ],
  },
  {
    key: "group", type: "select", label: "Gruppe",
    placeholder: "Auswählen...",
    options: [
      { value: "Kontrolle", label: "Kontrolle" },
      { value: "Parkinson", label: "Parkinson" },
      { value: "Sonstiges", label: "Sonstiges" },
    ],
  },
  { key: "mocaScore", type: "number", label: "MoCa-Wert", placeholder: "0-30", min: 0, max: 30 },
  { key: "notes", type: "textarea", label: "Bemerkungen", placeholder: "Zusätzliche Anmerkungen...", full_width: true },
];

export function usePatientFormConfig() {
  const query = useQuery({
    queryKey: ["patient-form-config"],
    queryFn: fetchPatientFormConfig,
    staleTime: Infinity,
    gcTime: 1000 * 60 * 60,
    retry: 1,
  });

  // Always return usable fields: API data > defaults on error/loading
  const fields = query.data?.fields?.length
    ? query.data.fields
    : DEFAULT_FIELDS;

  return { ...query, data: fields };
}
