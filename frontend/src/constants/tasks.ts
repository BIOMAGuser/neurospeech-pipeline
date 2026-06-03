import { TaskType } from "@/types/audio";

export interface TaskConfig {
  id: TaskType;
  label: string;
  icon: string;
  description: string;
  maxPoints: number;
  requiresApiKey: boolean;
  timerSeconds: number | null; // null = no timer
  pointsKey: string;           // which metrics key holds points
  performanceThresholds?: { excellent: number; good: number; fair: number };
}

export const TASKS: TaskConfig[] = [
  {
    id: "veggie",
    label: "Gemüseaufgabe",
    icon: "🥕",
    description:
      "Nennen Sie so viele Gemüsesorten wie möglich in einer Minute (60s, klinischer Standard für semantische Wortflüssigkeit). Nutzen Sie gerne die volle Zeit - oft fallen einem später noch mehr Begriffe ein.",
    maxPoints: 20,
    requiresApiKey: true,
    timerSeconds: 60,
    pointsKey: "points",
    performanceThresholds: { excellent: 15, good: 10, fair: 6 },
  },
  {
    id: "saying",
    label: "Sprichwortaufgabe",
    icon: "💬",
    description:
      'Erklären Sie das Sprichwort: "Der Apfel fällt nicht weit vom Stamm.',
    maxPoints: 1,
    requiresApiKey: true,
    timerSeconds: null,
    pointsKey: "points",
  },
  {
    id: "picture",
    label: "Bildbeschreibung",
    icon: "🖼️",
    description:
      "Bitte beschreiben Sie, was Sie auf folgendem Bild erkennen können:",
    maxPoints: 14,
    requiresApiKey: false,
    timerSeconds: null,
    pointsKey: "pic_points",
  },
];

// Derived lookups — existing imports (TASK_LABELS etc.) keep working
export const TASK_MAP = Object.fromEntries(
  TASKS.map((t) => [t.id, t])
) as Record<TaskType, TaskConfig>;

export const TASK_LABELS = Object.fromEntries(
  TASKS.map((t) => [t.id, t.label])
) as Record<TaskType, string>;

export const TASK_ICONS = Object.fromEntries(
  TASKS.map((t) => [t.id, t.icon])
) as Record<TaskType, string>;

export const TASK_DESCRIPTIONS = Object.fromEntries(
  TASKS.map((t) => [t.id, t.description])
) as Record<TaskType, string>;
