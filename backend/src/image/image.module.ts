import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { ImageController } from './image.controller';
import { ImageService } from './image.service';

@Module({
  imports: [HttpModule],
  controllers: [ImageController],
  providers: [ImageService]
})
export class ImageModule {}
