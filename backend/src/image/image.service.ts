import { Injectable } from '@nestjs/common';
import { PinataService } from '../ipfs/pinata.service';
import { HashingService } from '../hashing/hashing.service';

@Injectable()
export class ImageService {
  constructor(private readonly pinataService: PinataService, private readonly hashingService: HashingService) { }

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

        const result = await this.hashingService.getSimilarity(file);


        // Check for duplicate based on user provided structure
        const isDuplicate = result.data.similar_images.some(
          (img: any) => img.duplicateProbability > 0.70,
        );

        if (isDuplicate) {
          return {
            originalname: file.originalname,
            size: file.size,
            mimetype: file.mimetype,
            cid: null,
            imageUri: null,
            isDuplicate: true,
          };
        }

        const cid = await this.pinataService.pinFile(fileObj, file.originalname);

        return {
          originalname: file.originalname,
          size: file.size,
          mimetype: file.mimetype,
          cid,
          imageUri: this.pinataService.getGatewayUrl(cid),
          isDuplicate: isDuplicate,
          result: {
            status: 'success',
            data: result,
          },
        };
      }),
    );
  }
}