import { NestFactory } from '@nestjs/core';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
import { AppModule } from './app.module.js';

async function bootstrap() {
  const host = process.env.MICROSERVICE_HOST ?? '0.0.0.0';
  const port = Number(process.env.MICROSERVICE_PORT ?? 4001);
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(
    AppModule,
    {
      transport: Transport.TCP,
      options: { host, port },
    },
  );

  await app.listen();
  console.log(`Mindfully backend microservice listening on ${host}:${port}`);
}

await bootstrap();
