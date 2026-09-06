const defaultSupportEmail = 'support@memoryhive.example.com';
const configuredSupportEmail = import.meta.env.VITE_SUPPORT_EMAIL?.trim();

export const SUPPORT_EMAIL = configuredSupportEmail || defaultSupportEmail;
export const SUPPORT_MAILTO = `mailto:${SUPPORT_EMAIL}`;
