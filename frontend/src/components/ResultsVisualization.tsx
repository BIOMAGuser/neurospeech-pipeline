// src/components/ResultsVisualization.tsx
'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import {
  TrendingUp,
  Clock,
  MessageSquare,
  Target,
  Award,
  BarChart3,
  CheckCircle,
  AlertCircle,
  Timer,
  Zap,
  X
} from 'lucide-react';
import { TestResult, ResultsVisualizationProps, TaskType } from '@/types/audio';
import { TASK_ICONS } from '@/constants/tasks';

const performanceColors = {
  excellent: 'bg-green-500',
  good: 'bg-blue-500',
  fair: 'bg-yellow-500',
  needs_improvement: 'bg-red-500'
};

const performanceLabels = {
  excellent: 'Sehr gut',
  good: 'Gut gemacht', 
  fair: 'Schöner Versuch',
  needs_improvement: ''
};

const getPerformanceFromScore = (points: number, maxPoints: number): TestResult['performance'] => {
  const percentage = (points / maxPoints) * 100;
  if (percentage >= 90) return 'excellent';
  if (percentage >= 75) return 'good';
  if (percentage >= 60) return 'fair';
  return 'needs_improvement';
};

const formatDuration = (seconds: number): string => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return mins > 0 ? `${mins}:${secs.toString().padStart(2, '0')} min` : `${secs} sec`;
};

