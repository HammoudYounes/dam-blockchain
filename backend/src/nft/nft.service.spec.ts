import { Test, TestingModule } from '@nestjs/testing';
import { NftService } from './nft.service';
import { PinataService } from '../ipfs/pinata.service';

describe('NftService', () => {
  let service: NftService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        NftService,
        {
          provide: PinataService,
          useValue: {
            pinJSON: jest.fn(),
            getGatewayUrl: jest.fn(),
          },
        },
        {
          provide: 'DAM_ASSET_CONTRACT',
          useValue: { mintAsset: jest.fn() },
        },
        {
          provide: 'DAM_SIGNATURE_CONTRACT',
          useValue: {},
        },
        {
          provide: 'DAM_VERIFIER_CONTRACT',
          useValue: {},
        },
      ],
    }).compile();

    service = module.get<NftService>(NftService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });
});
