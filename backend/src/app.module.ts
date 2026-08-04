import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { HashingModule } from './hashing/hashing.module';
import { ImageModule } from './image/image.module';
import { SignatureModule } from './signature/signature.module';
import { NftModule } from './nft/nft.module';
import { AuthModule } from './auth/auth.module';
import { IpfsModule } from './ipfs/ipfs.module';
import { APP_GUARD } from '@nestjs/core';
import { JwtAuthGuard } from './auth/jwt-auth/jwt-auth.guard';

@Module({
  imports: [HashingModule, ImageModule, SignatureModule, NftModule, AuthModule, IpfsModule],
  controllers: [AppController],
  providers: [
    AppService,
    {
      provide: APP_GUARD,
      useClass: JwtAuthGuard,
    },
  ],
})
export class AppModule {}
