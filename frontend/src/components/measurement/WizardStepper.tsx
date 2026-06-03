"use client";

import { Check } from "lucide-react";

const steps = [
  { number: 1, label: "Patientendaten" },
  { number: 2, label: "Aufnahmen" },
  { number: 3, label: "Auswertung" },
];

interface WizardStepperProps {
  currentStep: number;
}

export default function WizardStepper({ currentStep }: WizardStepperProps) {
  return (
    <div className="flex items-center justify-center gap-2 mb-6">
      {steps.map((step, idx) => {
        const isActive = step.number === currentStep;
        const isDone = step.number < currentStep;

        return (
          <div key={step.number} className="flex items-center">
            {idx > 0 && (
              <div
                className={`w-16 h-0.5 mx-1 ${
                  isDone ? "bg-blue-600" : "bg-slate-200"
                }`}
              />
            )}
            <div className="flex items-center gap-2">
              <div
                className={`flex items-center justify-center w-10 h-10 rounded-full text-sm font-semibold transition-colors ${
                  isActive
                    ? "bg-blue-600 text-white"
                    : isDone
                    ? "bg-blue-600 text-white"
                    : "bg-slate-200 text-slate-500"
                }`}
              >
                {isDone ? <Check className="h-4 w-4" /> : step.number}
              </div>
              <span
                className={`text-sm font-medium ${
                  isActive ? "text-blue-700" : isDone ? "text-blue-600" : "text-slate-400"
                }`}
              >
                {step.label}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
