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

----

## **Waffle Configuration** 🧇

The waffle (La Gaufre) is the widget in the header that displays a grid of services. By default it loads its script and its list of services from the La Suite servers. Both can be replaced from the theme customization file, for example to list the services of your own instance.

### Settings 🔧

```shellscript
THEME_CUSTOMIZATION_FILE_PATH=<path>
```

### Example of a JSON customization file

The waffle is configured with the `waffle` key. It accepts either `apiUrl` (an endpoint returning `{"services": [...]}`) or `data` (the list itself), plus the optional `widgetPath` (URL of the `lagaufre.js` widget script) and `showMoreLimit`.

```json
{
  "waffle": {
    "data": {
      "services": [
        {
          "name": "Docs",
          "url": "https://docs.example.org",
          "maturity": "stable",
          "logo": "https://docs.example.org/logo.svg"
        }
      ]
    },
    "widgetPath": "https://drive.example.org/lagaufre.js",
    "showMoreLimit": 9
  }
}
```

If the file has no `waffle` key, or neither `apiUrl` nor `data` is set, the default waffle of the theme is used.

> [!NOTE]
> Without `widgetPath`, the widget script is still loaded from the default La Suite server. Set `widgetPath` to a self-hosted copy of `lagaufre.js` if the browsers must not call it. To remove the waffle entirely, set `FRONTEND_HIDE_GAUFRE=True`.
