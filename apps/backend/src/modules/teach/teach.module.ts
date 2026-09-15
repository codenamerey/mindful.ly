import { Module } from '@nestjs/common';
import { CodexTeachingAgent } from './codex-teaching-agent.adapter.js';
import { TeachController } from './teach.controller.js';
import { TeachService } from './teach.service.js';
import { TEACHING_AGENT } from './teaching-agent.port.js';

@Module({
  controllers: [TeachController],
  providers: [
    TeachService,
    {
      provide: TEACHING_AGENT,
      useClass: CodexTeachingAgent,
    },
  ],
})
export class TeachModule {}
