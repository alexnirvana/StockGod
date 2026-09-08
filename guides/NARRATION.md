# Spoken explanations

[English](NARRATION.md) · [Chinese](NARRATION_CN.md)

Version 0.5 includes 30 MP3 tracks: five lesson bodies, five course-specific coach summaries, and five common coach explanations, each in English and Simplified Chinese. These are synthesized voices, not human recordings.

## Listening

Open **Training → Lesson → Play narration**. The player supports pause, restart, seeking, section navigation, and 0.75×, 1×, 1.25×, 1.5×, and 2× speeds. The audio language can be selected independently of the interface. Coach answers include their own play button.

Playback starts on a click. Closing the dialog, leaving the course, signing out, or switching the spoken language stops the old audio. Starting another player pauses the previous one. If playback fails, the written explanation remains available and the player shows a retryable error.

Course listening positions and speed are stored in MySQL by account, lesson, and spoken language. Active playback checkpoints about every ten seconds, and pause, seek, and dialog close request another checkpoint. Abrupt browser termination or a network failure can lose the most recent unsaved seconds. **Learning Profile → My listening history** opens the saved course and spoken language. Coach audio does not create a course listening record.

Bookmarks are separate from course completion. Seeking to the end or listening to the entire recording does not award XP, unlock chapters, or replace quizzes. Competing windows use revision checks; if another window changed the bookmark, reopen the explanation before saving again.

## Hosting and updates

Audio is bundled in `content/narration/` and served by authenticated API routes with byte-range support. Playback needs access to the deployed application but no external speech service, API key, or installed system voice. Docker on Linux serves the same files. The speech engine is only needed when rebuilding recordings.

The manifest includes content versions, file checksums, durations, section offsets, and the voices used. Changes to lesson text or preset explanations require rebuilding narration. A changed audio version resets its resume position while retaining the user's speed preference. Missing audio does not prevent reading the lesson.

## Rebuilding recordings

On Windows, install the project Python environment and make FFmpeg/ffprobe available on PATH. The current build uses the installed `Microsoft Huihui Desktop` (Chinese) and `Microsoft Zira Desktop` (English) voices through System.Speech. Then run:

```powershell
.\scripts\build-narration.ps1
```

The script reads canonical lesson and coach text, creates intermediate WAV files in ignored `data/narration-build/`, and packages MP3s plus `content/narration/manifest.json`. It uses no network speech service. Commit the current manifest and all referenced MP3s with the corresponding text changes.

```sh
python -m pytest tests/integration/test_narration.py -q
npm --prefix frontend test
npm --prefix frontend run build
```

Tests cover audio integrity and text freshness, authenticated range requests, lesson locks, isolated bookmarks, retries, stale revisions, rewinds, and unchanged rewards. Browser tests additionally need actual media playback support. See [operations](OPERATIONS.md) for the isolated test environment.

Implementation references: [browser media playback](https://developer.mozilla.org/en-US/docs/Web/API/HTMLMediaElement/play) and [System.Speech WAV output](https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speechsynthesizer.setoutputtowavefile).
