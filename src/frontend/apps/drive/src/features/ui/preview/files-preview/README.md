# FilePreview Component

Un composant React pour afficher une prévisualisation de fichier en plein écran avec un header de 60px et un effet de blur sur le contenu.

## Fonctionnalités

- **Plein écran** : Le composant prend tout l'écran quand il est ouvert
- **Header fixe** : Header de 60px avec fond blanc et titre
- **Effet de blur** : Le contenu a un effet de blur pour créer de la profondeur
- **Responsive** : S'adapte aux différentes tailles d'écran
- **Accessible** : Support des raccourcis clavier et navigation au clavier
- **Animations** : Transitions fluides à l'ouverture et fermeture

## Utilisation

```tsx
import React, { useState } from 'react';
import { FilePreview } from './components/file-preview';

const MyComponent = () => {
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  return (
    <div>
      <button onClick={() => setIsPreviewOpen(true)}>
        Ouvrir la prévisualisation
      </button>

      <FilePreview
        isOpen={isPreviewOpen}
        onClose={() => setIsPreviewOpen(false)}
        title="Mon fichier.pdf"
      >
        {/* Votre contenu ici */}
        <div>
          <h1>Contenu du fichier</h1>
          <p>Le contenu peut être n'importe quel élément React.</p>
        </div>
      </FilePreview>
    </div>
  );
};
```

## Props

| Prop | Type | Requis | Défaut | Description |
|------|------|--------|--------|-------------|
| `isOpen` | `boolean` | ✅ | - | Contrôle si la prévisualisation est affichée |
| `onClose` | `() => void` | ✅ | - | Fonction appelée quand l'utilisateur ferme la prévisualisation |
| `children` | `React.ReactNode` | ✅ | - | Le contenu à afficher dans la prévisualisation |
| `title` | `string` | ❌ | `'File Preview'` | Le titre affiché dans le header |

## Styles SCSS

Le composant utilise des styles SCSS avec les classes suivantes :

- `.file-preview-overlay` : L'overlay plein écran
- `.file-preview-container` : Le conteneur principal
- `.file-preview-header` : Le header de 60px
- `.file-preview-content` : La zone de contenu avec effet de blur

## Personnalisation

Vous pouvez personnaliser l'apparence en modifiant le fichier `file-preview.scss` :

- Couleurs du header et du contenu
- Taille du header (actuellement 60px)
- Intensité de l'effet de blur
- Animations et transitions
- Responsive breakpoints

## Accessibilité

- Support de la navigation au clavier
- Raccourci `Escape` pour fermer (à implémenter dans le composant parent)
- Labels ARIA appropriés
- Focus management 