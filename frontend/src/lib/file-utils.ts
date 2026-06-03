/**
 * Reads a File object and converts it into a Base64 encoded data URL.
 *
 * @param file The File object to read.
 * @returns A promise that resolves with the data URL string, or null if an error occurs.
 */
export function readFileAsDataURL(file: File): Promise<string | null> {
  return new Promise((resolve) => {
    const reader = new FileReader();

    reader.onload = () => {
      resolve(reader.result as string);
    };

    reader.onerror = (error) => {
      console.error('Error reading file:', error);
      resolve(null); // Resolve with null on error
    };

    reader.readAsDataURL(file);
  });
}
