import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { lastValueFrom } from 'rxjs';
import * as FormData from 'form-data';

@Injectable()
export class HashingService {
  private readonly hashingServiceUrl: string;

  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService,
  ) {
    this.hashingServiceUrl = this.configService.get<string>('HASHING_SERVICE_URL')!;
  }

  async getSimilarity(file: Express.Multer.File, k: number = 5) {
    const formData = new FormData();
    formData.append('newFile', file.buffer, {
      filename: file.originalname,
      contentType: file.mimetype,
    });
    formData.append('k', k.toString());

    const { data } = await lastValueFrom(
      this.httpService.post(`${this.hashingServiceUrl}/similarity`, formData, {
        headers: {
          ...formData.getHeaders(),
        },
      }),
    );
    return data;
  }

  async indexImage(file: Express.Multer.File) {
    const formData = new FormData();
    formData.append('newFile', file.buffer, {
      filename: file.originalname,
      contentType: file.mimetype,
    });

    const { data } = await lastValueFrom(
      this.httpService.post(`${this.hashingServiceUrl}/image`, formData, {
        headers: {
          ...formData.getHeaders(),
        },
      }),
    );
    return data;
  }
  
}
