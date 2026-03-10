import { useEffect, useState } from "react";

function debounce<T extends (...args: never[]) => unknown>(
  func: T,
  timeout = 300,
): ((...args: Parameters<T>) => void) & { cancel: () => void } {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const debouncedFunc = (...args: Parameters<T>) => {
    if (timer !== undefined) {
      clearTimeout(timer);
    }
    timer = setTimeout(() => {
      func(...args);
    }, timeout);
  };
  debouncedFunc.cancel = () => {
    if (timer !== undefined) {
      clearTimeout(timer);
    }
  };
  return debouncedFunc;
}

export const useDebouncedResize = () => {
  const [size, setSize] = useState({
    width: window.innerWidth,
    height: window.innerHeight,
  });

  useEffect(() => {
    const handleResize = debounce(() => {
      setSize({ width: window.innerWidth, height: window.innerHeight });
    }, 100);
    window.addEventListener("resize", handleResize);
    return () => {
      handleResize.cancel();
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return size;
};
