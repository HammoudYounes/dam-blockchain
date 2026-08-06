import { Inject, Injectable, Logger, InternalServerErrorException } from '@nestjs/common';
import { MintNftDto } from './dto/mint-nft.dto';
import { PinataService } from '../ipfs/pinata.service';
import { SignatureService } from '../signature/signature.service';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { Contract } from 'ethers';

@Injectable()
export class NftService {
  private readonly logger = new Logger(NftService.name);

  constructor(
    private readonly pinataService: PinataService,
    private readonly signatureService: SignatureService,
    private readonly httpService: HttpService,
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

  private async fetchImageBytes(
    imageUri: string,
  ): Promise<{ buffer: Buffer; filename: string; contentType?: string }> {
    const response = await firstValueFrom(
      this.httpService.get(imageUri, { responseType: 'arraybuffer' }),
    );
  const rawContentType = response.headers?.['content-type'];
  const contentType = typeof rawContentType === 'string' ? rawContentType : undefined;    const filename = imageUri.split('/').pop() || 'upload.jpg';
    return { buffer: Buffer.from(response.data), filename, contentType };
  }

  async mint(dto: MintNftDto): Promise<any> {
    const metadata = this.buildMetadata(dto);
    console.log(`Minting NFT with metadata: ${JSON.stringify(metadata)}`);
    const cid = await this.pinataService.pinJSON(metadata);
    const tokenUri = this.pinataService.getGatewayUrl(cid);
    console.log(`Metadata pinned with CID: ${cid}, URI: ${tokenUri}`);

    // Hash + sign the canonical pinned image with the service key
    const { buffer, filename, contentType } = await this.fetchImageBytes(dto.imageUri);
    const { hash, r, s, v } = await this.signatureService.sign(buffer, filename, contentType);

    // Mint asset
    let tokenId: string;
    let tx2: any;
    try {
      const tx = await this.assetContract.mintAsset(dto.creator, tokenUri);
      tx2 = tx;
      const receipt = await tx.wait();

      // Extract tokenId from AssetMinted event
      const event = receipt.logs.find(log => log.fragment?.name === 'AssetMinted');
      tokenId = event?.args?.tokenId?.toString();
      if (!tokenId) {
        throw new Error('AssetMinted event not found in mint receipt');
      }
    } catch (error) {
      this.logger.error(`mintAsset failed: ${error.message}`);
      throw new InternalServerErrorException('Failed to mint NFT');
    }

    // Register the hash + signature against the minted token
    try {
      const regTx = await this.signatureContract.registerSignature(
        tokenId, hash, r, s, v, dto.creator,
      );
      await regTx.wait();
    } catch (error) {
      this.logger.error(`registerSignature failed for tokenId=${tokenId}: ${error.message}`);
      throw new InternalServerErrorException(
        `NFT minted (tokenId=${tokenId}) but signature registration failed: ${error.message}`,
      );
    }

    return { status: 'minted', tokenId, tokenUri, imageUri: dto.imageUri, perceptualHash: hash, txHash: tx2.hash };
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
