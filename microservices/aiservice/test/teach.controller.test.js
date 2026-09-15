import assert from 'node:assert/strict';
import { test } from 'node:test';
import { HealthController } from '../dist/health.controller.js';

test('prefixes teaching prompts with $teach', async () => {
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
  const controller = new HealthController(codex);

  await controller.teach('Explain spaced repetition.');

  assert.deepEqual(prompts, ['$teach Explain spaced repetition.']);
});
