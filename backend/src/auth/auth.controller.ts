import { Controller, Get, Post, Body, Query } from '@nestjs/common';
import { AuthService } from './auth.service';
import { LoginDto } from './dto/login.dto';
import { Public } from './jwt-auth/jwt-auth.guard';

@Controller('auth')
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @Public()
  @Get('nonce')
  getNonce(@Query('address') address: string) {
    if (!address) throw new Error('Address is required');
    return { nonce: this.authService.generateNonce(address) };
  }

  @Public()
  @Post('login')
  async login(@Body() loginDto: LoginDto) {
    return await this.authService.login(loginDto.address, loginDto.signature, loginDto.nonce);
  }
}
