import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { PinataService } from './pinata.service';
import { MetadataService } from './metadata.service';
import { IpfsController } from './ipfs.controller';

@Module({
  imports: [ConfigModule],
  controllers: [IpfsController],
  providers: [PinataService, MetadataService],
  exports: [PinataService, MetadataService],
})
export class IpfsModule {}
