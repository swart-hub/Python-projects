import argparse


parser = argparse.ArgumentParser()
parser.add_argument("amount", type=float)
parser.add_argument("category")
args = parser.parse_args()

print(f"Сумма: {args.amount}, Категория: {args.category}")