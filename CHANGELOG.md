# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- ✨(backend) search endpoint for ItemViewSet #312
- ✨(front) add search modal #326

### Patches

- ♻️(front) refactor tree loading #326
- ♻️(front) externalize FilePreview from EmbeddedExplorer + modalify #326

## [v0.4.0] - 2025-09-02

### Added

- ✨(back) implement lasuite.malware_detection app #212
- ✅(front) add e2e testing #317

### Changed

- 🔧(back) customize cache config #321

### Fixed

- 🐛(front) fix redirect after delete node in tree #325

## [v0.3.0] - 2025-08-25

### Added

- ✨(back) allow theme customization using a configuration file #299
- ✨(front) use theme_customization to configure the footer #299

### Fixed

- 🔧(nginx) fix trash route #309
- 🐛(front) fix workspace link react cache #310
- 🐛(backend) allow item partial update without modifying title #316
- 🌐(front) fix share item wording #315

## [v0.2.0] - 2025-08-18

### Added

- ✨(front) Add public workspaces
- ✨(front) Add 401, 403 pages
- ✨(front) Add redirect after login logic

### Changed

- ♻️(back) manage title uniqueness by generating new one if existing #296
- 🧑‍💻(docker) handle frontend development images with docker compose #298
- 🔧(project) change env.d system by using local files #298
- Bump ui-kit to remove the usage of base64 font in CSS #302

### Fixed

- 🐛(front) set the correct move icon
- 🐛(nginx) add trash route
- 💬(front) update feedback texts

## [v0.1.1] - 2025-07-30

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
- ✨(back) implement lasuite.malware_detection app #212

### Changed

- 🐛(email) add missing email logo
- 📝(dx) fix and document how to run the project locally

### Fixed

- 🐛(i18n) fix language detection and rendering
- 🌐(front) add english translation for rename modal
- 🐛(global) fix wrong Content-Type on specific s3 implementations

[unreleased]: https://github.com/suitenumerique/drive/compare/v0.4.0...main
[0.4.0]: https://github.com/suitenumerique/drive/releases/v0.3.0
[0.3.0]: https://github.com/suitenumerique/drive/releases/v0.3.0
[0.2.0]: https://github.com/suitenumerique/drive/releases/v0.2.0
[0.1.1]: https://github.com/suitenumerique/drive/releases/v0.1.1
[0.1.0]: https://github.com/suitenumerique/drive/releases/v0.1.0
