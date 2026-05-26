from hashing.algorithms.phash import compute, hamming_distance, similarity

image_path = "hashing/docs/image.jpg"
image_path2 = "hashing/docs/image2.jpg"

h = compute(image_path)
h2 = compute(image_path2)
print("Hash length:", len(h))
print("Hash length2:", len(h2))
print("Hash:", h)
print("Hash2:", h2)
print("Self-distance:", hamming_distance(h, h2))
print("Self-similarity:", similarity(h, h2))