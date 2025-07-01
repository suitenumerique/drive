import { useRouter } from "next/router";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { getDriver } from "@/features/config/Config";
import { useTranslation } from "react-i18next";
import { Item, ItemType } from "@/features/drivers/types";
import {
  getSdkPickerLayout,
  useSdkContext,
} from "@/features/layouts/components/sdk/SdkLayout";
import { ExplorerGridItems } from "@/features/explorer/components/grid/ExplorerGridItems";
import clsx from "clsx";
import {
  ExplorerGridBreadcrumbs,
  useBreadcrumbs,
} from "@/features/explorer/components/breadcrumbs/ExplorerGridBreadcrumbs";
import { PickerFooter } from "@/features/sdk/SdkPickerFooter";
import { Spinner } from "@gouvfr-lasuite/ui-kit";

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
  const { token } = useSdkContext();
  const [selectedItems, setSelectedItems] = useState<Item[]>([]);
  const { t } = useTranslation();
  const [init, setInit] = useState(false);

  const { data: children } = useQuery({
    queryKey: ["items", itemId, "children"],
    queryFn: () => getDriver().getChildren(itemId),
  });

  const onNavigate = (item?: Item) => {
    if (item) {
      router.push(`/sdk/explorer/items/${item.id}`);
    } else {
      router.push(`/sdk/explorer/workspaces`);
    }
  };

  const breadcrumbs = useBreadcrumbs({
    handleNavigate: onNavigate,
  });

  // Init the breadcrumbs by putting the current workspace as the first item.
  const initBreadcrumbs = async () => {
    const workspace = await getDriver().getTree(itemId);
    breadcrumbs.update(workspace);
    // We want to prevent navigation until the breadcrumbs are initialized.
    setInit(true);
  };

  useEffect(() => {
    initBreadcrumbs();
  }, []);

  if (!init) {
    return <Spinner size="xl" />;
  }

  return (
    <div>
      <ExplorerGridBreadcrumbs
        {...breadcrumbs}
        showSpacesItem={true}
        buildWithTreeContext={false}
      />
      <div
        className={clsx("explorer__grid ", {
          modal__move__empty: children?.length === 0,
        })}
      >
        {children && children.length > 0 ? (
          <ExplorerGridItems
            isCompact
            items={children}
            gridActionsCell={() => <div />}
            onNavigate={(e) => {
              const item = e.item as Item;
              breadcrumbs.update(item);
              onNavigate(item);
            }}
            selectedItems={selectedItems}
            setSelectedItems={setSelectedItems}
            canSelect={(item) => item.type === ItemType.FILE}
            disableItemDragAndDrop={true}
            displayMode="sdk"
            enableMetaKeySelection={true}
          />
        ) : (
          <div className="modal__move__empty">
            <span>{t("explorer.modal.move.empty_folder")}</span>
          </div>
        )}
      </div>

      <PickerFooter token={token} selectedItems={selectedItems} />
    </div>
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
