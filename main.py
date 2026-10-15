"""Ponto de entrada do GUY Builder.

  python main.py                 -> interface gráfica
  python main.py --cli --entry X -> modo linha de comando (ver --help)
"""
import sys


def run():
    if "--cli" in sys.argv[1:]:
        from guy_builder.cli import main
        argv = [a for a in sys.argv[1:] if a != "--cli"]
        sys.exit(main(argv))
    from guy_builder.ui.app import run_app
    run_app()


if __name__ == "__main__":
    run()
