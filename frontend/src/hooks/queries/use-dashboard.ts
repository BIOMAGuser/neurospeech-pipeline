import { useQuery } from "@tanstack/react-query";
import {
  fetchHealth,
  fetchStats,
  fetchOpenAIStatus,
} from "@/services/dashboard";

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
  });
}

export function useStats() {
  return useQuery({
    queryKey: ["stats"],
    queryFn: fetchStats,
  });
}

export function useOpenAIStatus() {
  return useQuery({
    queryKey: ["openai-status"],
    queryFn: fetchOpenAIStatus,
  });
}
