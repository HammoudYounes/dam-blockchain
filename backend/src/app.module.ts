import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { ImageModule } from './image/image.module';
import { SignatureModule } from './signature/signature.module';
import { NftModule } from './nft/nft.module';
import { AuthModule } from './auth/auth.module';

@Module({
  imports: [ImageModule, SignatureModule, NftModule, AuthModule],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
