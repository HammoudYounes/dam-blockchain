import { 
  Controller, 
  Post, 
  UseInterceptors, 
  UploadedFile, 
  ParseFilePipe, 
  MaxFileSizeValidator 
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { PinataService } from './pinata.service';

@Controller('ipfs')
export class IpfsController {
  constructor(private pinataService: PinataService) {}

  @Post('upload')
  @UseInterceptors(FileInterceptor('file'))
  async uploadFile(
    @UploadedFile(
      new ParseFilePipe({
        validators: [new MaxFileSizeValidator({ maxSize: 1024 * 1024 * 10 })], // 10MB limit
      }),
    )
    file: Express.Multer.File,
  ) {
    // Note: Pinata SDK file() takes a File object, 
    // Express Multer gives a buffer-based object. 
    // Converting Buffer to Uint8Array as expected by File constructor.
    const fileObj = new File([new Uint8Array(file.buffer)], file.originalname, { type: file.mimetype });
    
    const cid = await this.pinataService.pinFile(fileObj, file.originalname);
    return { cid, ipfsUrl: this.pinataService.getGatewayUrl(cid) };
  }
}
