import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  computeAcoustic,
  deleteSamples,
  fetchAcousticTrials,
  fetchCohort,
  fetchSamplesStatus,
  fetchTrialScore,
} from "@/services/acousticlab";

export function useAcousticTrials() {
  return useQuery({
    queryKey: ["acoustic-trials"],
    queryFn: fetchAcousticTrials,
  });
}

export function useTrialScore(trialId: number | null) {
  return useQuery({
    queryKey: ["acoustic-score", trialId],
    queryFn: () => fetchTrialScore(trialId!),
    enabled: trialId !== null,
  });
}

export function useCohort() {
  return useQuery({
    queryKey: ["acoustic-cohort"],
    queryFn: fetchCohort,
  });
}

export function useComputeAcoustic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ trialId, signal }: { trialId: number; signal?: AbortSignal }) =>
      computeAcoustic(trialId, signal),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["acoustic-trials"] });
      qc.invalidateQueries({ queryKey: ["acoustic-score", vars.trialId] });
      qc.invalidateQueries({ queryKey: ["acoustic-cohort"] });
    },
  });
}

export function useSamplesStatus() {
  return useQuery({
    queryKey: ["acoustic-samples-status"],
    queryFn: fetchSamplesStatus,
  });
}

export function useDeleteSamples() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteSamples,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["acoustic-trials"] });
      qc.invalidateQueries({ queryKey: ["acoustic-cohort"] });
      qc.invalidateQueries({ queryKey: ["acoustic-samples-status"] });
    },
  });
}
