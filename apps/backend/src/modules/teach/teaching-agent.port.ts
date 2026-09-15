import type { RunResult } from '@openai/codex-sdk';

export const TEACHING_AGENT = Symbol('TEACHING_AGENT');

export interface TeachingAgent {
  run(prompt: string): Promise<RunResult>;
}
