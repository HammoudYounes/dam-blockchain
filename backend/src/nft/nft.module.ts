import { Module } from '@nestjs/common';
import { NftController } from './nft.controller';
import { NftService } from './nft.service';
import { IpfsModule } from '../ipfs/ipfs.module';
import { SignatureModule } from '../signature/signature.module';
import { HttpModule } from '@nestjs/axios';


@Module({
  imports: [IpfsModule, SignatureModule, HttpModule],
  controllers: [NftController],
  providers: [NftService],
  exports: [NftService],
})
export class NftModule {}
