import { Module } from '@nestjs/common';
import { ImageController } from './image.controller';
import { ImageService } from './image.service';
import { IpfsModule } from '../ipfs/ipfs.module';
import { HashingModule } from '../hashing/hashing.module';

@Module({
  imports: [IpfsModule, HashingModule],
  controllers: [ImageController],
  providers: [ImageService],
})
export class ImageModule {}