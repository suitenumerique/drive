// saxen is ESM-only, which Jest cannot parse from read-excel-file's CJS
// build (pulled in by ui-kit). No unit test parses spreadsheets, so a
// stub Parser is enough.
module.exports = {
  Parser: class Parser {
    on() {}
    parse() {}
    stop() {}
  },
};
