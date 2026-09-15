import { Controller } from "@nestjs/common";
import { Codex } from "@openai/codex-sdk";
@Controller()
export class TeachController {
  constructor(private readonly codex: Codex = new Codex()) {
    this.codex = codex;
  }

  async teach(topic: string) {
    try {
      const thread = this.codex.startThread();
      const result = await thread.run(`$teach ${topic}`);

      return result;
    } catch (error) {
      throw new Error("Teach skill invocation failed.");
    }
  }
}
