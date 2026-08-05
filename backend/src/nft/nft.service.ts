import { Injectable } from '@nestjs/common';
import { MintNftDto } from './dto/mint-nft.dto';
import { PinataService } from '../ipfs/pinata.service';

@Injectable()
export class NftService {
  constructor(private readonly pinataService: PinataService) {}

  private buildMetadata(dto: MintNftDto) {
    return {
      name: dto.name,
      description: dto.description,
      image: dto.imageUri,
      attributes: dto.attributes || [],
    };
  }

  async mint(dto: MintNftDto): Promise<any> {
    const metadata = this.buildMetadata(dto);
    const cid = await this.pinataService.pinJSON(metadata);
    const uri = `ipfs://${cid}`;
    // B6.2: call HashingService ...
    return { status: 'pinned', uri };
  }

  async findOne(tokenId: string): Promise<any> {
    // B6.4
    return { status: 'not implemented', tokenId };
  }

  async transfer(tokenId: string, to: string): Promise<any> {
    // B6.5
    return { status: 'not implemented', tokenId, to };
  }
}
