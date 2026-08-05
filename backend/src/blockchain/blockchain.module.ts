import { Module, Global } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { ethers } from 'ethers';
import { BlockchainService } from './blockchain.service';

@Global()
@Module({
  imports: [ConfigModule],
  providers: [
    BlockchainService,
    {
      provide: 'DAM_ASSET_CONTRACT',
      useFactory: (blockchainService: BlockchainService) => blockchainService.getAssetContract(),
      inject: [BlockchainService],
    },
    {
      provide: 'DAM_SIGNATURE_CONTRACT',
      useFactory: (blockchainService: BlockchainService) => blockchainService.getSignatureContract(),
      inject: [BlockchainService],
    },
    {
      provide: 'DAM_VERIFIER_CONTRACT',
      useFactory: (blockchainService: BlockchainService) => blockchainService.getVerifierContract(),
      inject: [BlockchainService],
    },
  ],
  exports: [
    BlockchainService,
    'DAM_ASSET_CONTRACT',
    'DAM_SIGNATURE_CONTRACT',
    'DAM_VERIFIER_CONTRACT',
  ],
})
export class BlockchainModule {}
