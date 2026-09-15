import assert from "node:assert/strict";
import { test } from "node:test";
import { TeachController } from "../src/teach.controller.ts";
test("prefixes teaching prompts with $teach", async () => {
  const prompts = [];
  const codex = {
    startThread() {
      return {
        async run(prompt) {
          prompts.push(prompt);
        },
      };
    },
  };
  const controller = new TeachController(codex);

  await controller.teach("Explain spaced repetition.");

  assert.deepEqual(prompts, ["$teach Explain spaced repetition."]);
});
