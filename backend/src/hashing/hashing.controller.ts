import { Controller, Post, Body, UseInterceptors, UploadedFile, ParseFilePipe, MaxFileSizeValidator } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { HashingService } from './hashing.service';

@Controller('hashing')
export class HashingController {
  constructor(private readonly hashingService: HashingService) {}

  @Post('hash')
  @UseInterceptors(FileInterceptor('file'))
  async hash(@UploadedFile(new ParseFilePipe({ validators: [new MaxFileSizeValidator({ maxSize: 1024 * 1024 * 5 })] })) file: Express.Multer.File) {
    return this.hashingService.hash(file.buffer);
  }

  @Post('similarity')
  async similarity(@Body() body: { assetId: string; image: string }) {
    const imageBuffer = Buffer.from(body.image, 'base64');
    return this.hashingService.similarity(body.assetId, imageBuffer);
  }
}
