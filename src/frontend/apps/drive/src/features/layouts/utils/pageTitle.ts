/**
 * Browser tab title: current page, then application name.
 * RGAA 8.5 / WCAG 2.4.2. Example: "Mes fichiers | Fichiers".
 *
 * Lists load more results in the same document (infinite scroll), so there is
 * no distinct paginated page to append.
 */
export const formatPageTitle = (pageName: string, appTitle: string): string => {
  const name = pageName.trim();
  if (!name) {
    return appTitle;
  }
  return `${name} | ${appTitle}`;
};
