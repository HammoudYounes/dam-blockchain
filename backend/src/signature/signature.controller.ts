import {
  Controller,
  Post,
  UploadedFile,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { SignatureService } from './signature.service';

@Controller('signature')
export class SignatureController {
  constructor(private readonly signatureService: SignatureService) {}

  @Post('sign')
  @UseInterceptors(FileInterceptor('file'))
  async sign(@UploadedFile() file: Express.Multer.File) {
    return await this.signatureService.sign(file.buffer, file.originalname);
  }
}
