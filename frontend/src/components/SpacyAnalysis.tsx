"use client";

import React, { useState } from 'react';
import { Button } from './ui/button';
import { Textarea } from './ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Label } from './ui/label';
import { Alert, AlertDescription, AlertTitle } from './ui/alert';
import { BrainCircuit, Loader2, BarChartBig, Download } from 'lucide-react'; // Import Download icon

// --- Updated Interface (based on Python output) ---
interface AnalysisResult {
  // Block 1 – ratios
  ttr?: number;
  verb_ratio?: number;
  noun_ratio?: number;
  pronoun_ratio?: number;
  adverb_ratio?: number;
  adjective_ratio?: number;

  // Block 2 – counts
  verb_count?: number;
  noun_count?: number;
  pronoun_count?: number;
  adverb_count?: number;
  adjective_count?: number;
  filler_word_count?: number;
  total_word_count?: number;
  avg_sentence_length?: number;

  // Error field
  error?: string;
}

// --- Helper Functions ---

// Function to format keys for display
const formatKey = (key: string): string => {
  // Specific overrides for better readability
  if (key === 'ttr') return 'Type-Token Ratio (TTR)';
  if (key === 'avg_sentence_length') return 'Avg. Sentence Length';
  if (key === 'total_word_count') return 'Total Word Count';
  if (key === 'filler_word_count') return 'Filler Word Count';

  return key
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

 // Function to format values, especially numbers
const formatValue = (key: string, value: any): string => {
  if (typeof value === 'number') {
    // Format ratios and other decimals to 3 decimal places
    if (key.includes('_ratio') || key === 'ttr' || key === 'avg_sentence_length') {
        return value.toFixed(3);
    }
    // Format counts as integers
    if (key.includes('_count')) {
        return value.toFixed(0); // Display counts as whole numbers
    }
    // Fallback for other numbers
    return value.toString();
  }
  return value?.toString() ?? 'N/A'; // Handle null/undefined
};

// --- Analysis Display Component ---
interface SpacyAnalysisDisplayProps {
    analysis: AnalysisResult;
}

const SpacyAnalysisDisplay: React.FC<SpacyAnalysisDisplayProps> = ({ analysis }) => {
    // Filter out keys that are not part of the intended display sections or have undefined/null values
    const validEntries = Object.entries(analysis).filter(
        ([key, value]) => value !== undefined && value !== null && key !== 'error' // Exclude non-display/helper keys
    );

    const ratioKeys = ["ttr", "verb_ratio", "noun_ratio", "pronoun_ratio", "adverb_ratio", "adjective_ratio"];
    const countKeys = ["verb_count", "noun_count", "pronoun_count", "adverb_count", "adjective_count", "filler_word_count", "total_word_count", "avg_sentence_length"];

    return (
        <Card className="shadow-md">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                <BarChartBig className="text-primary" />
                Analysis Results
                </CardTitle>
            </CardHeader>

            {/* Block 1 – Ratios */}
            <CardContent className="space-y-2">
                {validEntries
                .filter(([key]) => ratioKeys.includes(key))
                .map(([key, value]) => (
                    <div key={key} className="flex justify-between rounded-md bg-secondary/30 p-3 text-sm">
                    <span className="font-medium text-foreground">{formatKey(key)}:</span>
                    <span className="font-mono text-primary">{formatValue(key, value)}</span>
                    </div>
                ))}
            </CardContent>

            {/* Divider */}
            <hr className="my-4 mx-6" /> {/* Added margin */}

            {/* Block 2 – Counts */}
            <CardContent className="space-y-2">
                {validEntries
                .filter(([key]) => countKeys.includes(key))
                 // Sort counts for consistent order if desired (optional)
                 .sort(([keyA], [keyB]) => countKeys.indexOf(keyA) - countKeys.indexOf(keyB))
                .map(([key, value]) => (
                    <div key={key} className="flex justify-between rounded-md bg-secondary/30 p-3 text-sm">
                    <span className="font-medium text-foreground">{formatKey(key)}:</span>
                    <span className="font-mono text-primary">{formatValue(key, value)}</span>
                    </div>
                ))}
            </CardContent>
        </Card>
    );
};


// --- Main Component ---
export function SpacyAnalysis() {
  const [inputText, setInputText] = useState<string>('');
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // --- Download Function ---
  const handleDownloadJson = () => {
    if (!analysis || analysis.error) {
      console.error("Cannot download: No valid analysis data available.");
      // Optionally show a user notification here
      return;
    }

    const dataToSave = {
      transcript: inputText,
      analysis: analysis,
    };

    const jsonString = JSON.stringify(dataToSave, null, 2); // Pretty print JSON
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    // Generate a filename (e.g., based on current date/time)
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    link.download = `spacy_analysis_${timestamp}.json`;
    document.body.appendChild(link); // Required for Firefox
    link.click();

    // Clean up
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleAnalyze = async () => {
    setIsLoading(true);
    setError(null);
    setAnalysis(null);

    // Define the Cloud Run URL directly (ensure this is correct and accessible)
    // const apiUrl = 'https://sprach-analyse-service-794357738916.europe-west1.run.app';
    const apiUrl = 'http://localhost:8080'; // For local testing
    const targetUrl = `${apiUrl}/analyze`;


    try {
      const response = await fetch(targetUrl, { // Use targetUrl here
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: inputText }),
      });

      const resultData = await response.json();

      if (!response.ok) {
        console.error(`Error response body from ${targetUrl}:`, resultData);
        throw new Error(resultData?.error || `HTTP error! Status: ${response.status} ${response.statusText}`);
      }

      if (resultData.error) {
           throw new Error(resultData.error);
      }

       // Explicitly cast/map to ensure correct types, handle potential missing fields gracefully
       const typedAnalysis: AnalysisResult = {
           ttr: resultData.ttr !== undefined ? Number(resultData.ttr) : undefined,
           verb_ratio: resultData.verb_ratio !== undefined ? Number(resultData.verb_ratio) : undefined,
           noun_ratio: resultData.noun_ratio !== undefined ? Number(resultData.noun_ratio) : undefined,
           pronoun_ratio: resultData.pronoun_ratio !== undefined ? Number(resultData.pronoun_ratio) : undefined,
           adverb_ratio: resultData.adverb_ratio !== undefined ? Number(resultData.adverb_ratio) : undefined,
           adjective_ratio: resultData.adjective_ratio !== undefined ? Number(resultData.adjective_ratio) : undefined, // Fix: was resultA
           verb_count: resultData.verb_count !== undefined ? Number(resultData.verb_count) : undefined,
           noun_count: resultData.noun_count !== undefined ? Number(resultData.noun_count) : undefined,
           pronoun_count: resultData.pronoun_count !== undefined ? Number(resultData.pronoun_count) : undefined,
           adverb_count: resultData.adverb_count !== undefined ? Number(resultData.adverb_count) : undefined,
           adjective_count: resultData.adjective_count !== undefined ? Number(resultData.adjective_count) : undefined,
           filler_word_count: resultData.filler_word_count !== undefined ? Number(resultData.filler_word_count) : undefined,
           total_word_count: resultData.total_word_count !== undefined ? Number(resultData.total_word_count) : undefined, // Match Python key
           avg_sentence_length: resultData.avg_sentence_length !== undefined ? Number(resultData.avg_sentence_length) : undefined,
       };

      setAnalysis(typedAnalysis);

    } catch (err: any) {
      console.error(`Analysis failed when fetching from ${targetUrl}:`, err);

      let userErrorMessage = 'An unexpected error occurred during analysis.';
      if (err instanceof TypeError && (err.message.includes('Failed to fetch') || err.message.includes('NetworkError'))) {
          userErrorMessage = `Could not connect to the analysis service at ${apiUrl}. This might be due to a network issue, the backend service being down, or a CORS configuration problem. Please check the browser console (F12 -> Console) for more details. Ensure the backend service is running and accessible.`;
      } else if (err instanceof Error) {
          userErrorMessage = err.message;
      }

      setError(userErrorMessage);
      setAnalysis(null); // Clear previous analysis on error
    } finally {
      setIsLoading(false);
    }
  };


  return (
    <div className="w-full max-w-3xl space-y-6"> {/* Ensure this matches AudioProcessor for width */}
      {/* Input Card */}
      <Card className="shadow-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BrainCircuit className="text-primary" />
            SPACY
          </CardTitle>
          <CardDescription>Enter German text directly for linguistic analysis using spaCy.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid w-full items-center gap-1.5">
            <Label htmlFor="text-input">Text Input</Label>
            <Textarea
              id="text-input"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Enter German text here..."
              disabled={isLoading}
              className="min-h-[150px] resize-none"
            />
          </div>
          <Button onClick={handleAnalyze} disabled={isLoading || !inputText} className="w-full">
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Analyzing...
              </>
            ) : (
              'Analyze Text'
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && !isLoading && ( // Only show error if not loading
        <Alert variant="destructive">
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

       {/* Display backend error if present in the analysis object (even if other fields are missing) */}
       {analysis?.error && !isLoading && ( // Added !isLoading check
         <Alert variant="destructive">
           <AlertTitle>Backend Error</AlertTitle>
           <AlertDescription>{analysis.error}</AlertDescription>
         </Alert>
       )}

      {/* Results Section - Use the SpacyAnalysisDisplay component */}
       {!isLoading && analysis && !analysis.error && Object.keys(analysis).filter(k => k !== 'error' && analysis[k as keyof AnalysisResult] !== undefined).length > 0 && (
           <>
               <SpacyAnalysisDisplay analysis={analysis} />
               {/* Add Download Button below the results */}
               <Button
                   onClick={handleDownloadJson}
                   disabled={!analysis || !!analysis.error} // Disable if no analysis or if there's an error in analysis
                   variant="outline"
                   className="w-full mt-4" // Add margin top
               >
                   <Download className="mr-2 h-4 w-4" />
                   Download Results (.json)
               </Button>
           </>
       )}

    </div>
  );
}

// export default SpacyAnalysis; // Assuming this is the intended export based on file name
