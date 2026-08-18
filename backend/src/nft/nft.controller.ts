import { Controller, Post, Get, Body, Param } from '@nestjs/common';
import { NftService } from './nft.service';
import { MintNftDto } from './dto/mint-nft.dto';
import { TransferNftDto } from './dto/transfer-nft.dto';

@Controller('nft')
export class NftController {
  constructor(private readonly nftService: NftService) {}

  @Post('mint')
  async mint(@Body() dto: MintNftDto) {
    return this.nftService.mint(dto);
  }

  @Get(':tokenId')
  async findOne(@Param('tokenId') tokenId: string) {
    return this.nftService.findOne(tokenId);
  }

  @Post(':tokenId/transfer')
  async transfer(@Param('tokenId') tokenId: string, @Body() dto: TransferNftDto) {
    return this.nftService.transfer(tokenId, dto.to);
  }
}
