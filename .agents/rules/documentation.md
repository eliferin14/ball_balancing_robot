# Documentation & Media Guidelines

- **Video Demonstrations in GitHub / README**:
  - Never embed raw HTML `<video>` tags for repository-hosted files (GitHub strips them).
  - Always convert demonstration videos to an optimized animated GIF (`.gif`) before embedding in `README.md` or documentation.
  - Embed GIFs using standard markdown image syntax: `![Description](path/to/animation.gif)`.
  - Use `ffmpeg` with two-pass palette generation (`palettegen` / `paletteuse`) and reasonable framerate (10-15 FPS) to keep file size lightweight while preserving quality.
  - Store media assets under `wiki/resources/` or dedicated documentation asset folders.

