export interface FormFieldOption {
  value: string;
  label: string;
}

export interface FormFieldConfig {
  key: string;
  type: 'text' | 'number' | 'date' | 'select' | 'textarea';
  label: string;
  required?: boolean;
  placeholder?: string;
  options?: FormFieldOption[];
  min?: number;
  max?: number;
  full_width?: boolean;
}

export interface PatientFormConfig {
  fields: FormFieldConfig[];
}
