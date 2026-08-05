import { Test, TestingModule } from '@nestjs/testing';
import { ImageService } from './image.service';
import { HttpService } from '@nestjs/axios';
import { PinataService } from '../ipfs/pinata.service';

describe('ImageService', () => {
  let service: ImageService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        ImageService,
        {
          provide: HttpService,
          useValue: { post: jest.fn() },
        },
        {
          provide: PinataService,
          useValue: { pinFile: jest.fn() },
        },
      ],
    }).compile();

    service = module.get<ImageService>(ImageService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });
});
