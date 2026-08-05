import { Test, TestingModule } from '@nestjs/testing';
import { SignatureService } from './signature.service';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { of } from 'rxjs';

describe('SignatureService', () => {
  let service: SignatureService;
  let httpService: HttpService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [
        SignatureService,
        {
          provide: HttpService,
          useValue: {
            post: jest.fn(),
          },
        },
        {
          provide: ConfigService,
          useValue: {
            get: jest.fn().mockReturnValue('http://localhost:8001'),
          },
        },
      ],
    }).compile();

    service = module.get<SignatureService>(SignatureService);
    httpService = module.get<HttpService>(HttpService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });

  it('should call hashing service and return data', async () => {
    const mockResponse = {
      data: {
        hash: '0x123',
        r: '0xabc',
        s: '0xdef',
        v: 27,
        signature: '0x...',
      },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {},
    };
    jest.spyOn(httpService, 'post').mockReturnValue(of(mockResponse as any));

    const result = await service.sign(Buffer.from('test'), 'test.jpg');
    expect(httpService.post).toHaveBeenCalled();
    expect(result).toEqual(mockResponse.data);
  });
});
