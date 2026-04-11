// Enforce login before accessing app pages. Set PUBLIC_AUTH_REQUIRED=true in production.
export const AUTH_REQUIRED = (import.meta.env.PUBLIC_AUTH_REQUIRED ?? "false") === "true";

// When AUTH_REQUIRED is true, show static demo data to unauthenticated guests instead of hard-blocking.
// Guests see a banner and can explore without consuming API credits.
export const GUEST_TRIAL_ENABLED = (import.meta.env.PUBLIC_GUEST_TRIAL ?? "true") === "true";

export const AUTH_BYPASS_USER_ID = import.meta.env.PUBLIC_AUTH_BYPASS_USER_ID ?? "user_local";
