import { Test, TestingModule } from '@nestjs/testing';
import { HashingService } from './hashing.service';
import { HttpModule } from '@nestjs/axios';
import { ConfigModule } from '@nestjs/config';

describe('HashingService', () => {
  let service: HashingService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      imports: [HttpModule, ConfigModule.forRoot()],
      providers: [HashingService],
    }).compile();

    service = module.get<HashingService>(HashingService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });
});
