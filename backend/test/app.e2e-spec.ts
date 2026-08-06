import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import * as request from 'supertest';
import { App } from 'supertest/types';
import { AppModule } from './../src/app.module';
import { BlockchainService } from './../src/blockchain/blockchain.service';

describe('AppController (e2e)', () => {
  let app: INestApplication<App>;

  beforeEach(async () => {
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    })
      // BlockchainService's real constructor requires a live Alchemy RPC URL
      // and a funded deployer private key -- neither exists in CI, and this
      // test only exercises the root health-check route, which has nothing
      // to do with the chain. Stubbing it here satisfies the three
      // DAM_*_CONTRACT factory providers (which call these methods) without
      // needing real credentials at all.
      .overrideProvider(BlockchainService)
      .useValue({
        getAssetContract: () => ({}),
        getSignatureContract: () => ({}),
        getVerifierContract: () => ({}),
      })
      .compile();

    app = moduleFixture.createNestApplication();
    await app.init();
  });

  it('/ (GET)', () => {
    return request(app.getHttpServer())
      .get('/')
      .expect(200)
      .expect('Hello World!');
  });

  afterEach(async () => {
    await app.close();
  });
});