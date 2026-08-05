import { Injectable } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { ethers } from 'ethers';
import * as DAMAssetABI from './abis/DAMAsset.json';
import * as DAMSignatureABI from './abis/DAMSignature.json';
import * as DAMVerifierABI from './abis/DAMVerifier.json';

@Injectable()
export class BlockchainService {
  private provider: ethers.JsonRpcProvider;
  private signer: ethers.Wallet;

  constructor(private configService: ConfigService) {
    const rpcUrl = this.configService.get<string>('ALCHEMY_AMOY_URL');
    const privateKey = this.configService.get<string>('DEPLOYER_PRIVATE_KEY');

    if (!rpcUrl || !privateKey) {
      throw new Error('Blockchain configuration missing');
    }

    this.provider = new ethers.JsonRpcProvider(rpcUrl);
    this.signer = new ethers.Wallet(privateKey, this.provider);
  }

  getAssetContract() {
    return new ethers.Contract(
      this.configService.get<string>('DAM_ASSET_ADDRESS')!,
      DAMAssetABI,
      this.signer,
    );
  }

  getSignatureContract() {
    return new ethers.Contract(
      this.configService.get<string>('DAM_SIGNATURE_ADDRESS')!,
      DAMSignatureABI,
      this.signer,
    );
  }

  getVerifierContract() {
    return new ethers.Contract(
      this.configService.get<string>('DAM_VERIFIER_ADDRESS')!,
      DAMVerifierABI,
      this.signer,
    );
  }
}
