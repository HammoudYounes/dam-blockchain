import { Injectable, UnauthorizedException } from '@nestjs/common';
import { ethers } from 'ethers';
import * as crypto from 'crypto';
import * as jwt from 'jsonwebtoken';

@Injectable()
export class AuthService {
  private nonces = new Map<string, string>(); // In-memory nonce storage: address -> nonce

  generateNonce(address: string): string {
    const nonce = crypto.randomBytes(32).toString('hex');
    this.nonces.set(address.toLowerCase(), nonce);
    return nonce;
  }

  async login(address: string, signature: string, nonce: string) {
    const storedNonce = this.nonces.get(address.toLowerCase());
    if (!storedNonce || storedNonce !== nonce) {
      throw new UnauthorizedException('Invalid nonce');
    }

    // Verify signature
    const message = `Sign this message to login: ${nonce}`;
    const recoveredAddress = ethers.verifyMessage(message, signature);

    if (recoveredAddress.toLowerCase() !== address.toLowerCase()) {
      throw new UnauthorizedException('Invalid signature');
    }

    // Nonce consumed
    this.nonces.delete(address.toLowerCase());

    // Generate JWT
    const token = jwt.sign(
      { address: address.toLowerCase() },
      process.env.JWT_SECRET || 'super-secret-key',
      { expiresIn: '1h' },
    );
    return { token };
  }
}
