import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

export async function GET() {
  try {
    const dataDir = path.join(process.cwd(), '..', 'data');
    
    const result = {
      intent_accuracy: {
        accuracy: 37.0,
        total: 200,
        correct: 74,
        bad_cases: [] as Array<{
          input: string;
          expected: string;
          actual: string;
          confidence: number;
        }>
      },
      baseline_comparison: {
        baseline_accuracy: 45.0,
        agent_accuracy: 37.0,
        improvement: -8.0,
        baseline_type: "纯LLM Zero-shot"
      },
      tool_fallback: {
        success_rate: 100.0,
        details: [] as Array<{
          name: string;
          expected: string;
          actual: string;
          correct: boolean;
        }>
      },
      memory_window: {
        memory_results: [
          { window_size: 3, message_count: 4, has_summary: true, remembers_drink: true, remembers_sugar: true, time_ms: 0.2 },
          { window_size: 5, message_count: 6, has_summary: true, remembers_drink: true, remembers_sugar: true, time_ms: 0.0 },
          { window_size: 10, message_count: 6, has_summary: false, remembers_drink: true, remembers_sugar: true, time_ms: 0.0 }
        ]
      },
      stratified_results: {
        easy_accuracy: 50.0,
        medium_accuracy: 33.3,
        hard_accuracy: 10.0,
        overall_accuracy: 37.0,
        adversarial_pass_rate: 10.0,
        adversarial_by_type: {
          sarcasm: { correct: 0, total: 8 },
          reference: { correct: 0, total: 12 },
          history_comparison: { correct: 4, total: 4 },
          vague: { correct: 0, total: 4 },
          implied: { correct: 0, total: 4 },
          neutral: { correct: 0, total: 4 },
          implied_complaint: { correct: 0, total: 4 }
        }
      },
      timestamp: new Date().toISOString()
    };

    const stratifiedPath = path.join(dataDir, 'stratified_eval_report.json');
    if (fs.existsSync(stratifiedPath)) {
      const stratifiedData = JSON.parse(fs.readFileSync(stratifiedPath, 'utf-8'));
      if (stratifiedData.stats) {
        result.intent_accuracy.accuracy = stratifiedData.stats.overall.accuracy;
        result.intent_accuracy.total = stratifiedData.stats.overall.total;
        result.intent_accuracy.correct = stratifiedData.stats.overall.correct;
        
        if (stratifiedData.stats.by_difficulty) {
          result.stratified_results.easy_accuracy = stratifiedData.stats.by_difficulty.easy?.accuracy || 0;
          result.stratified_results.medium_accuracy = stratifiedData.stats.by_difficulty.medium?.accuracy || 0;
          result.stratified_results.hard_accuracy = stratifiedData.stats.by_difficulty.hard?.accuracy || 0;
          result.stratified_results.overall_accuracy = stratifiedData.stats.overall.accuracy;
        }
        
        if (stratifiedData.stats.adversarial) {
          result.stratified_results.adversarial_pass_rate = stratifiedData.stats.adversarial.accuracy;
        }
        
        if (stratifiedData.stats.adversarial_by_type) {
          result.stratified_results.adversarial_by_type = {
            sarcasm: stratifiedData.stats.adversarial_by_type.sarcasm || { correct: 0, total: 0 },
            reference: stratifiedData.stats.adversarial_by_type.reference || { correct: 0, total: 0 },
            history_comparison: stratifiedData.stats.adversarial_by_type.history_comparison || { correct: 0, total: 0 },
            vague: stratifiedData.stats.adversarial_by_type.vague || { correct: 0, total: 0 },
            implied: stratifiedData.stats.adversarial_by_type.implied || { correct: 0, total: 0 },
            neutral: stratifiedData.stats.adversarial_by_type.neutral || { correct: 0, total: 0 },
            implied_complaint: stratifiedData.stats.adversarial_by_type.implied_complaint || { correct: 0, total: 0 }
          };
        }
        
        if (stratifiedData.bad_cases && Array.isArray(stratifiedData.bad_cases)) {
          result.intent_accuracy.bad_cases = stratifiedData.bad_cases.slice(0, 5).map((bc: any) => ({
            input: bc.query,
            expected: bc.expected_intent,
            actual: bc.predicted_intent,
            confidence: bc.confidence
          }));
        }
        
        if (stratifiedData.timestamp) {
          result.timestamp = stratifiedData.timestamp;
        }
      }
    }

    const enhancedPath = path.join(dataDir, 'enhanced_experiment_results.json');
    if (fs.existsSync(enhancedPath)) {
      const enhancedData = JSON.parse(fs.readFileSync(enhancedPath, 'utf-8'));
      if (enhancedData.tool_fallback && enhancedData.tool_fallback.details) {
        result.tool_fallback = enhancedData.tool_fallback;
      }
      if (enhancedData.memory_window && enhancedData.memory_window.memory_results) {
        result.memory_window = enhancedData.memory_window;
      }
    }

    return NextResponse.json(result);
  } catch (error) {
    console.error('Failed to load experiment results:', error);
    return NextResponse.json({ error: 'Failed to load experiment results' }, { status: 500 });
  }
}
