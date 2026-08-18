import { Injectable, InternalServerErrorException } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom } from 'rxjs';
import * as FormData from 'form-data';

@Injectable()
export class SignatureService {
  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService,
  ) {}

  async sign(fileBuffer: Buffer, filename: string, contentType?: string) {
    const formData = new FormData();
    formData.append('file', fileBuffer, {
      filename,
      contentType: contentType || 'application/octet-stream',
    });

    const url = `${this.configService.get('HASHING_SERVICE_URL')}/sign`;

    try {
      const response = await firstValueFrom(
        this.httpService.post(url, formData, {
          headers: formData.getHeaders(),
        }),
      );
      return response.data;
    } catch (error) {
      console.error('Error calling hashing service:', error.message);
      throw new InternalServerErrorException('Failed to sign image');
    }
  }
}