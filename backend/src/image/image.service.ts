import { Injectable } from '@nestjs/common';

@Injectable()
export class ImageService {
  async processUploads(files: Array<Express.Multer.File>) {
    if (!files) {
      return [];
    }
    // For now, just return file metadata as proof of receipt
    return files.map(file => ({
      originalname: file.originalname,
      size: file.size,
      mimetype: file.mimetype,
    }));
  }
}
