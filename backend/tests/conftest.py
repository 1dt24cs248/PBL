import os

# Lower bcrypt work factor in tests only; production defaults to 12 rounds.
os.environ["BCRYPT_ROUNDS"] = "4"
