import random
import string


def create_dummy_file(filename="10k.txt", num_lines=10000, pattern_length=8):
    """
    Creates a dummy text file with a specified number of unique strings
    following the pattern 'digit;digit;digit;digit;digit;digit;digit;digit;'.

    Args:
        filename: The name of the file to create.
        num_lines: The number of unique lines to generate.
        pattern_length: The number of semicolon-separated digits in each line.
    """
    unique_strings = set()
    while len(unique_strings) < num_lines:
        random_digits = [random.choice(string.digits) for _ in range(pattern_length)]
        unique_strings.add(";".join(random_digits) + ";")

    with open(filename, 'w') as f:
        for line in unique_strings:
            f.write(line + "\n")


if __name__ == "__main__":
    create_dummy_file("10k.txt", 10000, 8)
    create_dummy_file("250k.txt", 250000, 8)
    create_dummy_file("500k.txt", 500000, 8)
    create_dummy_file("750k.txt", 750000, 8)
    create_dummy_file("1m.txt", 1000000, 8)


