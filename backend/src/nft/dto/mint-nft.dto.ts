export class MintNftDto {
  name!: string;
  description!: string;
  imageUri!: string;
  attributes?: { trait_type: string; value: string | number }[];
}
