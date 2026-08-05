import { Injectable } from '@nestjs/common';

@Injectable()
export class ImageService {
  async processUploads(files: Array<Express.Multer.File>) {
    if (!files) {
      return [];
    }
    return files.map(file => ({
      originalname: file.originalname,
      path: file.path,
      size: file.size,
      mimetype: file.mimetype,
    }));
  }
}
