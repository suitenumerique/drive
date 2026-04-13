#!/usr/bin/env bash

# Download OnlyOffice client-side editor (v9) and x2t WASM converter.
# These assets are gitignored and downloaded on demand for dev/CI/build.
#
# OnlyOffice client-side components are used for editing encrypted files
# without going through WOPI (server-to-server), keeping all decryption
# in the browser.
#
# Sources:
#   - OnlyOffice editor: https://github.com/cryptpad/onlyoffice-editor
#   - x2t WASM: https://github.com/cryptpad/onlyoffice-x2t-wasm

set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)
OO_DIR="$SCRIPT_DIR/../src/frontend/apps/drive/public/onlyoffice"

# OnlyOffice v9 client-side build (sdkjs + web-apps)
OO_VERSION="v9.2.0.119+5"
OO_SHA512="1f1184fb04cf72a7eb2a49a9740074b5419486c79e1fd713e1f8c09b8594a826050ae941fed6ac6a96807ba73cc751d7c807bd7e6b73de9e4f8e74cd5ed04cfa"

# x2t WASM format converter (docx/xlsx/pptx <-> bin)
X2T_VERSION="v7.3+1"
X2T_SHA512="ab0c05b0e4c81071acea83f0c6a8e75f5870c360ec4abc4af09105dd9b52264af9711ec0b7020e87095193ac9b6e20305e446f2321a541f743626a598e5318c1"

ensure_command() {
    if ! command -v "$1" &>/dev/null; then
        echo "Error: $1 is required but not installed."
        exit 1
    fi
}

install_oo() {
    local FULL_DIR="$OO_DIR/v9"

    if [ -e "$FULL_DIR/.version" ] && [ "$(cat "$FULL_DIR/.version")" = "$OO_VERSION" ]; then
        echo "OnlyOffice v9 is up to date."
        return
    fi

    ensure_command curl
    ensure_command sha512sum
    ensure_command unzip

    echo "Downloading OnlyOffice v9..."
    rm -rf "$FULL_DIR"
    mkdir -p "$FULL_DIR"
    cd "$FULL_DIR"

    curl -L "https://github.com/cryptpad/onlyoffice-editor/releases/download/$OO_VERSION/onlyoffice-editor.zip" \
        -o onlyoffice-editor.zip

    echo "$OO_SHA512 onlyoffice-editor.zip" > onlyoffice-editor.zip.sha512
    if ! sha512sum -c onlyoffice-editor.zip.sha512; then
        echo "Checksum mismatch for OnlyOffice editor!"
        rm -rf "$FULL_DIR"
        exit 1
    fi

    unzip -q onlyoffice-editor.zip
    rm onlyoffice-editor.zip*

    # Remove help files to save space
    rm -rf "$FULL_DIR/web-apps/apps/documenteditor/main/resources/help"
    rm -rf "$FULL_DIR/web-apps/apps/presentationeditor/main/resources/help"
    rm -rf "$FULL_DIR/web-apps/apps/spreadsheeteditor/main/resources/help"
    rm -rf "$FULL_DIR/web-apps/apps/common/main/resources/help/"

    # Create stub files that OnlyOffice expects but aren't in the build
    echo '{}' > "$FULL_DIR/plugins.json"
    echo '[]' > "$FULL_DIR/themes.json"
    echo '// Stub service worker for client-side mode' > "$FULL_DIR/document_editor_service_worker.js"

    # CryptPad's build doesn't include the format icons spritesheet that OO's
    # injectSvgIcons() tries to load — create an empty SVG to suppress the 404.
    echo '<svg xmlns="http://www.w3.org/2000/svg"/>' > \
        "$FULL_DIR/web-apps/apps/common/main/resources/img/doc-formats/formats@2.5x.svg"

    echo "$OO_VERSION" > "$FULL_DIR/.version"
    echo "OnlyOffice v9 installed."
}

install_x2t() {
    local X2T_DIR="$OO_DIR/x2t"

    if [ -e "$X2T_DIR/.version" ] && [ "$(cat "$X2T_DIR/.version")" = "$X2T_VERSION" ]; then
        echo "x2t WASM is up to date."
        return
    fi

    ensure_command curl
    ensure_command sha512sum
    ensure_command unzip

    echo "Downloading x2t WASM converter..."
    rm -rf "$X2T_DIR"
    mkdir -p "$X2T_DIR"
    cd "$X2T_DIR"

    curl -L "https://github.com/cryptpad/onlyoffice-x2t-wasm/releases/download/$X2T_VERSION/x2t.zip" \
        -o x2t.zip

    echo "$X2T_SHA512 x2t.zip" > x2t.zip.sha512
    if ! sha512sum -c x2t.zip.sha512; then
        echo "Checksum mismatch for x2t!"
        rm -rf "$X2T_DIR"
        exit 1
    fi

    unzip -q x2t.zip
    rm x2t.zip*

    echo "$X2T_VERSION" > "$X2T_DIR/.version"
    echo "x2t WASM installed."
}

main() {
    mkdir -p "$OO_DIR"
    install_oo
    install_x2t
    echo "Done. OnlyOffice assets installed in $OO_DIR"
}

main "$@"
