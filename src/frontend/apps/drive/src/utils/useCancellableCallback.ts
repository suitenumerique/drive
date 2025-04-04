import { useCallback, useRef } from 'react';

type CancellablePromise<T> = Promise<T> & {
  cancel?: () => void;
};

interface Options {
  delay?: number;
}

/**
 * Hook that returns a function which will cancel any previous execution when called again
 * @param callback The async function to be executed
 * @param options Configuration options including delay in milliseconds
 * @returns A wrapped function that will cancel previous executions
 */
export const useCancellableCallback = <T, Args extends unknown[]>(
  callback: (...args: Args) => Promise<T>,
  options: Options = {}
) => {
  const currentPromiseRef = useRef<CancellablePromise<T> | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);

  return useCallback(
    async (...args: Args) => {
      // Clear any existing timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }

      // Cancel previous execution if it exists
      if (currentPromiseRef.current?.cancel) {
        currentPromiseRef.current.cancel();
      }

      // Create a new promise that can be cancelled
      let isCancelled = false;
      const promise: CancellablePromise<T> = new Promise((resolve, reject) => {
        const executeCallback = () => {
          callback(...args)
            .then((result) => {
              if (!isCancelled) {
                resolve(result);
              }
            })
            .catch((error) => {
              if (!isCancelled) {
                reject(error);
              }
            });
        };

        if (options.delay && options.delay > 0) {
          timeoutRef.current = setTimeout(executeCallback, options.delay);
        } else {
          executeCallback();
        }
      });

      // Add cancel method to the promise
      promise.cancel = () => {
        isCancelled = true;
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
      };

      // Store the current promise
      currentPromiseRef.current = promise;

      try {
        return await promise;
      } catch (error) {
        throw error;
      } finally {
        // Clear the reference if this was the last promise
        if (currentPromiseRef.current === promise) {
          currentPromiseRef.current = null;
          if (timeoutRef.current) {
            clearTimeout(timeoutRef.current);
            timeoutRef.current = null;
          }
        }
      }
    },
    [callback, options.delay]
  );
}; 