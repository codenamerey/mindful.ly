import { Inject, Injectable } from '@nestjs/common';
import type { RunResult } from '@openai/codex-sdk';
import {
  TEACHING_AGENT,
  type TeachingAgent,
} from './teaching-agent.port.js';

@Injectable()
export class TeachService {
  constructor(
    @Inject(TEACHING_AGENT)
    private readonly teachingAgent: TeachingAgent,
  ) {}

  async teach(topic: string): Promise<RunResult> {
    try {
      return await this.teachingAgent.run(`$teach ${topic}`);
    } catch (error) {
      throw new Error('Teach skill invocation failed.', { cause: error });
    }
  }
}
