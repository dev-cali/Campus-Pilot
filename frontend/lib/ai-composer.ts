export type ComposerKeyState = {
  key: string;
  shiftKey: boolean;
  isComposing: boolean;
  keyCode?: number;
  pending: boolean;
};

export function shouldSubmitOnEnter(state: ComposerKeyState): boolean {
  return state.key === "Enter" && !state.shiftKey && !state.isComposing &&
    state.keyCode !== 229 && !state.pending;
}
