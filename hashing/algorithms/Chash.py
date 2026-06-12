import numpy as np
from PIL import Image

IMAGE_SIZE = (32, 32) 
S_MIN      = 25
NUM_BINS   = 8
BIN_WIDTH  = 256 // NUM_BINS   # 32 units per bin in PIL's 0-255 hue range

_EMPTY_ZONE = -1  # sentinel: zone had no colorful (unmasked) pixels


class CHash:
    """
    Spatial color hash.

    Encodes the *relative* dominant hue and mean saturation of each zone
    in a 4×4 grid → 64-bit hash invariant to global channel shifts.

    Falls back to a luminance-zone hash for grayscale / near-grayscale images.
    Never compare a color-mode hash against a fallback-mode hash:
    hamming_distance returns 64 (max distance) in that case.
    """

    def __init__(self, image_input: str | Image.Image) -> None:
        self.is_fallback: bool = False          # set inside _compute_hash
        self.raw_data: np.ndarray = self._load_as_hsv(image_input)
        self.hash_int: int  = self._compute_hash()
        self.hash_hex: str  = format(self.hash_int, "016x")

    # ------------------------------------------------------------------
    # Properties / dunder
    # ------------------------------------------------------------------

    def mode(self) -> str:
        return "fallback" if self.is_fallback else "color"

    def __repr__(self) -> str:
        return f"CHash(hex='{self.hash_hex}', mode={self.mode()})"

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_as_hsv(self, data: str | Image.Image) -> np.ndarray:
        if isinstance(data, str):
            im = Image.open(data)
        elif isinstance(data, Image.Image):
            im = data
        else:
            raise TypeError("Expected a file path or PIL Image")

        # convert("RGB") normalises RGBA / palette / grayscale inputs before
        # resizing; LANCZOS gives better colour averaging than nearest/bilinear.
        im = im.convert("RGB").resize(IMAGE_SIZE, Image.LANCZOS)
        # PIL HSV: H 0-255 → 0-360°, S 0-255 → 0-100%, V 0-255 → 0-100%
        return np.array(im.convert("HSV"), dtype=np.uint8)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_dominant_bin(self, h_channel: np.ndarray, mask: np.ndarray) -> int:
        """
        Most frequent hue bin (0-7) among unmasked pixels.
        Returns _EMPTY_ZONE (-1) when no valid pixels exist in the region,
        so callers can distinguish a genuinely gray zone from bin-0 (red).
        """
        valid_hues = h_channel[mask]
        if valid_hues.size == 0:
            return _EMPTY_ZONE
        counts = np.bincount(valid_hues // BIN_WIDTH, minlength=NUM_BINS)
        return int(np.argmax(counts))

    def _compute_fallback_hash(self, v_chan: np.ndarray) -> int:
        """
        Luminance-zone hash for grayscale images: 1 bit per zone,
        16 bits total, zero-padded to 64 bits.
        Only meaningful when compared against other fallback-mode hashes.
        """
        global_mean_v = v_chan.mean()
        bits: list[str] = [
            "1" if v_chan[r*8:(r+1)*8, c*8:(c+1)*8].mean() >= global_mean_v else "0"
            for r in range(4)
            for c in range(4)
        ]
        return int("".join(bits).ljust(64, "0"), 2)

    # ------------------------------------------------------------------
    # Main hash
    # ------------------------------------------------------------------

    def _compute_hash(self) -> int:
        h_chan = self.raw_data[..., 0]
        s_chan = self.raw_data[..., 1]
        v_chan = self.raw_data[..., 2]

        mask = s_chan >= S_MIN

        # Grayscale fallback: entire image has no meaningful hue signal
        self.is_fallback = not bool(np.any(mask))
        if self.is_fallback:
            return self._compute_fallback_hash(v_chan)

        h_global = self._get_dominant_bin(h_chan, mask)         # always 0-7 here
        global_mean_sat = s_chan[mask].mean()                   # safe: mask non-empty

        bits: list[str] = []

        for r in range(4):
            for c in range(4):
                sl = np.s_[r*8:(r+1)*8, c*8:(c+1)*8]
                z_h, z_s, z_mask = h_chan[sl], s_chan[sl], mask[sl]

                h_zone = self._get_dominant_bin(z_h, z_mask)

                if h_zone == _EMPTY_ZONE:
                    # Gray zone: encode as neutral 0000 rather than letting
                    # (0 - h_global) % 8 produce a spurious hue offset.
                    bits.append("0000")
                    continue

                offset  = (h_zone - h_global) % NUM_BINS
                # z_mask is non-empty here (h_zone != _EMPTY_ZONE guarantees it)
                sat_bit = 1 if z_s[z_mask].mean() >= global_mean_sat else 0

                bits.append(format(offset, "03b"))
                bits.append(str(sat_bit))

        return int("".join(bits), 2)

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def hamming_distance(self, other: CHash) -> int:
        if self.is_fallback != other.is_fallback:
            # Cross-mode comparison is structurally meaningless.
            # Return max distance so downstream code treats them as dissimilar
            # rather than crashing the benchmark loop.
            return 64
        return bin(self.hash_int ^ other.hash_int).count("1")

    def similarity(self, other: CHash) -> float:
        return 1.0 - self.hamming_distance(other) / 64.0