// Special binary result card for proverb task
const ProverbResultCard: React.FC<{ result: TestResult }> = ({ result }) => {
  const isCorrect = result.points > 0; // Binary: correct if any points scored
  const expectedProverb = "Der Apfel fällt nicht weit vom Stamm";
  
  return (
    <Card className="transition-all duration-200 hover:shadow-lg h-full">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <span className="text-2xl">💬</span>
          <span>Sprichwort Vervollständigen</span>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Result Display */}
        <div className={`text-center p-6 rounded-lg ${isCorrect ? 'bg-green-50' : 'bg-red-50'}`}>
          {isCorrect ? (
            <>
              <CheckCircle className="h-12 w-12 mx-auto mb-3 text-green-600" />
              <div className="text-lg font-semibold text-green-800 mb-2">
                Antwort korrekt!
              </div>
              <div className="text-sm text-green-700">
                "{expectedProverb}"
              </div>
            </>
          ) : (
            <>
              <X className="h-12 w-12 mx-auto mb-3 text-red-600" />
              <div className="text-lg font-semibold text-red-800 mb-2">
                Nicht korrekt
              </div>
              <div className="text-sm text-red-700 mb-2">
                <strong>Erwartet:</strong> "{expectedProverb}"
              </div>
              <div className="text-xs text-red-600">
                Versuchen Sie, das Sprichwort vollständig zu ergänzen
              </div>
            </>
          )}
        </div>

        <Separator />

        {/* Duration Display */}
        <div className="flex items-center justify-center gap-2">
          <Clock className="h-4 w-4 text-blue-600" />
          <span className="text-sm font-medium">
            Antwortzeit: {formatDuration(result.duration)}
          </span>
        </div>

        {/* Transcription if available */}
        {result.transcription && (
          <div className="space-y-2">
            <p className="text-sm font-medium text-gray-700">Ihre Antwort:</p>
            <div className="text-sm p-3 bg-gray-50 rounded-md italic">
              "{result.transcription}"
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

const ResultCard: React.FC<{ result: TestResult }> = ({ result }) => {
  const scorePercentage = (result.points / result.maxPoints) * 100;
  
  return (
    <Card className="transition-all duration-200 hover:shadow-lg h-full">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <CardTitle className="flex items-center gap-2 text-lg flex-1 mr-2">
            <span className="text-2xl">{TASK_ICONS[result.taskType]}</span>
            <span className="leading-tight">{result.taskName}</span>
          </CardTitle>
          {result.performance !== 'needs_improvement' && (
            <Badge 
              variant="secondary" 
              className={`${performanceColors[result.performance]} text-white shrink-0`}
            >
              {performanceLabels[result.performance]}
            </Badge>
          )}
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Score Section */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium flex items-center gap-1">
              <Target className="h-4 w-4" />
              Punkte
            </span>
            <span className="font-bold text-lg">
              {result.points}/{result.maxPoints}
            </span>
          </div>
          <Progress value={scorePercentage} className="h-2" />
          <p className="text-xs text-gray-600 text-center">
            {scorePercentage.toFixed(0)}% erreicht
          </p>
        </div>

        <Separator />

        {/* Key Metrics */}
        <div className="grid grid-cols-2 gap-3">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <Clock className="h-5 w-5 mx-auto mb-1 text-blue-600" />
            <div className="text-sm font-semibold">{formatDuration(result.duration)}</div>
            <div className="text-xs text-gray-600">Dauer</div>
          </div>
          
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <MessageSquare className="h-5 w-5 mx-auto mb-1 text-green-600" />
            <div className="text-sm font-semibold">{result.wordCount}</div>
            <div className="text-xs text-gray-600">Wörter</div>
          </div>
        </div>

        {/* Task-specific metrics */}
        {result.taskType === 'veggie' && Array.isArray(result.metrics.correct_words) && result.metrics.correct_words.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Korrekte Begriffe:</p>
            <div className="flex flex-wrap gap-1">
              {(result.metrics.correct_words as string[]).slice(0, 6).map((word, idx) => (
                <Badge key={idx} variant="outline" className="text-xs">
                  {word}
                </Badge>
              ))}
              {(result.metrics.correct_words as string[]).length > 6 && (
                <Badge variant="outline" className="text-xs">
                  +{(result.metrics.correct_words as string[]).length - 6} weitere
                </Badge>
              )}
            </div>
          </div>
        )}

        {result.taskType === 'picture' && (
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="text-center p-2 bg-blue-50 rounded">
                <div className="font-semibold">{result.metrics.sentence_count}</div>
                <div className="text-xs text-gray-600">Sätze</div>
              </div>
              <div className="text-center p-2 bg-green-50 rounded">
                <div className="font-semibold">{(result.metrics.ttr as number)?.toFixed(2)}</div>
                <div className="text-xs text-gray-600">TTR</div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export const ResultsVisualization: React.FC<ResultsVisualizationProps> = ({
  results,
  patientName,
  testDate,
  recommendations = []
}) => {
  return (
    <div className="space-y-6 p-4 max-w-6xl mx-auto">
      {/* Header */}
      <Card className="bg-gradient-to-r from-teal-50 to-blue-50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl flex items-center gap-2">
                <Award className="h-6 w-6 text-teal-600" />
                Testergebnisse - Einzelauswertung
              </CardTitle>
              {patientName && (
                <p className="text-gray-600 mt-1">für {patientName}</p>
              )}
              {testDate && (
                <p className="text-sm text-gray-500">vom {testDate}</p>
              )}
            </div>
            
            <div className="text-center">
              <div className="text-lg font-medium text-teal-600">
                {results.length} Test{results.length !== 1 ? 's' : ''}
              </div>
              <div className="text-sm text-gray-600">
                abgeschlossen
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Individual Test Results - Each task gets its own display */}
      <div className="space-y-6">
        {results.map((result) => (
          <div key={result.taskType}>
            {result.taskType === 'saying' ? (
              <ProverbResultCard result={result} />
            ) : (
              <ResultCard result={result} />
            )}
          </div>
        ))}
      </div>

      {/* Task-specific Recommendations */}
      {recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Individuelle Empfehlungen
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {recommendations.map((rec) => (
                <li key={rec} className="flex items-start gap-2">
                  <AlertCircle className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                  <span className="text-sm">{rec}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Individual Task Summary */}
      <div className="grid gap-4 md:grid-cols-3">
        {results.map((result) => (
          <Card key={result.taskType} className="text-center">
            <CardContent className="pt-4">
              <div className="text-2xl mb-2">{TASK_ICONS[result.taskType]}</div>
              <div className="text-lg font-bold mb-1">
                {result.taskType === 'saying' 
                  ? (result.points > 0 ? '✓ Korrekt' : '✗ Nicht korrekt')
                  : `${result.points}/${result.maxPoints} Punkte`
                }
              </div>
              <div className="text-sm text-gray-600 mb-2">{result.taskName}</div>
              <div className="text-xs text-gray-500">
                Dauer: {formatDuration(result.duration)}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default ResultsVisualization;
