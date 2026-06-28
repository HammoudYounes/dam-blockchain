import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

const DAMDeployModule = buildModule("DAMDeployModule", (m) => {
  // Deploy DAMAsset first — no dependencies
  const damAsset = m.contract("DAMAsset");

  // Deploy DAMSignature second — no dependencies
  const damSignature = m.contract("DAMSignature");

  // Deploy DAMVerifier last — requires DAMSignature's address
  const damVerifier = m.contract("DAMVerifier", [damSignature]);

  return { damAsset, damSignature, damVerifier };
});

export default DAMDeployModule;