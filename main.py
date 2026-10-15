# The detector's runtime has to be loaded before the first window opens.
# Loaded afterwards, its bundled LLVM collides with the one the graphics
# driver brings in and the process crashes.
try:
    import triton  # noqa: F401
except ImportError:
    pass

from app.application import main


if __name__ == "__main__":
    main()
