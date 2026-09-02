import { Test, TestingModule } from '@nestjs/testing';
import { ImageService } from './image.service';
import { HashingService } from '../hashing/hashing.service';
import { HttpService } from '@nestjs/axios';
import { PinataService } from '../ipfs/pinata.service';

describe('ImageService', () => {
  let service: ImageService;
  let hashingService: HashingService;
  let pinataService: PinataService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        ImageService,
        {
          provide: HashingService,
          useValue: { getSimilarity: jest.fn() },
        },
        {
          provide: HttpService,
          useValue: { post: jest.fn() },
        },
        {
          provide: PinataService,
          useValue: { pinFile: jest.fn(), getGatewayUrl: jest.fn() },
        },
      ],
    }).compile();

    service = module.get<ImageService>(ImageService);
    hashingService = module.get<HashingService>(HashingService);
    pinataService = module.get<PinataService>(PinataService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  it('should detect duplicate when similarity > 0.70', async () => {
    const mockFile = { buffer: Buffer.from('test'), originalname: 'test.jpg', mimetype: 'image/jpeg' } as Express.Multer.File;
    jest.spyOn(hashingService, 'getSimilarity').mockResolvedValue({
      data: { similar_images: [{ duplicateProbability: 0.8 }] }
    });
    jest.spyOn(pinataService, 'getGatewayUrl').mockReturnValue('url');
    jest.spyOn(pinataService, 'pinFile').mockResolvedValue('cid1');
    
    const result = await service.processUploads([mockFile]);
    
    expect(result[0].isDuplicate).toBe(true);
    expect(result[0].cid).toBe(null);
    expect(result[0].result).toBeUndefined();
  });
});
