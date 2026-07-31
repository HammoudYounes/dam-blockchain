import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { PinataSDK } from 'pinata';

@Injectable()
export class PinataService {
  private readonly pinata: PinataSDK;
  private readonly logger = new Logger(PinataService.name);

  constructor(private configService: ConfigService) {
    const jwt = this.configService.get<string>('PINATA_JWT');
    const gateway = this.configService.get<string>('PINATA_GATEWAY');
    this.pinata = new PinataSDK({
      pinataJwt: jwt,
      pinataGateway: gateway,
    });
  }

  async pinFile(file: File, fileName: string) {
    try {
      const upload = await this.pinata.upload.public.file(file);
      return upload.cid;
    } catch (error) {
      this.logger.error(`Error pinning file: ${error.message}`);
      throw error;
    }
  }

  async pinJSON(metadata: any) {
    try {
      const upload = await this.pinata.upload.public.json(metadata);
      return upload.cid;
    } catch (error) {
      this.logger.error(`Error pinning JSON: ${error.message}`);
      throw error;
    }
  }
}
