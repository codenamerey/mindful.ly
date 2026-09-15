import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const host = process.env.HOST ?? '0.0.0.0';
  const port = Number(process.env.PORT ?? 4000);
  const app = await NestFactory.create(AppModule);

  await app.listen(port, host);
  console.log(`Mindfully backend listening on http://${host}:${port}`);
}

await bootstrap();
