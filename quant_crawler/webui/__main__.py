"""``python -m quant_crawler.webui`` entry point."""
import sys

from .server import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
