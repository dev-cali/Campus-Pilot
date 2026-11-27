export type ComposerKeyState = {
  key: string;
  shiftKey: boolean;
  isComposing: boolean;
  keyCode?: number;
  pending: boolean;
};

export type ComposerAction = {
  type: "button" | "submit";
  action: "send" | "stop";
  label: string;
  title?: string;
  disabled: boolean;
};

/** Keep the composer action in one stable position while its request is active. */
export function getComposerAction(pending: boolean, questionValid: boolean): ComposerAction {
  if (pending) {
    return { type: "button", action: "stop", label: "Stop waiting", title: "Stop waiting", disabled: false };
  }
  return { type: "submit", action: "send", label: "Ask CampusPilot", disabled: !questionValid };
}

export function shouldSubmitOnEnter(state: ComposerKeyState): boolean {
  return state.key === "Enter" && !state.shiftKey && !state.isComposing &&
    state.keyCode !== 229 && !state.pending;
}
