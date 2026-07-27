// Widget helper functions to share common logic

declare global {
  interface Window {
    _lasuite_widget?: unknown[];
    _stmsg_widget?: unknown[];
  }
}

export class WidgetHelper {
  // Both keys are populated so that legacy and current widget runtimes
  // can consume the same command queue.
  static #QUEUE_KEYS = ["_lasuite_widget", "_stmsg_widget"] as const;

  static pushCommand(command: unknown[]) {
    for (const key of WidgetHelper.#QUEUE_KEYS) {
      const queue = window[key] ?? [];
      queue.push(command);
      window[key] = queue;
    }
  }

  static loadScript(scriptUrl: string) {
    if (document.querySelector(`script[src="${scriptUrl}"]`)) return;

    const script = document.createElement("script");
    script.async = true;
    script.src = scriptUrl;
    const firstScript = document.getElementsByTagName("script")[0];
    if (firstScript && firstScript.parentNode) {
      firstScript.parentNode.insertBefore(script, firstScript);
    }
  }
}