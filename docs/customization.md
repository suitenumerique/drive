# Customization Guide 🛠 ️

## Runtime Theming 🎨

### How to Use

To use this feature, simply set the `FRONTEND_CSS_URL` environment variable to the URL of your custom CSS file. For example:

```javascript
FRONTEND_CSS_URL=http://anything/custom-style.css
```

Once you've set this variable, Drive will load your custom CSS file and apply the styles to our frontend application.

### Benefits

This feature provides several benefits, including:

*   **Easy customization** 🔄: With this feature, you can easily customize the look and feel of our application without requiring any code changes.
*   **Flexibility** 🌈: You can use any CSS styles you like to create a custom theme that meets your needs.
*   **Runtime theming** ⏱️: This feature allows you to change the theme of our application at runtime, without requiring a restart or recompilation.

### Example Use Case

Let's say you want to change the background color of our application to a custom color. You can create a custom CSS file with the following contents:

```css
body {
  background-color: #3498db;
}
```

Then, set the `FRONTEND_CSS_URL` environment variable to the URL of your custom CSS file. Once you've done this, our application will load your custom CSS file and apply the styles, changing the background color to the custom color you specified.

----

## Runtime JavaScript Injection 🚀

### How to Use

To use this feature, simply set the `FRONTEND_JS_URL` environment variable to the URL of your custom JavaScript file. For example:

```javascript
FRONTEND_JS_URL=http://anything/custom-script.js
```

Once you've set this variable, Drive will load your custom JavaScript file and execute it in the browser, allowing you to modify the application's behavior at runtime.

### Benefits

This feature provides several benefits, including:

*   **Dynamic customization** 🔄: With this feature, you can dynamically modify the behavior and appearance of our application without requiring any code changes.
*   **Flexibility** 🌈: You can add custom functionality, modify existing features, or integrate third-party services.
*   **Runtime injection** ⏱️: This feature allows you to inject JavaScript into the application at runtime, without requiring a restart or recompilation.

### Example Use Case

Let's say you want to add a custom menu to the application header. You can create a custom JavaScript file with the following contents:

```javascript
(function() {
  'use strict';

  function initCustomMenu() {
    // Wait for the page to be fully loaded
    const header = document.querySelector('header');
    if (!header) return false;

    // Create and inject your custom menu
    const customMenu = document.createElement('div');
    customMenu.innerHTML = '<button>Custom Menu</button>';
    header.appendChild(customMenu);
    
    console.log('Custom menu added successfully');
    return true;
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCustomMenu);
  } else {
    initCustomMenu();
  }
})();
```

Then, set the `FRONTEND_JS_URL` environment variable to the URL of your custom JavaScript file. Once you've done this, our application will load your custom JavaScript file and execute it, adding your custom menu to the header.

----

## **Footer Configuration** 📝

The footer is configurable from the theme customization file.

### Settings 🔧

```shellscript
THEME_CUSTOMIZATION_FILE_PATH=<path>
```

### Example of a JSON customization file

The json must follow some rules: https://github.com/suitenumerique/drive/blob/main/src/backend/drive/configuration/theme/default.json

`footer.default` is the fallback if the language is not supported.

### Custom translations in the footer 📝

The translations can be partially overridden from the theme customization file.

### Settings 🔧

```shellscript
THEME_CUSTOMIZATION_FILE_PATH=<path>
```

### Example of a JSON customization file

The json must follow some rules: https://github.com/suitenumerique/drive/blob/main/src/backend/drive/configuration/theme/default.json

## Help menu

The help menu is the "?" button of the left panel. It is hidden when its
configuration is empty.

### Settings 🔧

```shellscript
FRONTEND_HELP_MENU_CONFIG=<dict>
```

The value is read as a Python dict: write it like JSON, but with `True` and
`False`. A JSON `true` or `null` makes the setting fail. Every key is optional,
and an entry only shows when its key is set.

| Key | Description |
|-----|-------------|
| `documentationUrl` | "Documentation" link |
| `legal` | "Legal" submenu, with `personalDataUrl`, `termsOfUseUrl`, `accessibilityUrl` and `legalNoticeUrl` |
| `laSuiteSupportForm` | Support form, sent to the La Suite support API: `challengeUrl` (anti-spam challenge), `deliverUrl` (where the messages are posted) and `channel` (the support team that receives them). The three keys are needed, and the URLs are used as given |
| `supportMessagesWidget` | `True` to open the messages widget, set with the `FRONTEND_FEEDBACK_MESSAGES_WIDGET_*` variables |
| `supportEmail` | Link to open, e.g. `mailto:support@example.com`. Also the default of `EMAIL_SUPPORT_URL` |

"Contact us" opens the first of these that is set: `laSuiteSupportForm`, then
`supportMessagesWidget`, then `supportEmail`. The support form fills in the
email of the logged-in user.

### Example

```json
{
  "documentationUrl": "https://docs.example.com/drive/",
  "legal": {
    "personalDataUrl": "https://example.com/personal-data/",
    "termsOfUseUrl": "https://example.com/terms/",
    "accessibilityUrl": "https://example.com/accessibility/",
    "legalNoticeUrl": "https://example.com/legal-notice/"
  },
  "supportEmail": "mailto:support@example.com",
  "laSuiteSupportForm": {
    "challengeUrl": "https://lasuite.numerique.gouv.fr/api/support/challenge",
    "deliverUrl": "https://lasuite.numerique.gouv.fr/api/support/deliver/",
    "channel": "fichiers"
  }
}
```

In an env file, write the value on one line, after
`FRONTEND_HELP_MENU_CONFIG=`.

### Content-Security-Policy

Behind a Content-Security-Policy, the support form needs the origin of the
support API in `connect-src`, and `'wasm-unsafe-eval'` in `script-src` for the
anti-spam check.
