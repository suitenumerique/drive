import { useQuery } from "@tanstack/react-query";
import { getDriver } from "@/features/config/config";

export const ExplorerTree = () => {
  const driver = getDriver();
  console.log("ExplorerTree", driver);
  const { data } = useQuery({
    queryKey: ["explorer-tree"],
    queryFn: () => driver.getItems(),
  });
  console.log("ExplorerTree", data);

  return (
    <div>
      <h4>Explorer Tree</h4>
      <div>
        {data?.map((item) => (
          <div key={item.id}>{item.name}</div>
        ))}
      </div>
    </div>
  );
};
