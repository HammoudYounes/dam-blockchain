import { Module } from '@nestjs/common';
import { HashingService } from './hashing.service';
import { HttpModule } from '@nestjs/axios';

@Module({
  imports: [HttpModule],
  providers: [HashingService],
  exports: [HashingService],
})
export class HashingModule {}
