"""Allow ``python -m quant_crawler.strategy_gen [...]`` invocation."""
import sys

from .generate import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
