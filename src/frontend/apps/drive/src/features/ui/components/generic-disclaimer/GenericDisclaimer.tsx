import { PropsWithChildren } from "react";

export const GenericDisclaimer = ({
  message,
  imageSrc,
  children,
}: {
  message: string;
  imageSrc: string;
} & PropsWithChildren) => {
  return (
    <div className="drive__generic-disclaimer">
      <div className="drive__generic-disclaimer__content">
        <img
          className="drive__generic-disclaimer__content__image"
          src={imageSrc}
          alt=""
        />
        <p>{message}</p>
        {children}
      </div>
    </div>
  );
};
