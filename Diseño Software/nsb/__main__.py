"""Entry point: ``python -m nsb <subcomando>``."""
import nsb._bootstrap  # noqa: F401

from nsb.cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
