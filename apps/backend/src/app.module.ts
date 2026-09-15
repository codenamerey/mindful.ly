import { Module } from '@nestjs/common';
import { HealthModule } from './modules/health/health.module.js';
import { TeachModule } from './modules/teach/teach.module.js';

@Module({
  imports: [HealthModule, TeachModule],
})
export class AppModule {}
