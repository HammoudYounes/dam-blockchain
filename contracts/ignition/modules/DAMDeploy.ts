// ignition/modules/DAMDeploy.ts
import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

const TRUSTED_SIGNER_ADDRESS = process.env.TRUSTED_SIGNER_ADDRESS as string;
const EXISTING_DAM_ASSET_ADDRESS = "0xE7127207eB3E24B34021344aCB7D7Cff5D092A59";

const DAMDeployModule = buildModule("DAMDeployModule", (m) => {
  if (!TRUSTED_SIGNER_ADDRESS) {
    throw new Error(
      "TRUSTED_SIGNER_ADDRESS is not set in contracts/.env. This must be the public " +
      "address matching the hashing service's PRIVATE_KEY."
    );
  }

  const trustedSigner = m.getParameter("trustedSigner", TRUSTED_SIGNER_ADDRESS);

  // DAMAsset is unchanged — reuse the already-deployed instance rather than redeploying it.
  const damAsset = m.contractAt("DAMAsset", EXISTING_DAM_ASSET_ADDRESS);

  const damSignature = m.contract("DAMSignature", [damAsset, trustedSigner]);
  const damVerifier = m.contract("DAMVerifier", [damSignature]);

  return { damAsset, damSignature, damVerifier };
});

export default DAMDeployModule;