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
OO_VERSION="v9.3.2+3"
OO_SHA512="181978176e443b9ff9cce127e6aa9668a4ee8e81473cb0c0c4cf0d83dea9b6636c730d40e704ebe8fdf313498a3106bafe5c4021ae937b269d05a07b7be6bbb4"

# x2t WASM format converter (docx/xlsx/pptx <-> bin).
X2T_VERSION="v9.3.2+3"
X2T_SHA512="ed0579097a0269877d6622b28b1e2718e1f9f4e8ac99301f5f13f5f052b3db24db789deab8c654044db588be103c139be74f83a0ca066dee1789522241c1af6e"

# A file made here gets a fixed date: nginx derives the ETag from it, and the build
# time would make browsers download it again after every deployment.
write_stub() {
    echo "$2" > "$1"
    touch -d "2000-01-01 00:00:00" "$1"
}

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
    write_stub "$FULL_DIR/plugins.json" '{}'
    write_stub "$FULL_DIR/themes.json" '[]'
    write_stub "$FULL_DIR/document_editor_service_worker.js" '// Stub service worker for client-side mode'

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

patch_stubs() {
    # Stubs that may be missing from an earlier install (added after initial version)
    local FORMATS_SVG="$OO_DIR/v9/web-apps/apps/common/main/resources/img/doc-formats/formats@2.5x.svg"
    if [ -d "$OO_DIR/v9" ] && [ ! -f "$FORMATS_SVG" ]; then
        write_stub "$FORMATS_SVG" '<svg xmlns="http://www.w3.org/2000/svg"/>'
        echo "Patched missing formats@2.5x.svg stub."
    fi

    # The header's product icons (9.3+), not in the build
    local HEADER_DIR="$OO_DIR/v9/web-apps/apps/common/main/resources/img/header"
    if [ -d "$HEADER_DIR" ]; then
        for kind in document spreadsheet presentation pdf drawing; do
            for variant in "" "-white"; do
                local ICON="$HEADER_DIR/icon-$kind$variant.svg"
                [ -f "$ICON" ] || write_stub "$ICON" '<svg xmlns="http://www.w3.org/2000/svg"/>'
            done
        done
    fi
}

main() {
    mkdir -p "$OO_DIR"
    install_oo
    install_x2t
    patch_stubs
    echo "Done. OnlyOffice assets installed in $OO_DIR"
}

main "$@"
