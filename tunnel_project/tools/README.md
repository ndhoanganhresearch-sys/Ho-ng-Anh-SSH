# Tunnel Project Tools

This folder contains standalone helper scripts used for dataset generation,
profile learning, station merging, and verification experiments.

Dataset generators currently include:

- `create_blender_test_dataset.py`: compact multi-case benchmark suite.
- `create_blender_sample_like_dataset.py`: OS1/OS6-style field sample surrogate
  with global coordinates and six-column TXT files.

These scripts are not the main application entrypoint. Keep production UI and
pipeline code under `tunnel_analysis/`, and add reusable tests under the project
root or a dedicated test suite when a helper becomes part of the maintained
workflow.
