import { removeFileExtension } from "../mimeTypes";

describe("removeFileExtension", () => {
  describe("when filename is empty or null", () => {
    it("should return empty string when filename is empty", () => {
      expect(removeFileExtension("")).toBe("");
    });

    it("should return the same value when filename is falsy", () => {
      // @ts-expect-error - testing with null/undefined
      expect(removeFileExtension(null)).toBe(null);
      // @ts-expect-error - testing with null/undefined
      expect(removeFileExtension(undefined)).toBe(undefined);
    });
  });

  describe("when filename starts with a dot (hidden files)", () => {
    it("should return the filename unchanged for hidden files", () => {
      expect(removeFileExtension(".env")).toBe(".env");
      expect(removeFileExtension(".gitignore")).toBe(".gitignore");
      expect(removeFileExtension(".hidden.txt")).toBe(".hidden.txt");
      expect(removeFileExtension("..")).toBe("..");
    });
  });

  describe("when filename has no extension", () => {
    it("should return the filename unchanged", () => {
      expect(removeFileExtension("filename")).toBe("filename");
      expect(removeFileExtension("myfile")).toBe("myfile");
      expect(removeFileExtension("file.name")).toBe("file.name"); // dot but no valid extension
    });
  });

  describe("when filename has an unknown extension", () => {
    it("should return the filename unchanged for unknown extensions", () => {
      expect(removeFileExtension("file.unknown")).toBe("file.unknown");
      expect(removeFileExtension("document.xyz")).toBe("document.xyz");
      expect(removeFileExtension("test.abc123")).toBe("test.abc123");
    });
  });

  describe("when filename has a known extension", () => {
    it("should remove .pdf extension", () => {
      expect(removeFileExtension("document.pdf")).toBe("document");
      expect(removeFileExtension("my file.pdf")).toBe("my file");
    });

    it("should remove .docx extension", () => {
      expect(removeFileExtension("document.docx")).toBe("document");
      expect(removeFileExtension("my file.docx")).toBe("my file");
    });

    it("should remove .xlsx extension", () => {
      expect(removeFileExtension("spreadsheet.xlsx")).toBe("spreadsheet");
    });

    it("should remove image extensions", () => {
      expect(removeFileExtension("photo.jpg")).toBe("photo");
      expect(removeFileExtension("image.png")).toBe("image");
      expect(removeFileExtension("picture.gif")).toBe("picture");
      expect(removeFileExtension("photo.heic")).toBe("photo");
    });

    it("should remove video extensions", () => {
      expect(removeFileExtension("video.mp4")).toBe("video");
      expect(removeFileExtension("movie.avi")).toBe("movie");
      expect(removeFileExtension("clip.webm")).toBe("clip");
    });

    it("should remove audio extensions", () => {
      expect(removeFileExtension("song.mp3")).toBe("song");
      expect(removeFileExtension("audio.wav")).toBe("audio");
      expect(removeFileExtension("music.flac")).toBe("music");
    });

    it("should remove archive extensions", () => {
      expect(removeFileExtension("archive.zip")).toBe("archive");
      expect(removeFileExtension("compressed.rar")).toBe("compressed");
      expect(removeFileExtension("backup.7z")).toBe("backup");
    });

    it("should remove code file extensions", () => {
      expect(removeFileExtension("script.js")).toBe("script");
      expect(removeFileExtension("code.ts")).toBe("code");
      expect(removeFileExtension("style.css")).toBe("style");
      expect(removeFileExtension("program.py")).toBe("program");
    });

    it("should handle extensions case-insensitively", () => {
      expect(removeFileExtension("file.PDF")).toBe("file");
      expect(removeFileExtension("file.DOCX")).toBe("file");
      expect(removeFileExtension("file.JPG")).toBe("file");
      expect(removeFileExtension("file.Mp4")).toBe("file");
    });

    it("should handle filenames with multiple dots correctly", () => {
      expect(removeFileExtension("my.file.pdf")).toBe("my.file");
      expect(removeFileExtension("version.1.2.3.zip")).toBe("version.1.2.3");
      expect(removeFileExtension("file.backup.tar.gz")).toBe("file.backup.tar"); // .gz is known
    });

    it("should handle filenames with spaces", () => {
      expect(removeFileExtension("my document.pdf")).toBe("my document");
      expect(removeFileExtension("  spaced  .pdf")).toBe("  spaced  ");
    });
  });

  describe("edge cases", () => {
    it("should handle single character filenames with extension", () => {
      expect(removeFileExtension("a.pdf")).toBe("a");
      expect(removeFileExtension("x.txt")).toBe("x");
    });

    it("should handle very long filenames", () => {
      const longName = "a".repeat(100) + ".pdf";
      expect(removeFileExtension(longName)).toBe("a".repeat(100));
    });

    it("should handle special characters in filename", () => {
      expect(removeFileExtension("file-name_123.pdf")).toBe("file-name_123");
      expect(removeFileExtension("file@name#123.pdf")).toBe("file@name#123");
    });
  });
});
