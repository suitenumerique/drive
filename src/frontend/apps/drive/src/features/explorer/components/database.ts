import { Item } from "@/features/drivers/types";

import { ItemType } from "@/features/drivers/types";

export const database: Item[] = [
  {
    id: "1",
    type: ItemType.FOLDER,
    title: "Projets en cours",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "2",
    type: ItemType.FOLDER,
    title: "Archives dernières années",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "3",
    type: ItemType.FOLDER,
    title: "Resources juridiques",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "4",
    type: ItemType.FOLDER,
    title: "Présentation nouveau logo",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "5",
    type: ItemType.FOLDER,
    title: "Comptabilité hebdomadaire",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "6",
    type: ItemType.FOLDER,
    title: "Présentation nouveau logo",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "7",
    type: ItemType.FILE,
    title: "Rapport annuel 2024",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "8",
    type: ItemType.FILE,
    title: "Fond d'écran",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "9",
    type: ItemType.FILE,
    title: "Export utilisateurs",
    lastUpdate: "Il y a 5h",
  },
];
