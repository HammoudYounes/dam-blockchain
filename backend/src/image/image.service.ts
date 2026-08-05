import { Injectable } from '@nestjs/common';
import { PinataService } from '../ipfs/pinata.service';

@Injectable()
export class ImageService {
  constructor(private readonly pinataService: PinataService) {}

  async processUploads(files: Array<Express.Multer.File>) {
    if (!files || files.length === 0) {
      return [];
    }

    return Promise.all(
      files.map(async (file) => {
        const fileObj = new File(
          [new Uint8Array(file.buffer)],
          file.originalname,
          { type: file.mimetype },
        );
        const cid = await this.pinataService.pinFile(fileObj, file.originalname);

        return {
          originalname: file.originalname,
          size: file.size,
          mimetype: file.mimetype,
          cid,
          imageUri: `ipfs://${cid}`,
        };
      }),
    );
  }
}