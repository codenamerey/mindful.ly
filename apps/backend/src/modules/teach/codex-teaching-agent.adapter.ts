import { Injectable } from '@nestjs/common';
import { Codex, type RunResult } from '@openai/codex-sdk';
import type { TeachingAgent } from './teaching-agent.port.js';

@Injectable()
export class CodexTeachingAgent implements TeachingAgent {
  private readonly codex = new Codex();

  async run(prompt: string): Promise<RunResult> {
    return await this.codex.startThread().run(prompt);
  }
}
