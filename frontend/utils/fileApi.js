import API_BASE from "./api";

/**
 * Upload file (Task 9)
 */
export async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/chat/files/upload/`, {
    method: "POST",
    body: formData,
  });

  return response.json();
}

/**
 * List uploaded files (Task 10)
 */
export async function listFiles() {
  const response = await fetch(`${API_BASE}/chat/files/`);
  return response.json();
}

/**
 * Delete file by ID (Task 11)
 */
export async function deleteFile(fileId) {
  await fetch(`${API_BASE}/chat/files/${fileId}/delete/`, {
    method: "DELETE",
  });
}
