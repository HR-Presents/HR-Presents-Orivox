HR-Presents ORIVOX v1.0.2 — LOCAL WEB EDITION

THIS is the recommended ORIVOX package.

1. Extract the ZIP completely. Do not run ORIVOX from inside the ZIP preview.
2. Double-click: Start ORIVOX.bat
3. A terminal opens and shows every setup step.
4. On first launch ORIVOX will:
   - check/install Python 3.11 if needed
   - create a private .venv inside the ORIVOX folder
   - install Python requirements with visible pip progress
   - check/install Ollama if needed
   - check qwen2.5:3b
   - if qwen2.5:3b is missing, run `ollama pull qwen2.5:3b` in the same terminal so you can see percentage, size and speed
   - start the ORIVOX local website
   - open http://127.0.0.1:8765 in your browser

IMPORTANT
- Keep the terminal open while using ORIVOX.
- Press Ctrl+C in the terminal to stop ORIVOX.
- First launch is slower because dependencies and AI models may need to download.
- Later launches reuse the installed .venv and Ollama model and start much faster.
- Internet is needed only for first-time dependency/model downloads and for live web/current-data questions.
- The ORIVOX server itself runs locally on 127.0.0.1.
