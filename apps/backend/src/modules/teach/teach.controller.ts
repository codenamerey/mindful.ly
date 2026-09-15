import { BadRequestException, Body, Controller, Post } from '@nestjs/common';
import { TeachService } from './teach.service.js';

@Controller('teach')
export class TeachController {
  constructor(private readonly teachService: TeachService) {}

  @Post()
  teach(@Body('topic') topic: unknown) {
    if (typeof topic !== 'string' || topic.trim().length === 0) {
      throw new BadRequestException('topic must be a non-empty string');
    }

    return this.teachService.teach(topic.trim());
  }
}
