import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { lastValueFrom } from 'rxjs';
import * as fs from 'fs';
import { PhashResponseDto } from './dto/phash-response.dto';
const FormData = require('form-data');

@Injectable()
export class ImageService {
  constructor(private httpService: HttpService) {}

  async processUploads(files: Array<Express.Multer.File>) {
    if (!files) {
      return [];
    }

    return Promise.all(files.map(async (file) => {
      const formData = new FormData();
      formData.append('newFile', fs.createReadStream(file.path), file.originalname);

      const response = await lastValueFrom(
        this.httpService.post<PhashResponseDto>('http://hashing-service:8001/phash', formData, {
          headers: formData.getHeaders(),
        })
      );

      return {
        originalname: file.originalname,
        path: file.path,
        size: file.size,
        mimetype: file.mimetype,
        phash: response.data.data.phash,
      };
    }));
  }
}
