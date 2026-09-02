import { Test, TestingModule } from '@nestjs/testing';
import { InternalServerErrorException } from '@nestjs/common';
import { of } from 'rxjs';
import { NftService } from './nft.service';
import { PinataService } from '../ipfs/pinata.service';
import { SignatureService } from '../signature/signature.service';
import { HashingService } from '../hashing/hashing.service';
import { HttpService } from '@nestjs/axios';

describe('NftService', () => {
  let service: NftService;
  let pinataService: PinataService;
  let signatureService: SignatureService;
  let hashingService: HashingService;
  let httpService: HttpService;
  let assetContract: any;
  let signatureContract: any;

  const dto = { imageUri: 'https://gateway.pinata.cloud/ipfs/testcid/image.jpg', creator: '0xCreatorAddress' };
  const signResult = { hash: '0xhash', r: '0xr', s: '0xs', v: 27, signature: '0xsig' };

  beforeEach(async () => {
    assetContract = {
      mintAsset: jest.fn().mockResolvedValue({
        wait: jest.fn().mockResolvedValue({
          logs: [{ fragment: { name: 'AssetMinted' }, args: { tokenId: 1 } }],
        }),
      }),
    };

    signatureContract = {
      registerSignature: jest.fn().mockResolvedValue({
        wait: jest.fn().mockResolvedValue({}),
      }),
    };

    const module: TestingModule = await Test.createTestingModule({
      providers: [
        NftService,
        {
          provide: PinataService,
          useValue: {
            pinJSON: jest.fn().mockResolvedValue('metadata-cid'),
            getGatewayUrl: jest.fn().mockReturnValue('https://gateway.pinata.cloud/ipfs/metadata-cid'),
          },
        },
        {
          provide: SignatureService,
          useValue: {
            sign: jest.fn().mockResolvedValue(signResult),
          },
        },
        {
          provide: HashingService,
          useValue: {
            getSimilarity: jest.fn(),
          },
        },
        {
          provide: HttpService,
          useValue: {
            get: jest.fn().mockReturnValue(
              of({
                data: Buffer.from('fake-image-bytes'),
                headers: { 'content-type': 'image/jpeg' },
              }),
            ),
          },
        },
        { provide: 'DAM_ASSET_CONTRACT', useValue: assetContract },
        { provide: 'DAM_SIGNATURE_CONTRACT', useValue: signatureContract },
        { provide: 'DAM_VERIFIER_CONTRACT', useValue: {} },
      ],
    }).compile();

    service = module.get<NftService>(NftService);
    pinataService = module.get<PinataService>(PinataService);
    signatureService = module.get<SignatureService>(SignatureService);
    hashingService = module.get<HashingService>(HashingService);
    httpService = module.get<HttpService>(HttpService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  describe('mint', () => {
    it('pins metadata, fetches image bytes, signs, mints, and registers the signature', async () => {
      const result = await service.mint(dto as any);

      expect(pinataService.pinJSON).toHaveBeenCalledWith({
        image: dto.imageUri,
        creator: dto.creator,
      });
      expect(httpService.get).toHaveBeenCalledWith(dto.imageUri, { responseType: 'arraybuffer' });
      expect(signatureService.sign).toHaveBeenCalledWith(
        Buffer.from('fake-image-bytes'),
        'image.jpg',
        'image/jpeg',
      );
      expect(assetContract.mintAsset).toHaveBeenCalledWith(
        dto.creator,
        'https://gateway.pinata.cloud/ipfs/metadata-cid',
      );
      expect(signatureContract.registerSignature).toHaveBeenCalledWith(
        '1', signResult.hash, signResult.r, signResult.s, signResult.v, dto.creator,
      );
      expect(result).toEqual({
        status: 'minted',
        tokenId: '1',
        tokenUri: 'https://gateway.pinata.cloud/ipfs/metadata-cid',
        imageUri: dto.imageUri,
        perceptualHash: signResult.hash,
      });
    });

    it('throws if mintAsset does not emit an AssetMinted event', async () => {
      assetContract.mintAsset.mockResolvedValueOnce({
        wait: jest.fn().mockResolvedValue({ logs: [] }),
      });

      await expect(service.mint(dto as any)).rejects.toThrow(InternalServerErrorException);
      expect(signatureContract.registerSignature).not.toHaveBeenCalled();
    });

    it('throws a descriptive error if registerSignature fails after a successful mint', async () => {
      signatureContract.registerSignature.mockRejectedValueOnce(new Error('reverted'));

      await expect(service.mint(dto as any)).rejects.toThrow(
        /NFT minted \(tokenId=1\) but signature registration failed/,
      );
    });
  });
});