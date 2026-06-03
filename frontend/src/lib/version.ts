export const appName = process.env.NEXT_PUBLIC_APP_NAME || 'PARK_SPEECH';
export const version = process.env.NEXT_PUBLIC_APP_VERSION || '3.0.0';
export const buildDate = process.env.NEXT_PUBLIC_BUILD_DATE || '';

export const getVersionInfo = () => ({
  version,
  name: appName,
  buildDate,
});
