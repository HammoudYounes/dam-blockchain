import { Test, TestingModule } from '@nestjs/testing';
import { ImageController } from './image.controller';
import { ImageService } from './image.service';

describe('ImageController', () => {
  let controller: ImageController;
  let service: ImageService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [ImageController],
      providers: [
        {
          provide: ImageService,
          useValue: {
            processUploads: jest.fn().mockResolvedValue([{ originalname: 'test.jpg' }]),
          },
        },
      ],
    }).compile();

    controller = module.get<ImageController>(ImageController);
    service = module.get<ImageService>(ImageService);
  });

  it('should call ImageService.processUploads with files', async () => {
    const mockFiles = [{ originalname: 'test.jpg' } as Express.Multer.File];
    const result = await controller.uploadFiles(mockFiles);
    expect(service.processUploads).toHaveBeenCalledWith(mockFiles);
    expect(result).toEqual([{ originalname: 'test.jpg' }]);
  });
});
