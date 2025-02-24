export const Explorer = ({ itemId }: { itemId: string }) => {
  return (
    <div className="explorer">
      <div className="explorer__filters">FILTERS</div>
      <div className="explorer__content">
        <div>ITEM {itemId}</div>
      </div>
    </div>
  );
};
