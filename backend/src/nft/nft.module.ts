import { Module } from '@nestjs/common';
import { NftController } from './nft.controller';
import { NftService } from './nft.service';
import { IpfsModule } from '../ipfs/ipfs.module';

@Module({
  imports: [IpfsModule],
  controllers: [NftController],
  providers: [NftService],
  exports: [NftService],
})
export class NftModule {}
