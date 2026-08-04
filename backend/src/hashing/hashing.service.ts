import { Injectable, InternalServerErrorException, BadGatewayException, RequestTimeoutException } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { lastValueFrom } from 'rxjs';
import { AxiosError } from 'axios';
import FormData from 'form-data';

@Injectable()
export class HashingService {
  constructor(private readonly httpService: HttpService) {}

  async hash(imageBuffer: Buffer): Promise<any> {
    const form = new FormData();
    form.append('file', imageBuffer, { filename: 'image.png' });
    try {
      const { data } = await lastValueFrom(
        this.httpService.post('/hash', form, {
          headers: { ...form.getHeaders() },
        }),
      );
      return data;
    } catch (error) {
      this.handleError(error);
    }
  }

  async similarity(assetId: string, imageBuffer: Buffer): Promise<any> {
    try {
      const { data } = await lastValueFrom(
        this.httpService.post(`/similarity`, { assetId, image: imageBuffer.toString('base64') }),
      );
      return data;
    } catch (error) {
      this.handleError(error);
    }
  }

  async index(assetId: string, imageBuffer: Buffer): Promise<void> {
    try {
      await lastValueFrom(
        this.httpService.post('/index', { assetId, image: imageBuffer.toString('base64') }),
      );
    } catch (error) {
      this.handleError(error);
    }
  }

  async deleteIndex(assetId: string): Promise<void> {
    try {
      await lastValueFrom(this.httpService.delete(`/index/${assetId}`));
    } catch (error) {
      this.handleError(error);
    }
  }

  private handleError(error: any): never {
    if (error instanceof AxiosError) {
      if (!error.response) {
        throw new BadGatewayException('Hashing service unavailable');
      }
      if (error.code === 'ECONNABORTED') {
        throw new RequestTimeoutException('Hashing service timeout');
      }
    }
    throw new InternalServerErrorException('Hashing service error');
  }
}
