import { Explorer } from "@/features/explorer/components/Explorer";
import { useRouter } from "next/router";
import { useExplorer } from "@/features/explorer/components/ExplorerContext";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { getDriver } from "@/features/config/Config";
import { Button } from "@openfun/cunningham-react";
import { useTranslation } from "react-i18next";
import { ItemType } from "@/features/drivers/types";
import { useMutationCreateFile } from "@/features/explorer/hooks/useMutations";
import { getSdkPickerLayout } from "@/features/layouts/components/sdk/SdkLayout";

// interface FileSavePayload {
//   title: string;
//   object: File;
// }

// interface SaverPayload {
//   files: FileSavePayload[];
// }

/**
 * Route used for SDK integration as popup ( File Picker ).
 */
export default function ItemPage() {
  const router = useRouter();
  const itemId = router.query.id as string;

  const { data: children } = useQuery({
    queryKey: ["items", itemId, "children"],
    queryFn: () => getDriver().getChildren(itemId),
  });

  return (
    <Explorer
      childrenItems={children}
      canSelect={(item) => item.type === ItemType.FILE}
      disableAreaSelection={true}
      disableItemDragAndDrop={true}
    />
  );
}

ItemPage.getLayout = getSdkPickerLayout;

// const SaveFooter = ({ token }: { token: string }) => {
//   const { t } = useTranslation();
//   const [payload, setPayload] = useState<SaverPayload | null>(null);
//   const createFile = useMutationCreateFile();
//   const { itemId } = useExplorer();

//   useEffect(() => {
//     window.opener.postMessage(
//       {
//         type: ClientMessageType.SAVER_READY,
//       },
//       "*"
//     );

//     const onMessage = (event: MessageEvent) => {
//       const { type, data } = event.data;

//       if (type === ClientMessageType.SAVER_PAYLOAD) {
//         console.log("payload", data);
//         // setInterval(() => {
//         //   console.log("payload", data);
//         // }, 1000);
//         setPayload(data);
//       }
//     };

//     window.addEventListener("message", onMessage);

//     return () => {
//       window.removeEventListener("message", onMessage);
//     };
//   }, []);

//   const onSave = async () => {
//     if (!payload) {
//       return;
//     }
//     const promises = [];
//     for (const file of payload.files) {
//       promises.push(
//         () =>
//           new Promise<void>((resolve) => {
//             createFile.mutate(
//               {
//                 filename: file.title,
//                 file: file.object,
//                 parentId: itemId,
//               },
//               {
//                 onError: () => {
//                   // TODO
//                 },
//                 onSettled: () => {
//                   resolve();
//                 },
//               }
//             );
//           })
//       );
//     }
//     for (const promise of promises) {
//       await promise();
//     }
//     window.opener.postMessage(
//       {
//         type: ClientMessageType.ITEM_SAVED,
//         data: {
//           items: payload.files,
//         },
//       },
//       "*"
//     );
//   };

//   return (
//     <div className="explorer__footer">
//       <div>
//         <span>{t("sdk.explorer.save_label")} </span>
//         {payload?.files.map((file) => (
//           <span style={{ fontWeight: "bold" }} key={file.title}>
//             {file.title}
//           </span>
//         ))}
//       </div>
//       <Button onClick={onSave}>{t("sdk.explorer.save")}</Button>
//     </div>
//   );
// };
