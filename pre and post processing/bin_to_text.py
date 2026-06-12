def save_bits(filename, out_txt):
    with open(filename, "rb") as f:
        data = f.read()

    bitstring = ''.join(f'{byte:08b}' for byte in data)

    with open(out_txt, "w") as f:
        f.write(bitstring)


save_bits("F:/Documents/Academics/mini project/pre and post processing/misc/top10/img25.bin", "F:/Documents/Academics/mini project/pre and post processing/misc/top10/img25.txt")