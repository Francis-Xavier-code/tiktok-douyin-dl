---
name: media-downloader
description: Download public Douyin or TikTok videos and photo posts from share text, direct URLs, short links, or Douyin search-result URLs. Use when a user asks an autonomous agent to find and save supported Douyin/TikTok media locally, choose an output folder, install the official Linux/macOS CLI when missing, or explicitly update the managed CLI.
---

# Media Downloader

Use the bundled script to run the project CLI with safely quoted input. It normalizes supported Douyin web-result URLs before invoking the CLI, supports Linux x86_64 and macOS (Apple Silicon arm64 / Intel x86_64) directly, and can use a caller-supplied executable on other systems through `MEDIA_DOWNLOADER_BIN`. Packaged CLI archives bundle the headless Chromium, so no browser download is needed on first run.

## Workflow

1. If the user supplied keywords instead of a URL, use the agent's available web or browser search capability to find public candidate works. When several candidates plausibly match, show the choices or ask which one to download; do not silently choose unrelated media.
2. Confirm the selected public Douyin or TikTok result/share link and an authorized output location. Accept Douyin search-result URLs containing `modal_id`; the bundled script converts them to direct work URLs.
   - If a Douyin search URL has no `modal_id`, it identifies a results page rather than one work. Select one specific result or ask the user which result they want.
3. Default the output directory to `downloads` inside the current workspace unless the user chose another path.
4. Run:

```bash
bash "{baseDir}/scripts/download.sh" --output "<output-directory>" -- "<share-text-or-url>"
```

5. Wait for the command to finish. Report the selected result, platform detected by the CLI, output directory, and only files the command confirms were saved.
6. If automatic detection fails for another supported nonstandard URL, retry once with `--platform douyin` or `--platform tiktok`. Do not require the user to obtain mobile share text first.

## CLI management

Install the latest official Linux x86_64 or macOS CLI without downloading media:

```bash
bash "{baseDir}/scripts/download.sh" --install
```

Update the managed CLI only when the user explicitly asks:

```bash
bash "{baseDir}/scripts/download.sh" --update
```

Pin installation to a release when reproducibility matters:

```bash
MEDIA_DOWNLOADER_VERSION=v1.8.2 bash "{baseDir}/scripts/download.sh" --install
```

## Guardrails

- Keep share text and paths quoted; never pass them through `eval` or another shell.
- Do not request account cookies, passwords, or private-platform credentials.
- Do not bypass access controls or download private/restricted media.
- If the Playwright browser runtime is missing, report the CLI's exact installation hint before taking any dependency-install action.
- Stop and report the exact error if the OS or CPU has no supported release binary.
