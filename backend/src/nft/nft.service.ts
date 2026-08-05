import { Inject, Injectable } from '@nestjs/common';
import { MintNftDto } from './dto/mint-nft.dto';
import { PinataService } from '../ipfs/pinata.service';
import { Contract } from 'ethers';

@Injectable()
export class NftService {
  constructor(
    private readonly pinataService: PinataService,
    @Inject('DAM_ASSET_CONTRACT') private readonly assetContract: Contract,
    @Inject('DAM_SIGNATURE_CONTRACT') private readonly signatureContract: Contract,
    @Inject('DAM_VERIFIER_CONTRACT') private readonly verifierContract: Contract,
  ) { }

  private buildMetadata(dto: MintNftDto) {
    return {
      image: dto.imageUri,
      creator: dto.creator,
    };
  }

  async mint(dto: MintNftDto): Promise<any> {
    const metadata = this.buildMetadata(dto);
    console.log(`Minting NFT with metadata: ${JSON.stringify(metadata)}`);
    const cid = await this.pinataService.pinJSON(metadata);
    const uri = this.pinataService.getGatewayUrl(cid);
    console.log(`Metadata pinned with CID: ${cid}, URI: ${uri}`);

    // Mint asset
    const tx = await this.assetContract.mintAsset(dto.creator, uri);
    const receipt = await tx.wait();

    // Extract tokenId from AssetMinted event
    const event = receipt.logs.find(log => log.fragment?.name === 'AssetMinted');
    const tokenId = event?.args?.tokenId.toString();

    return { status: 'minted', tokenId, uri };
  }

  async findOne(tokenId: string): Promise<any> {
    // B6.4: Implement using this.assetContract
    return { status: 'not implemented', tokenId };
  }

  async transfer(tokenId: string, to: string): Promise<any> {
    // B6.5: Implement using this.assetContract
    return { status: 'not implemented', tokenId, to };
  }
}
