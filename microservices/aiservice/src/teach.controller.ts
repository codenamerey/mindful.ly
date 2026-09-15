import { Controller } from "@nestjs/common";
import { Codex } from "@openai/codex-sdk";
@Controller()
export class TeachController {
  constructor(codex: Codex) {
    this.codex = codex;
  }

  teach(topic: string) {
    const thread = this.codex.startThread();
    const result = thread.run(`$teach ${topic}`);

    return result;
  }
}
