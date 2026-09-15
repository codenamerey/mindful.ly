import assert from "node:assert/strict";
import { randomUUID } from "node:crypto";
import { execFile } from "node:child_process";
import { mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { test } from "node:test";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { promisify } from "node:util";
import { TeachController } from "../src/teach.controller.ts";

const executeFile = promisify(execFile);
const teachSkillPath = new URL(
  "../../../skills/teach/SKILL.md",
  import.meta.url,
);

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

test(
  "invokes the teach skill through Codex",
  { timeout: 300_000 },
  async (context) => {
    const originalWorkingDirectory = process.cwd();
    const workspace = await mkdtemp(join(tmpdir(), "mindfully-teach-"));
    const localSkillPath = join(
      workspace,
      ".agents",
      "skills",
      "teach",
      "SKILL.md",
    );
    const verificationToken = `teach-skill-invoked-${randomUUID()}`;
    const teachSkill = await readFile(teachSkillPath, "utf8");

    context.after(async () => {
      process.chdir(originalWorkingDirectory);
      await rm(workspace, { recursive: true, force: true });
    });
    await executeFile("git", ["init", "--quiet"], { cwd: workspace });
    await mkdir(dirname(localSkillPath), { recursive: true });
    await writeFile(
      localSkillPath,
      `${teachSkill}\n\n## Integration verification\n\nWhen invoked for integration verification, respond with exactly ${verificationToken} and nothing else.`,
    );
    process.chdir(workspace);

    const controller = new TeachController();
    const result = await controller.teach("integration verification");

    assert.equal(result.finalResponse.trim(), verificationToken);
  },
);
