export type AiFailureAction = "signIn" | "retry";
export type AiFailure = { message: string; action?: AiFailureAction };

// Keep the browser deadline longer than the proxy's 75-second upstream deadline
// while leaving room inside the Route Handler's configured 120-second ceiling.
export const AI_BROWSER_TIMEOUT_MS = 110_000;
export const AI_SLOW_NOTICE_MS = 15_000;

export function aiFailureForStatus(status: number): AiFailure {
  if (status === 400 || status === 422) {
    return { message: "CampusPilot could not validate that question. Check the 2,000-character limit and try again." };
  }
  if (status === 401) {
    return { message: "Your sign-in session may have expired. Sign in again to continue.", action: "signIn" };
  }
  if (status === 403) {
    return { message: "This request was not permitted. Review the question and your access, then try again." };
  }
  if (status === 429) {
    return { message: "The AI demo request limit was reached. Wait a little before trying again.", action: "retry" };
  }
  if (status === 502 || status === 503 || status === 504) {
    return { message: "The AI service is temporarily unavailable or taking too long. You can retry manually.", action: "retry" };
  }
  return { message: "CampusPilot received an unexpected response. You can retry manually.", action: "retry" };
}

export const AI_NETWORK_FAILURE: AiFailure = {
  message: "CampusPilot could not reach the AI service. Check your connection and retry manually.",
  action: "retry",
};

export const AI_INVALID_RESPONSE: AiFailure = {
  message: "CampusPilot could not read a valid AI response. You can retry manually.",
  action: "retry",
};

export const AI_REQUEST_TIMEOUT: AiFailure = {
  message: "This request took longer than expected. The backend may still be processing; you can retry manually.",
  action: "retry",
};
