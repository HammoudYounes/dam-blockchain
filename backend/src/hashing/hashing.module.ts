import { Module } from '@nestjs/common';
import { HashingService } from './hashing.service';
import { HashingController } from './hashing.controller';
import { HttpModule } from '@nestjs/axios';
import { ConfigModule } from '@nestjs/config';

@Module({
  imports: [
    HttpModule.registerAsync({
      imports: [ConfigModule],
      useFactory: async () => ({
        baseURL: process.env.HASHING_SERVICE_URL,
        timeout: 5000,
      }),
    }),
  ],
  controllers: [HashingController],
  providers: [HashingService],
  exports: [HashingService],
})
export class HashingModule {}
