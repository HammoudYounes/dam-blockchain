import { Injectable } from '@nestjs/common';
import { PinataService } from './pinata.service';

@Injectable()
export class MetadataService {
  constructor(private pinataService: PinataService) {}

  async buildAndPinMetadata(
    name: string,
    description: string,
    imageIpfsHash: string,
    attributes: any[] = []
  ) {
    const metadata = {
      name,
      description,
      image: this.pinataService.getGatewayUrl(imageIpfsHash),
      attributes,
    };

    const ipfsHash = await this.pinataService.pinJSON(metadata);
    return this.pinataService.getGatewayUrl(ipfsHash);
  }
}
