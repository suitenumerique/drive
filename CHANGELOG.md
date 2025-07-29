# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- 🐛(backend) stop decreasing twice the numchild in deletion process #284
- ⚡️(backend) optimize trashbin endpoint #276 
- ♻️(backend) modify sdk-relay to use DRF viewset and serializers #269

## [v0.1.0] - 2025-07-25

### Added

- 🚀 Drive, A collaborative file sharing and document management platform
- ✨(front) add move modal #213
- ✨(front) update the homepage to alpha #234
- ✨(global) add customization to feedbacks
- ✨(front) add PDF, Audio, Video, Image viewers
- ✨(front) make frontend themable
- ✨(global) Add File Picker SDK
- 🔧(cron) add pgdump cron on scalingo deployment #264

### Changed

- 🐛(email) add missing email logo
- 📝(dx) fix and document how to run the project locally

### Fixed

- 🐛(i18n) fix language detection and rendering
- 🌐(front) add english translation for rename modal
- 🐛(global) fix wrong Content-Type on specific s3 implementations


[unreleased]: https://github.com/suitenumerique/drive/compare/v0.1.0...main
[0.1.0]: https://github.com/suitenumerique/drive/releases/v0.1.0